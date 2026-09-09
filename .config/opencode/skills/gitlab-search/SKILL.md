---
name: gitlab-search
description: >
  Recherche sur l'instance GitLab Kaizen Solutions (https://forge.kaizen-solutions.net/).
  Permet de chercher des projets, issues, merge requests, code source (blobs), commits
  et autres ressources via l'API REST GitLab v4.
  Nécessite la variable d'environnement GITLAB_TOKEN (Personal Access Token avec scope read_api).
  Utiliser ce skill dès qu'une question porte sur la forge GitLab, les projets Kaizen,
  ou qu'il faut retrouver du code, des issues ou des MR sur forge.kaizen-solutions.net.
---

# GitLab Search

Recherche sur l'instance GitLab Kaizen Solutions via l'API REST v4.

## Prérequis

- Variable d'environnement `GITLAB_TOKEN` définie avec un Personal Access Token (scope `read_api`)

## Utilisation

Utiliser `curl` avec l'header `PRIVATE-TOKEN: $GITLAB_TOKEN` pour interroger l'API :

```bash
curl -s --header "PRIVATE-TOKEN: $GITLAB_TOKEN" "https://forge.kaizen-solutions.net/api/v4/<endpoint>"
```

## Endpoints courants

| Action | Endpoint |
|--------|----------|
| Lister les projets | `/api/v4/projects?per_page=100` |
| Chercher un projet | `/api/v4/projects?search=<mot>&per_page=100` |
| Issues d'un projet | `/api/v4/projects/<id>/issues` |
| Commits d'un projet | `/api/v4/projects/<id>/repository/commits` |
| Chercher du code | `/api/v4/projects/<id>/search?scope=blobs&search=<mot>` |
| Infos projet | `/api/v4/projects/<id>` |
