#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["databricks-sql-connector>=4"]
# ///
"""dbx — compact Databricks query helper for agentic use.

Connection comes from ~/.databrickscfg (profile 'dev' by default). The default
warehouse reads esxp_dev, esxp_dev_pr and esxp_uat (same workspace/metastore).
esxp_prd is a separate workspace: use --profile prd (auto-selects its warehouse).
Fully qualify tables as catalog.schema.table.

Usage:
  dbx "SELECT ..."                      raw SQL (';'-separated multi-statement)
  dbx schemas <catalog>                 SHOW SCHEMAS
  dbx tables  <catalog.schema> [like]   SHOW TABLES (+ substring filter)
  dbx desc    <catalog.schema.table>    columns + types
  dbx sample  <catalog.schema.table> [N]
  dbx count   <catalog.schema.table> ["where clause"]
  dbx pr                                print resolved PR number

  dbx batch <file.sql>                  run a labelled query batch
  dbx diff  <file.sql|SQL> --a K=V --b K=V   run the same batch twice, diff rows
  dbx runctx <run_id>                   execution_context / input / output probe
  dbx card   <run_id>                   gaf_aging_card probe
  dbx coefs  <run_id>                   coef / component / global / measures probe

Batch files use '-- @label' separators (optionally '-- @label key=c1,c2'):
  -- @row_counts
  SELECT COUNT(*) AS n FROM ${SCHEMA}.coef WHERE run_id = '${RUN}';
  -- @per_urn key=measurement_urn
  SELECT measurement_urn, COUNT(*) AS n FROM ${SCHEMA}.coef ... GROUP BY 1;

Variables: --var/-v KEY=VAL (repeatable) expands ${KEY} anywhere in the SQL.
For diff, --a/--b carry the two variable sets, e.g.
  dbx diff probes.sql -v RUN=123 \\
      --a SCHEMA=esxp_dev.gold_analytics \\
      --b SCHEMA=esxp_dev_pr.pr{pr}_gold_analytics --key pov_id

PR-scoped schemas are named pr<N>_<schema>. The token {pr} in any SQL/table arg
expands to the resolved PR number:
  dbx --pr auto count 'esxp_dev_pr.pr{pr}_gold_analytics.coef' "measurement_value IS NULL"

Global flags (anywhere): --profile P --warehouse ID --pr N|auto --repo DIR
  --var/-v K=V --schema catalog.schema --key c1,c2 --max-diff N
  --json --csv --limit N --no-limit --max-col N
Env: DBX_WAREHOUSE, DBX_PR, DBX_REPO, DBX_SCHEMA
"""
from __future__ import annotations

import configparser
import json
import os
import re
import subprocess
import sys
from pathlib import Path

from databricks import sql

DEFAULT_WAREHOUSE = "0632bd3c72a82b45"  # dev workspace: reads esxp_dev, esxp_dev_pr, esxp_uat
PROFILE_WAREHOUSE = {"prd": "69bc4af4cdee445f"}  # esxp_prd is a separate workspace
DEFAULT_SCHEMA = "esxp_dev.gold_analytics"
PROBE_CMDS = {"runctx", "card", "coefs"}
KNOWN_CMDS = {"schemas", "tables", "desc", "sample", "count", "pr", "sql", "batch", "diff"} | PROBE_CMDS
META_CMDS = {"tables", "desc", "sample", "count", "schemas"}


# ---- argument parsing (hand-rolled so bare SQL stays ergonomic) -------------
FLAGS_WITH_VALUE = {"--profile", "--warehouse", "--pr", "--repo", "--limit", "--max-col",
                    "--schema", "--key", "--max-diff", "--sql-a", "--sql-b"}
FLAGS_REPEATED = {"--var": "var", "-v": "var", "--a": "a", "--b": "b"}
FLAGS_BOOL = {"--json", "--csv", "--no-limit"}


def parse_args(argv: list[str]) -> tuple[dict, list[str]]:
    opts: dict = {}
    pos: list[str] = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a in FLAGS_REPEATED:
            opts.setdefault(FLAGS_REPEATED[a], []).append(argv[i + 1])
            i += 2
        elif a in FLAGS_WITH_VALUE:
            opts[a.lstrip("-")] = argv[i + 1]
            i += 2
        elif a in FLAGS_BOOL:
            opts[a.lstrip("-")] = True
            i += 1
        else:
            pos.append(a)
            i += 1
    return opts, pos


# ---- connection -------------------------------------------------------------
def connect(profile: str, warehouse: str):
    cfg = configparser.ConfigParser()
    read = cfg.read(Path.home() / ".databrickscfg")
    if not read or profile not in cfg:
        sys.exit(f"dbx: profile '{profile}' not found in ~/.databrickscfg")
    host = cfg[profile]["host"].replace("https://", "").rstrip("/")
    token = cfg[profile]["token"]
    wh = warehouse if warehouse.startswith("/sql/") else f"/sql/1.0/warehouses/{warehouse}"
    return sql.connect(server_hostname=host, http_path=wh, access_token=token)


# ---- PR resolution ----------------------------------------------------------
_PR_CACHE: dict = {}


def resolve_pr(pr_arg: str | None, repo: str) -> str:
    if pr_arg and pr_arg != "auto":
        return str(pr_arg)
    if os.environ.get("DBX_PR"):
        return os.environ["DBX_PR"]
    if "n" in _PR_CACHE:
        return _PR_CACHE["n"]
    n = _gh_pr(repo) or _branch_pr(repo)
    if not n:
        sys.exit("dbx: could not resolve PR number; pass --pr N or set DBX_PR")
    _PR_CACHE["n"] = n
    return n


def _gh_pr(repo: str) -> str | None:
    try:
        r = subprocess.run(
            ["gh", "pr", "view", "--json", "number", "--jq", ".number"],
            cwd=repo, capture_output=True, text=True, timeout=20,
        )
        s = r.stdout.strip()
        return s if r.returncode == 0 and s.isdigit() else None
    except (OSError, subprocess.SubprocessError):
        return None


def _branch_pr(repo: str) -> str | None:
    try:
        r = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=repo, capture_output=True, text=True, timeout=10,
        )
        m = re.search(r"pr[-_/]?(\d+)", r.stdout, re.I)
        return m.group(1) if m else None
    except (OSError, subprocess.SubprocessError):
        return None


def subst_pr(text: str, opts: dict) -> str:
    if "{pr}" not in text:
        return text
    repo = opts.get("repo") or os.environ.get("DBX_REPO") or os.getcwd()
    return text.replace("{pr}", resolve_pr(opts.get("pr"), repo))


# ---- variables --------------------------------------------------------------
def parse_vars(items: list[str] | None) -> dict[str, str]:
    out: dict[str, str] = {}
    for it in items or []:
        if "=" not in it:
            sys.exit(f"dbx: bad variable '{it}', expected KEY=VALUE")
        k, v = it.split("=", 1)
        out[k.strip()] = v
    return out


def subst_vars(text: str, variables: dict[str, str]) -> str:
    if not variables:
        return text
    def repl(m: re.Match) -> str:
        k = m.group(1)
        if k not in variables:
            sys.exit(f"dbx: undefined variable ${{{k}}}")
        return variables[k]
    return re.sub(r"\$\{(\w+)\}", repl, text)


def schema_of(opts: dict) -> str:
    return opts.get("schema") or os.environ.get("DBX_SCHEMA") or DEFAULT_SCHEMA


# ---- SQL building -----------------------------------------------------------
def split_statements(sql_text: str) -> list[str]:
    # Split on ';' while ignoring separators inside '...', "...", or `...`.
    stmts: list[str] = []
    buf: list[str] = []
    quote: str | None = None
    i, n = 0, len(sql_text)
    while i < n:
        c = sql_text[i]
        if quote:
            buf.append(c)
            if c == quote:
                if i + 1 < n and sql_text[i + 1] == quote:  # escaped '' "" ``
                    buf.append(sql_text[i + 1])
                    i += 2
                    continue
                quote = None
        elif c in "'\"`":
            quote = c
            buf.append(c)
        elif c == ";":
            stmts.append("".join(buf))
            buf = []
        else:
            buf.append(c)
        i += 1
    stmts.append("".join(buf))
    return [s.strip() for s in stmts if s.strip()]


def maybe_limit(stmt: str, opts: dict) -> str:
    if opts.get("no-limit"):
        return stmt
    if not re.match(r"(?is)^\s*select\b", stmt):
        return stmt
    if re.search(r"(?is)\blimit\s+\d+\s*$", stmt):
        return stmt
    return f"{stmt} LIMIT {opts.get('limit', 100)}"


# ---- labelled batches -------------------------------------------------------
_LABEL_RE = re.compile(r"^\s*--\s*@(\S+)\s*(.*)$")


def parse_batch(text: str) -> list[tuple[str, str, list[str]]]:
    """Return [(label, sql, key_cols)] from '-- @label [key=c1,c2]' sections."""
    blocks: list[tuple[str, str, list[str]]] = []
    label, keys, buf = "query", [], []
    seen_label = False
    for line in text.splitlines():
        m = _LABEL_RE.match(line)
        if not m:
            buf.append(line)
            continue
        if seen_label or "".join(buf).strip():
            blocks.append((label, "\n".join(buf), keys))
        seen_label = True
        label = m.group(1)
        keys = _parse_key_attr(m.group(2))
        buf = []
    blocks.append((label, "\n".join(buf), keys))
    return [(lb, s, k) for lb, s, k in blocks if s.strip()]


def _parse_key_attr(attrs: str) -> list[str]:
    m = re.search(r"key\s*=\s*([\w,.\s]+)", attrs)
    return [c.strip() for c in m.group(1).split(",") if c.strip()] if m else []


def read_source(arg: str) -> str:
    p = Path(arg).expanduser()
    return p.read_text(encoding="utf-8") if p.is_file() else arg


# ---- output -----------------------------------------------------------------
def emit(cols: list[str], rows: list, opts: dict) -> None:
    if cols is None:
        return
    if opts.get("json"):
        for r in rows:
            print(json.dumps(dict(zip(cols, [_j(v) for v in r])), default=str))
    elif opts.get("csv"):
        print(",".join(cols))
        for r in rows:
            print(",".join(_csv(v) for v in r))
    else:
        _table(cols, rows, int(opts.get("max-col", 60)))
    print(f"({len(rows)} row{'s' if len(rows) != 1 else ''})", file=sys.stderr)


def _j(v):
    return v


def _csv(v) -> str:
    s = "" if v is None else str(v)
    return f'"{s}"' if any(c in s for c in ',"\n') else s


def _table(cols: list[str], rows: list, max_col: int) -> None:
    def cell(v) -> str:
        s = "" if v is None else str(v)
        return s if len(s) <= max_col else s[: max_col - 1] + "\u2026"

    data = [[cell(v) for v in r] for r in rows]
    widths = [len(c) for c in cols]
    for r in data:
        for i, v in enumerate(r):
            widths[i] = max(widths[i], len(v))
    print(" | ".join(c.ljust(widths[i]) for i, c in enumerate(cols)))
    print("-+-".join("-" * w for w in widths))
    for r in data:
        print(" | ".join(v.ljust(widths[i]) for i, v in enumerate(r)))


# ---- built-in probes --------------------------------------------------------
def _coef_probe(schema: str, table: str, run_id: str) -> str:
    return (
        f"SELECT measurement_urn, COUNT(*) AS n, COUNT(DISTINCT pov_id) AS povs,"
        f" SUM(CASE WHEN measurement_value IS NULL THEN 1 ELSE 0 END) AS nulls,"
        f" ROUND(MIN(measurement_value), 4) AS min_v,"
        f" ROUND(AVG(measurement_value), 4) AS avg_v,"
        f" ROUND(MAX(measurement_value), 4) AS max_v"
        f" FROM {schema}.{table} WHERE run_id = '{run_id}' GROUP BY 1 ORDER BY 1"
    )


def probe_plan(cmd: str, run_id: str, schema: str) -> list[tuple[str, str, list[str]]]:
    if cmd == "runctx":
        return [
            ("context", f"SELECT COUNT(*) AS rows, COUNT(DISTINCT root_pov_id) AS roots,"
                        f" COUNT(DISTINCT child_pov_id) AS children, MIN(_creation_date) AS first_seen,"
                        f" MAX(_creation_date) AS last_seen"
                        f" FROM {schema}.execution_context WHERE run_id = '{run_id}'", []),
            ("roots_by_urn", f"SELECT root_pov_urn, COUNT(DISTINCT root_pov_id) AS roots"
                             f" FROM {schema}.execution_context WHERE run_id = '{run_id}'"
                             f" GROUP BY 1 ORDER BY 2 DESC", ["root_pov_urn"]),
            ("inputs", f"SELECT input_type, COUNT(*) AS n, COUNT(DISTINCT measurement_urn) AS urns,"
                       f" COUNT(DISTINCT child_pov_id) AS povs"
                       f" FROM {schema}.execution_context_input WHERE run_id = '{run_id}'"
                       f" GROUP BY 1 ORDER BY 2 DESC", ["input_type"]),
            ("outputs", f"SELECT COUNT(*) AS n, COUNT(DISTINCT measurement_urn) AS urns,"
                        f" COUNT(DISTINCT child_pov_id) AS povs"
                        f" FROM {schema}.execution_context_output WHERE run_id = '{run_id}'", []),
        ]
    if cmd == "card":
        return [
            ("cards", f"SELECT COUNT(*) AS n, COUNT(DISTINCT asset_id) AS assets,"
                      f" MIN(_creation_date) AS first_seen, MAX(_creation_date) AS last_seen"
                      f" FROM {schema}.gaf_aging_card WHERE run_id = '{run_id}'", []),
            ("per_asset", f"SELECT asset_id, COUNT(*) AS n, MAX(_creation_date) AS last_seen,"
                          f" LENGTH(MAX(aging_card)) AS card_len"
                          f" FROM {schema}.gaf_aging_card WHERE run_id = '{run_id}'"
                          f" GROUP BY 1 ORDER BY 1", ["asset_id"]),
        ]
    return [
        ("coef", _coef_probe(schema, "coef", run_id), ["measurement_urn"]),
        ("component_coef", _coef_probe(schema, "component_coef", run_id), ["measurement_urn"]),
        ("global_coef", _coef_probe(schema, "global_coef", run_id), ["measurement_urn"]),
        ("attention_global_coef", _coef_probe(schema, "attention_global_coef", run_id), ["measurement_urn"]),
        ("computed_measures", _coef_probe(schema, "computed_measures", run_id), ["measurement_urn"]),
    ]


# ---- command dispatch -------------------------------------------------------
def build_plan(pos: list[str], opts: dict) -> list[tuple[str, str, list[str]]] | None:
    """Return [(label, sql, key_cols)]; label '' means 'no header'."""
    cmd = pos[0] if pos and pos[0] in KNOWN_CMDS else None
    rest = pos[1:] if cmd else pos

    if cmd == "pr":
        repo = opts.get("repo") or os.environ.get("DBX_REPO") or os.getcwd()
        print(resolve_pr(opts.get("pr"), repo))
        return None
    if cmd in PROBE_CMDS:
        if not rest:
            sys.exit(f"dbx: {cmd} needs a run_id")
        return probe_plan(cmd, rest[0], schema_of(opts))
    if cmd in {"batch", "diff"}:
        if not rest and not (opts.get("sql-a") and opts.get("sql-b")):
            sys.exit(f"dbx: {cmd} needs a .sql file or an inline query")
        return parse_batch(read_source(rest[0])) if rest else []
    if cmd == "schemas":
        return [("", f"SHOW SCHEMAS IN {rest[0]}", [])]
    if cmd == "tables":
        return [("", f"SHOW TABLES IN {rest[0]}", [])]  # like-filter applied post-query
    if cmd == "desc":
        return [("", f"DESCRIBE TABLE {rest[0]}", [])]
    if cmd == "sample":
        n = rest[1] if len(rest) > 1 else "10"
        return [("", f"SELECT * FROM {rest[0]} LIMIT {n}", [])]
    if cmd == "count":
        where = f" WHERE {rest[1]}" if len(rest) > 1 else ""
        return [("", f"SELECT COUNT(*) AS n FROM {rest[0]}{where}", [])]
    return [("", " ".join(rest), [])]  # bare SQL (optionally after 'sql')


# ---- execution --------------------------------------------------------------
def run_stmt(cur, stmt: str) -> tuple[list[str] | None, list]:
    cur.execute(stmt)
    if cur.description is None:
        return None, []
    return [d[0] for d in cur.description], list(cur.fetchall())


def prepare(sql_text: str, opts: dict, variables: dict[str, str]) -> str:
    return subst_vars(subst_pr(sql_text, opts), variables)


def run_batch(cur, plan, opts: dict, variables: dict, cmd: str | None, like: str | None) -> None:
    for label, raw, _keys in plan:
        for stmt in split_statements(prepare(raw, opts, variables)):
            if cmd not in META_CMDS:
                stmt = maybe_limit(stmt, opts)
            if label:
                print(f"\n== {label} ==")
            cols, rows = run_stmt(cur, stmt)
            if cols is None:
                continue
            if like is not None:
                rows = [r for r in rows if any(like in str(v).lower() for v in r)]
            emit(cols, rows, opts)


# ---- diff -------------------------------------------------------------------
def _key_index(cols: list[str], keys: list[str]) -> list[int]:
    missing = [k for k in keys if k not in cols]
    if missing:
        sys.exit(f"dbx: --key column(s) not in result: {', '.join(missing)}")
    return [cols.index(k) for k in keys]


def _index_rows(cols: list[str], rows: list, keys: list[str]) -> dict:
    idx = _key_index(cols, keys)
    out: dict = {}
    for r in rows:
        out.setdefault(tuple(str(r[i]) for i in idx), []).append(tuple(r))
    return out


def _fmt(row: tuple) -> str:
    return " | ".join("" if v is None else str(v) for v in row)


def diff_keyed(cols: list[str], a_rows: list, b_rows: list, keys: list[str], cap: int) -> None:
    a, b = _index_rows(cols, a_rows, keys), _index_rows(cols, b_rows, keys)
    only_a = sorted(set(a) - set(b))
    only_b = sorted(set(b) - set(a))
    changed = [k for k in sorted(set(a) & set(b)) if a[k] != b[k]]
    print(f"  rows: A={len(a_rows)} B={len(b_rows)} | key={','.join(keys)}"
          f" | only_A={len(only_a)} only_B={len(only_b)} changed={len(changed)}")
    for k in only_a[:cap]:
        print(f"  -A {_fmt(a[k][0])}")
    for k in only_b[:cap]:
        print(f"  +B {_fmt(b[k][0])}")
    for k in changed[:cap]:
        for col, av, bv in zip(cols, a[k][0], b[k][0]):
            if av != bv:
                print(f"  ~  {'/'.join(k)} {col}: {av} -> {bv}")


def diff_unkeyed(a_rows: list, b_rows: list, cap: int) -> None:
    a, b = {tuple(r) for r in a_rows}, {tuple(r) for r in b_rows}
    only_a, only_b = sorted(a - b, key=_fmt), sorted(b - a, key=_fmt)
    print(f"  rows: A={len(a_rows)} B={len(b_rows)} | only_A={len(only_a)} only_B={len(only_b)}")
    for r in only_a[:cap]:
        print(f"  -A {_fmt(r)}")
    for r in only_b[:cap]:
        print(f"  +B {_fmt(r)}")


def run_diff(cur, plan, opts: dict, base_vars: dict) -> None:
    a_vars = {**base_vars, **parse_vars(opts.get("a"))}
    b_vars = {**base_vars, **parse_vars(opts.get("b"))}
    cap = int(opts.get("max-diff", 20))
    cli_keys = [c.strip() for c in opts.get("key", "").split(",") if c.strip()]
    if opts.get("sql-a") and opts.get("sql-b"):
        plan = [("query", "", cli_keys)]
    for label, raw, keys in plan:
        keys = cli_keys or keys
        sql_a = opts.get("sql-a") or raw
        sql_b = opts.get("sql-b") or raw
        a_cols, a_rows = run_stmt(cur, maybe_limit(prepare(sql_a, opts, a_vars).strip().rstrip(";"), opts))
        b_cols, b_rows = run_stmt(cur, maybe_limit(prepare(sql_b, opts, b_vars).strip().rstrip(";"), opts))
        print(f"\n== {label} ==")
        if a_cols is None or b_cols is None:
            print("  (no result set)")
            continue
        if a_cols != b_cols:
            print(f"  !! column mismatch: A={a_cols} B={b_cols}")
            continue
        if keys:
            diff_keyed(a_cols, a_rows, b_rows, keys, cap)
        else:
            diff_unkeyed(a_rows, b_rows, cap)


def main() -> None:
    opts, pos = parse_args(sys.argv[1:])
    if not pos:
        sys.exit(__doc__)

    cmd = pos[0] if pos[0] in KNOWN_CMDS else None
    plan = build_plan(pos, opts)
    if plan is None:  # handled inline (pr)
        return
    if not plan and cmd != "diff":
        sys.exit("dbx: empty query")

    variables = parse_vars(opts.get("var"))
    like = pos[2].lower() if cmd == "tables" and len(pos) > 2 else None
    profile = opts.get("profile", "dev")
    warehouse = (opts.get("warehouse") or os.environ.get("DBX_WAREHOUSE")
                 or PROFILE_WAREHOUSE.get(profile) or DEFAULT_WAREHOUSE)

    with connect(profile, warehouse) as conn:
        with conn.cursor() as cur:
            if cmd == "diff":
                run_diff(cur, plan, opts, variables)
            else:
                run_batch(cur, plan, opts, variables, cmd, like)


if __name__ == "__main__":
    main()
