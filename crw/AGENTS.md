# crw — agent notes

MCP supply app: SearXNG(검색) + crw-server(스크레이핑) + mcp-bridge(FastMCP
streamable HTTP :8099 `/mcp`)를 s6-overlay v3로 묶는다. 설계 근거와 결정
사항은 repo 루트 `SPEC.md`, 작업 순서는 `tasks/plan.md`.

## Shape

```
crw/
  config.yaml           slug=crw, stage: experimental, discovery: [mcp]
  Dockerfile            crw-server prebuilt(아치별)+checksum, SearXNG, bridge
  rootfs/etc/s6-overlay/s6-rc.d/{searxng,crw,mcp-bridge}/   longrun 3종
  rootfs/etc/searxng/settings.yml     crw sidecar 기반, format json, loopback 8080
  rootfs/opt/mcp-bridge/              FastMCP 서버 + pytest tests/
  translations/{en,ko}.yaml
```

## Invariants (SPEC §8)

- 내부 서비스는 loopback 전용(searxng 8080, crw 3000) — 외부 표면은 8099 하나
- 검색 흐름은 fastcrw sidecar 패턴: bridge → crw /v1/search → SearXNG
- 검색은 항상 SearXNG 경유 · crw cloud 사용 금지
- web_search 결과는 jxlarrea scheme (`source/query/results[]/featured_image/instruction`)
- 버전 전부 pin + prebuilt checksum

## Preflight

```
yamllint crw/config.yaml crw/translations/*.yaml
shellcheck crw/rootfs/etc/s6-overlay/s6-rc.d/*/run
hadolint crw/Dockerfile
cd crw/rootfs/opt/mcp-bridge && python3 -m pytest
```

빌드/스모크는 linux-test container machine에서 (M1 제약, user CLAUDE.md 참조).
