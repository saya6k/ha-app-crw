# ha-app-crw

Source repo for the **CRW Web Tools** Home Assistant app — web search
(SearXNG) and page scraping ([crw](https://github.com/us/crw)) supplied to
Assist conversation agents over MCP (streamable HTTP).

Install it from the [saya6k/ha-apps](https://github.com/saya6k/ha-apps)
catalog. This repo carries the source, Dockerfile, and CI; the catalog carries
the metadata.

- App docs: [crw/DOCS.md](crw/DOCS.md)
- Design spec: [SPEC.md](SPEC.md)
- Task plan: [tasks/plan.md](tasks/plan.md)

## Release flow

1. Merge to `main` — release-drafter updates the draft.
2. Publish the draft → `build.yml` pushes `ghcr.io/saya6k/app-crw:{ver}`.
3. The build dispatches to ha-apps, which opens a version-bump PR.
