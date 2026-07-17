# Spec: ha-app-crw — CRW Web Tools (검색·스크레이핑 MCP 공급 App)

**Repo:** `saya6k/ha-app-crw` (신규) · **Slug:** `crw` · **Stage:** `experimental`
**Date:** 2026-07-17 (rev 2 — unix socket 경량화, aarch64 prebuilt 확정, interact/secret은 [ha-app-playwright](../ha-app-playwright/SPEC.md)로 분리)

## 0. 아키텍처 판정 (요청하신 확인 사항)

**App 단독으로는 conversation에 LLM intent(tool) 공급이 불가능하다.**

- HA 2026.8.0의 신규 구조([core#174253](https://github.com/home-assistant/core/pull/174253),
  `llm` integration)는 tool 공급 주체가 **integration**이다 — integration이
  `llm.py` platform 파일에서 `async_get_tools`를 구현하는 방식. HA core의
  Python 프로세스 안에서만 동작하므로, 컨테이너로 격리된 App은 접근 경로가 없다.
- jxlarrea의 voice-satellite-card-llm-tools도 실제로는 **custom integration**이다
  (구식 `llm.async_register_api` 사용). Visual card scheme은 integration이 반환한
  구조화 JSON을 카드가 렌더링하는 구조라서, integration 없이는 재현 불가.

→ 지시하신 fallback대로 **MCP 형태로 공급**한다. App이 **streamable HTTP
(`/mcp`)** MCP 서버를 노출하고, HA 공식
[MCP integration](https://www.home-assistant.io/integrations/mcp/)이 이를 tool로
변환해 Assist conversation agent에 제공한다. (웹 문서는 "SSE 전용"이라 하지만
core `mcp/coordinator.py` 확인 결과 **streamable HTTP 우선 + 405 시 SSE
fallback** — streamable HTTP가 정방향이다.)

**Visual card는 이번 scope에서 제외** (custom integration 필요). 단, MCP tool의
결과 JSON을 jxlarrea scheme(`{source, query, results: [{url, title, snippet,
site_name}], featured_image, instruction}`)과 동일한 형태로 반환해 두어, 추후
integration을 만들거나 카드가 MCP tool trace를 지원하게 되면 그대로 호환된다.

**브라우저 자동화(Firecrawl Interact 대응 = crw-browse)와 Infisical secret은
이 앱에 넣지 않는다** — 별도 앱 `ha-app-playwright`로 분리 (해당 SPEC 참조).

## 1. Objective

HA App 컨테이너 하나에 s6-overlay v3로 세 서비스를 묶는다:

```
┌─ ha-app crw ────────────────────────────────────────────────┐
│  searxng      UDS /run/crw/searxng.sock   메타 검색 (JSON)   │
│  crw-server   127.0.0.1:3000              스크레이핑 전용     │
│  mcp-bridge   0.0.0.0:8099   MCP 서버 (streamable HTTP /mcp) │
│     ├─ tool web_search  → SearXNG UDS 직접 호출⁽*⁾           │
│     └─ tool web_scrape  → crw POST /v1/scrape                │
└──────────────────────────────────────────────────────────────┘
        ▲ http://03f32180-crw:8099/mcp (HA 내부 네트워크)
   HA 공식 MCP integration → llm tool → conversation agent
```

⁽*⁾ 확정(T3): crw의 `/v1/search`는 자체 백엔드가 아니라 **외부 SearXNG URL이
필수**(`CRW_SEARCH__SEARXNG_URL`)이고 UDS 클라이언트 지원은 불확실하다. 경량화
원칙에 따라 bridge가 SearXNG JSON API를 UDS로 직접 호출하고, crw는
`CRW_SEARCH__ENABLED=false`로 스크레이핑 전용으로 둔다 — 검색은 항상 SearXNG를
거친다는 요구를 더 짧은 경로로 충족.

**내부 통신은 가능한 곳 전부 unix domain socket** (경량화·포트 무노출):
- searxng: granian/uwsgi UDS 바인드, bridge·crw는 UDS로 호출 (httpx UDS transport)
- crw-server: UDS 지원 시 UDS, 미지원이면 127.0.0.1 TCP (§10-2)
- bridge의 MCP 엔드포인트(8099)만 TCP — HA가 접속해야 하는 유일한 표면

**Auto discovery — Supervisor discovery로 준비, mDNS는 채택 안 함:**
- `config.yaml`에 `discovery: [mcp]` 선언 + 기동 시
  `bashio::discovery "mcp" '{"url": "http://<hostname>:8099/mcp"}'` announce.
  Supervisor는 임의 service 이름을 허용하므로(validate.py 확인) app 쪽은 무해하게
  선제 적용 가능. 단 **core `mcp` integration에 `async_step_hassio`가 없어**
  현재는 수신부가 없음 — upstream PR 전까지 사용자는 URL 수동 입력 (§11-6).
- mDNS/zeroconf는 부적합: `mcp` manifest에 zeroconf 선언이 없어 HA가 아예 듣지
  않고, 컨테이너에서 mDNS 멀티캐스트를 하려면 `host_network: true`로 격리를
  포기해야 함. 채택하지 않는다.

- SearXNG-Crawl4AI는 설계 참조(검색/본문 추출 분리 구조)로만 사용, 번들 안 함 —
  Crawl4AI(Playwright/Chromium)는 이미지가 수 GB로 비대.
- Tool은 `web_search`, `web_scrape` 두 개만 (crawl/map/extract는 대화 턴에
  부적합, interact는 ha-app-playwright 담당).

**User stories:**
1. "어제 발표된 ○○ 소식 찾아줘" → agent가 `web_search` 호출 → SearXNG 결과를
   요약해 음성/텍스트로 답변.
2. "이 페이지 내용 요약해줘 (URL)" → `web_scrape` → crw가 마크다운으로 변환한
   본문을 agent가 요약.

## 2. Tech Stack

| 구성 | 선택 | 비고 |
|---|---|---|
| Base image | HA add-on base (`ARG BUILD_FROM`), s6-overlay v3 | ha-apps 표준 |
| 검색 | SearXNG (버전 pin) | `settings.yml`에 `format: [json]` 허용 + UDS 바인드 |
| 스크레이핑 | **crw-server v0.25.x prebuilt** — `crw-server-linux-{x64,arm64}.tar.gz` | GitHub release asset 확인 완료, cargo build 불필요. AGPL-3.0 고지 필요 |
| MCP bridge | Python 3.12+, `mcp` SDK(FastMCP, **streamable HTTP transport**), `httpx`(UDS transport) | HA MCP integration이 streamable HTTP 우선 지원(core 확인). SSE 별도 제공 불필요 |
| Arch | `amd64`, `aarch64` | 두 아치 모두 prebuilt 존재 |

## 3. Commands

로컬 빌드는 이 Mac(M1)에서 직접 불가 — `linux-test` container machine 사용
(user CLAUDE.md의 Docker 절차 준수).

```bash
# Lint (app-preflight 스킬과 동일)
yamllint crw/config.yaml crw/translations/*.yaml
shellcheck crw/rootfs/etc/s6-overlay/s6-rc.d/*/run crw/rootfs/etc/s6-overlay/s6-rc.d/*/finish
hadolint crw/Dockerfile
python3 -m py_compile crw/rootfs/opt/mcp-bridge/*.py

# Bridge 단위 테스트
cd crw/rootfs/opt/mcp-bridge && python3 -m pytest

# Build (linux-test machine 경유; dockerd 기동 후)
container machine run --root -n linux-test -- docker build \
  --build-arg BUILD_FROM=ghcr.io/home-assistant/aarch64-base:latest \
  /Users/saya6k/Projects/ha-app-crw/crw

# Runtime smoke (machine run의 compound command quoting 제약 → 스크립트 파일 경유)
container machine run --root -n linux-test -- sh ~/scripts/crw-smoke.sh
```

## 4. Project Structure (ha-app-* 표준, wardrowbe 템플릿 기반)

```
crw/                              ← 서브프로젝트 (slug)
  config.yaml                     ← image: 없음 (ha-apps 쪽에만), ports: 8099/tcp
  Dockerfile                      ← ARG BUILD_FROM, 아치별 crw-server prebuilt
                                    다운로드(+checksum), COPY rootfs /, s6 chmod
  apparmor.txt
  rootfs/
    etc/s6-overlay/s6-rc.d/
      searxng/    run·finish·type (longrun)
      crw/        run·finish·type (longrun)
      mcp-bridge/ run·finish·type (longrun, searxng·crw 이후 기동)
      user/contents.d/…
    etc/searxng/settings.yml      ← json format, UDS, 엔진 기본셋
    opt/mcp-bridge/               ← FastMCP 서버 (server.py, tools.py, tests/)
  translations/{en,ko}.yaml
  AGENTS.md · DOCS.md · .README.j2 · icon.png · logo.png
.github/
  workflows/ci.yml                ← lint + unit + build-test (amd64/aarch64 matrix)
  workflows/build.yml             ← GHCR publish + ha-apps dispatch (notify/notify-beta)
  workflows/release-drafter.yml   ← 2-track (draft + draft-prerelease)
  release-drafter.yml · release-drafter-prerelease.yml
.agents/{workflows,skills}/ + .claude/ symlink   ← new-app-scaffold §4
.hadolint.yaml · .markdownlint.yaml · .shellcheckrc · .yamllint · .gitattributes(LF)
SPEC.md                           ← 이 문서
```

Repo 생성·secret(`CATALOG_PAT`)·초기 릴리스는
`~/Projects/.agents/workflows/new-app-scaffold.md` Part A 절차를 그대로 따른다.

## 5. config.yaml 옵션 (사용자 knob)

```yaml
options:
  max_search_results: 3   # 1–6
  safe_search: 1          # 0/1/2 (SearXNG)
```

(schema 키 알파벳 순 · en/ko 번역 쌍 필수. SearXNG 엔진 커스텀은 §10-3)

## 6. Code Style

s6 run 스크립트 — 기존 앱들과 동일한 bashio 스타일:

```bash
#!/command/with-contenv bashio
# shellcheck shell=bash
set -euo pipefail

bashio::log.info "Starting crw-server …"
exec /usr/local/bin/crw-server --host 127.0.0.1 --port 3000
```

MCP bridge(Python) — tool 결과는 jxlarrea scheme 그대로:

```python
@mcp.tool()
async def web_search(query: str, num_results: int = 3) -> dict:
    """Search the internet for current information on a topic."""
    rows = await search_backend(query, num_results)   # crw /v1/search 또는 SearXNG UDS
    return {
        "source": "searxng",
        "query": query,
        "num_results": len(rows),
        "results": [
            {"url": r["url"], "title": r["title"],
             "snippet": r.get("content", ""), "site_name": site_name(r["url"])}
            for r in rows
        ],
        "featured_image": featured_image(rows),
        "instruction": (
            "Summarize the key information from these search results in 2-3 "
            "concise sentences. Do NOT list individual URLs or sources."
        ),
    }
```

컨벤션: 커밋은 conventional commit(`feat(crw): …`) · 번역은 en/ko 쌍으로 ·
`config.yaml` schema 키는 알파벳 순 유지 · LF 전용 · 버전 전부 pin.

## 7. Testing Strategy

| 레벨 | 내용 | 어디서 |
|---|---|---|
| Lint | yamllint · shellcheck · hadolint · py_compile | 로컬 + `ci.yml` |
| Unit (pytest) | 결과 포매팅(scheme) · site_name/featured_image 추출 (백엔드는 httpx mock) | 로컬 + `ci.yml` |
| Build | 두 아키텍처 docker build 성공 | `ci.yml` matrix |
| Smoke | 컨테이너 기동 후: ① SearXNG UDS `GET /search?q=test&format=json` 200 ② crw `POST /v1/scrape` 200+markdown ③ bridge `/mcp` initialize(streamable HTTP) → `tools/list`에 web_search·web_scrape → `tools/call web_search` 결과 scheme 검증 | linux-test 스크립트, CI에도 편입 |
| HA E2E (수동) | 실제 HA에 설치 → MCP integration에 `http://03f32180-crw:8099/mcp` 등록 → Assist에서 user story 1·2 재현 | 릴리스 전 체크리스트 (DOCS.md에 절차 기록) |

## 8. Boundaries

**Always:**
- ha-apps Invariants 준수: LF 전용, `config.yaml`은 서브프로젝트 루트에만,
  lint 설정은 repo 루트에만, `--no-verify`/`--no-gpg-sign` 금지.
- 커밋 전 app-preflight(lint 3종 + py_compile) 통과.
- 내부 서비스는 UDS 우선(불가 시 127.0.0.1) — 외부 노출은 bridge(8099) 하나만.
- 버전 pin: SearXNG·crw-server·mcp SDK 모두 고정 버전 + prebuilt checksum 검증.

**Ask first:**
- `ports`/`privileged`/apparmor capability 등 config.yaml 권한 표면 변경.
- 서비스 추가, 의존성 추가, tool 추가(extract·crawl 등).
- CI 워크플로 구조 변경, ha-apps(카탈로그) 쪽 파일 생성.
- MCP 인증 방식 결정(현재: 내부 네트워크 한정 무인증 — 외부 포트 여는 순간 재논의).

**Never:**
- Secret/API key 커밋. crw cloud(`api.fastcrw.com`) 사용 금지 — 전부 self-hosted.
- 사용자 검색 쿼리를 컨테이너 밖으로 로깅/전송 (SearXNG 프라이버시 원칙).
- 브라우저 자동화·secret 기능을 이 앱에 추가 (ha-app-playwright 소관).
- 기존 ha-app-* repo나 ha-apps를 이 작업에서 임의 수정.

## 9. Success Criteria

1. `ci.yml` green: lint + unit 전부 통과 + amd64/aarch64 빌드 성공.
2. linux-test smoke: 세 서비스 기동, §7 Smoke ①–③ 모두 통과.
3. 실제 HA(2026.7+)에서: App 설치 → MCP integration 연결 → Assist 대화에서
   검색 질의가 `web_search` tool 호출로 이어지고, 웹 검색 결과에 근거한 답변이
   돌아온다 (user story 1·2 재현).
4. 릴리스 파이프라인: draft publish → `ghcr.io/saya6k/app-crw:{ver}` 멀티아치
   manifest 푸시 → ha-apps dispatch 동작 (카탈로그 등록 자체는 out of scope).

## 10. Phases

1. **Scaffold** — new-app-scaffold Part A (repo 생성, wardrowbe 템플릿, CI 2-track). → verify: lint green
2. **Services** — Dockerfile(prebuilt 다운로드) + s6 (searxng UDS, crw-server) + settings.yml. → verify: build + smoke ①②
3. **MCP bridge** — FastMCP streamable HTTP 서버, tool 2종, scheme 포매팅 + pytest. → verify: smoke ③
4. **Docs/Release** — DOCS.md(HA MCP 연결 절차·AGPL 고지), .README.j2, translations, 초기 릴리스. → verify: success criteria 4

**Out of scope (이번 spec):** ha-apps 카탈로그 메타데이터(Part B, 별도 진행),
custom integration + visual card 렌더링, crawl/map/extract tool,
브라우저 자동화(interact)·Infisical secret([ha-app-playwright](../ha-app-playwright/SPEC.md)).

## 11. Open Questions

1. ~~crw-server ↔ 번들 SearXNG 연결 설정~~ → **확정(T3)**: crw 검색은
   `CRW_SEARCH__SEARXNG_URL` 필수(자체 백엔드 없음). bridge가 SearXNG를 UDS로
   직접 호출하고 crw는 `CRW_SEARCH__ENABLED=false` (§1 ⁽*⁾ 참조).
2. ~~crw-server UDS 바인드 지원 여부~~ → **확정(T3)**: 미지원 (CLI는 setup
   서브커맨드뿐, `CRW_SERVER__HOST/PORT` env로 127.0.0.1:3000 바인드).
3. **SearXNG 엔진 기본셋과 knob 확장** — 엔진 선택을 사용자 옵션으로 열지
   (기본안: settings.yml 고정, 요청 오면 `engines` 리스트 옵션 추가).
4. **crw 자체 `/mcp` 직결로 bridge 대체 가능성** — transport는 이제 문제없음
   (streamable HTTP 상호 지원). 남는 쟁점: crw MCP의 tool 표면을 2종으로 제한할
   수 있는지, 검색이 번들 SearXNG를 경유하는지(§11-1), jxlarrea 결과 scheme
   포기 여부. 셋 다 충족되면 bridge를 제거해 더 경량화할 수 있다 — Phase 3
   착수 전 판단.
5. **crw AGPL-3.0** — 이미지에 소스 링크 고지 방식 (DOCS.md + 라벨로 충분한지).
