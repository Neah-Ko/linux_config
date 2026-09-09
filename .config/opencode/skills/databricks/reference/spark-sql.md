# Spark SQL on Delta — gotchas

Databricks runs **Spark SQL** over Delta tables. It is not Postgres/ANSI. Common traps when a query throws `PARSE_SYNTAX_ERROR` (SQLSTATE 42601):

## Set literals / exploding arrays
`explode(array(...)) AS x` is **invalid in the SELECT list**. Use an inline `VALUES` table instead:

```sql
WITH roots AS (
  SELECT * FROM VALUES ('id-a'), ('id-b'), ('id-c') AS t(root_pov_id)
)
SELECT * FROM roots;
```

Or, if you must explode, use `LATERAL VIEW`:

```sql
SELECT x FROM (SELECT array('a','b') AS arr) LATERAL VIEW explode(arr) e AS x;
```

## Inline rows
```sql
SELECT * FROM VALUES (1,'a'), (2,'b') AS t(id, name);
```

## Typed literals
```sql
TIMESTAMP'2026-08-03 22:00:00'
DATE'2026-08-03'
INTERVAL 7 DAYS
```

## NaN / NULL
`isnan(x)` works only on FLOAT/DOUBLE and errors on NULL — always guard:
```sql
CASE WHEN value_numeric IS NULL OR isnan(value_numeric) THEN 1 ELSE 0 END
```

## Quoting
- Strings: **single quotes** `'text'`.
- Identifiers: **backticks** `` `weird col` `` — never double quotes.

## Casts
Use `CAST(x AS type)` or `try_cast(x AS type)`. There is **no** `x::type` syntax.

## Multi-statement
The `dbx` helper is literal-aware: `;` inside `'...'` / `"..."` / `` `...` `` does not split statements. Still keep `;` out of SQL comments in a multi-statement string.

## Other differences
- No `SELECT ... INTO`. Use `CREATE TABLE ... AS SELECT`.
- Boolean literals `true` / `false` (unquoted).
- `qualify`, `pivot`, `explode`, `posexplode`, `named_struct`, `map`, `array` are available.
- String funcs: `substring`, `split`, `regexp_extract`, `regexp_replace` (Java regex, not POSIX).
