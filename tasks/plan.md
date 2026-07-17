# Implementation Plan: ha-app-crw

SPEC.md(rev 2, 승인됨) 기준. Phase 1~4를 10개 태스크로 분해.

## Overview

검색(SearXNG)·스크레이핑(crw-server)을 streamable HTTP MCP(`/mcp`)로 HA
conversation에 공급하는 App. wardrowbe/otelcol 템플릿 + new-app-scaffold Part A
절차를 따르고, 빌드/스모크는 linux-test container machine에서 수행.

## Architecture Decisions (SPEC에서 확정)

- MCP-only 공급 (App은 llm platform에 직접 등록 불가) · bridge는 FastMCP
  **streamable HTTP** (core mcp integration이 streamable 우선임을 확인)
- 검색은 항상 SearXNG 경유 · 내부 통신은 UDS 우선 · 외부 표면은 8099 하나
- crw-server는 v0.25.x prebuilt (linux-x64/arm64) + checksum
- tool 2종: `web_search`(jxlarrea scheme), `web_scrape`
- Supervisor discovery(`discovery: [mcp]`) 선제 announce (수신부는 upstream 과제)

## Dependency Graph

```
T1 로컬 scaffold (템플릿·워크플로·lint 설정)
 ├─ T2 GitHub repo 셋업 (create·secret·권한·push)
 ├─ T3 Dockerfile + crw-server 서비스 ──┐  (musl/glibc 리스크 조기 검증)
 │    └─ T4 bridge 골격 + web_scrape ───┤  ← 수직 슬라이스 1 (scrape E2E)
 ├─ T5 SearXNG 서비스 (UDS) ────────────┤
 │    └─ T6 web_search + config 옵션 ───┘  ← 수직 슬라이스 2 (search E2E)
 ├─ T7 CI green (GitHub Actions)
 ├─ T8 스모크 스크립트 정리 + CI 편입
 └─ T9 문서·아이콘·번역 → T10 초기 릴리스 (GHCR 멀티아치)
```

---

## Task List

### Phase 1: Scaffold

#### Task 1: 로컬 repo scaffold

**Description:** wardrowbe를 rsync 템플릿으로 로컬 스켈레톤 생성. `crw/` 서브
프로젝트 디렉토리, `.github/workflows/`(ci·build·release-drafter 2-track,
otelcol 최신형 기준으로 slug 치환), `.agents/`+`.claude/` symlink, 루트 lint
설정, `.gitattributes`(LF).

**Acceptance criteria:**
- [ ] `crw/config.yaml`(image: 없음, ports 미공개, `discovery: [mcp]`),
      `translations/{en,ko}.yaml`, `AGENTS.md`·`DOCS.md`·`.README.j2` 스텁 존재
- [ ] 워크플로 5개 파일에 `wardrowbe`/`otelcol` 잔재 0 (slug=crw, IMAGE=app-crw)
- [ ] `.agents/workflows/app-dev-pr.md` + `app-preflight` 스킬 복사, symlink 동작

**Verification:**
- [ ] `yamllint crw/config.yaml crw/translations/*.yaml .github/**/*.yml` 통과
- [ ] `grep -ri wardrowbe . --exclude-dir=.git` 결과 없음

**Dependencies:** None · **Files:** ~15개 (템플릿 복사 위주) · **Scope:** M

#### Task 2: GitHub repo 셋업

**Description:** new-app-scaffold Part A §1·5·6·7 — `gh repo create
saya6k/ha-app-crw`, `CATALOG_PAT` secret, workflow write 권한, initial commit
push. (base release는 T10으로 연기 — 구현 전 릴리스는 빈 이미지를 만들므로.)

**Acceptance criteria:**
- [ ] repo 생성·push 완료, Actions에서 ci.yml 트리거됨 (실패해도 무방, T7에서 green화)
- [ ] `gh secret list`에 CATALOG_PAT, workflow 권한 write

**Verification:**
- [ ] `gh repo view saya6k/ha-app-crw` + `gh run list` 확인

**Dependencies:** T1 · **Files:** 0 (외부 셋업) · **Scope:** S

### Checkpoint A (Phase 1 완료)
- [ ] 로컬 lint 전부 통과 · repo push 완료 · 사용자 보고

### Phase 2: 수직 슬라이스 1 — web_scrape E2E

#### Task 3: Dockerfile + crw-server 서비스

**Description:** `ARG BUILD_FROM` Dockerfile: 아치별 crw-server v0.25.x prebuilt
다운로드+checksum 검증, s6 `crw/` longrun 서비스. **선결 확인:** prebuilt가
musl(Alpine)에서 실행되는지 — glibc 전용이면 debian base로 전환 결정(리스크 1).
crw UDS 바인드 지원 확인(SPEC §11-2) — 미지원 시 127.0.0.1:3000.

**Acceptance criteria:**
- [ ] linux-test에서 amd64·aarch64 둘 다 `docker build` 성공
- [ ] 컨테이너 기동 후 `POST /v1/scrape` (예: example.com) 200 + markdown 본문
- [ ] SPEC §11-2 (UDS) 답 확정되어 SPEC.md에 반영

**Verification:**
- [ ] `hadolint crw/Dockerfile` + shellcheck 통과, smoke ② 스크립트 통과

**Dependencies:** T1 · **Files:** Dockerfile, s6-rc.d/crw/{run,finish,type}, user/contents.d · **Scope:** M

#### Task 4: MCP bridge 골격 + web_scrape tool

**Description:** `rootfs/opt/mcp-bridge/` FastMCP streamable HTTP 서버(0.0.0.0:8099
`/mcp`) + `web_scrape` tool(crw /v1/scrape 호출) + s6 `mcp-bridge/` 서비스
(searxng·crw 이후 기동) + 기동 시 `bashio::discovery "mcp"` announce + pytest
(응답 포매팅, crw는 httpx mock).

**Acceptance criteria:**
- [ ] `/mcp` initialize → `tools/list`에 web_scrape → `tools/call`이 markdown 반환
- [ ] pytest 통과 (포매팅·에러 경로)
- [ ] discovery announce가 Supervisor 부재 환경에서도 무해(로그 후 계속)

**Verification:**
- [ ] smoke ③(scrape 한정) + `python3 -m pytest` + py_compile

**Dependencies:** T3 · **Files:** server.py, tools.py, tests/, s6-rc.d/mcp-bridge/*, requirements 고정 · **Scope:** M

### Checkpoint B (슬라이스 1)
- [ ] linux-test에서 scrape가 MCP 경유로 end-to-end 동작 · 빌드 2아치 green

### Phase 3: 수직 슬라이스 2 — web_search E2E

#### Task 5: SearXNG 서비스 (UDS)

**Description:** SearXNG 버전 pin 설치(Dockerfile 확장), `settings.yml`
(`format: [json]`, 엔진 기본셋, secret_key는 기동 시 생성), UDS
`/run/crw/searxng.sock` 바인드, s6 `searxng/` longrun.

**Acceptance criteria:**
- [ ] 컨테이너 내 UDS로 `GET /search?q=test&format=json` 200 + results 배열
- [ ] TCP 포트 미청취 (`netstat`으로 8888 등 부재 확인)

**Verification:**
- [ ] smoke ① 스크립트 통과, 빌드 2아치 성공 유지

**Dependencies:** T3 · **Files:** Dockerfile, settings.yml, s6-rc.d/searxng/* · **Scope:** M

#### Task 6: web_search tool + config 옵션 wiring

**Description:** SPEC §11-1 확정(crw /v1/search가 외부 SearXNG를 쓸 수 있는지 →
가능하면 crw 경유, 아니면 bridge가 UDS 직접 호출). `web_search` tool을 jxlarrea
scheme(`source/query/results[]/featured_image/instruction`)으로 구현,
`max_search_results`·`safe_search` 옵션을 bashio→env로 bridge에 전달. pytest.

**Acceptance criteria:**
- [ ] `tools/call web_search` 결과가 scheme 그대로 (unit + smoke에서 키 검증)
- [ ] 옵션 변경이 동작에 반영 (num_results 상한, safe_search 파라미터)
- [ ] SPEC §11-1 답 확정되어 SPEC.md에 반영

**Verification:**
- [ ] smoke ③ 전체 + pytest 통과

**Dependencies:** T4, T5 · **Files:** tools.py, server.py, run 스크립트, tests/ · **Scope:** M

### Checkpoint C (슬라이스 2)
- [ ] smoke ①②③ 전부 통과 (빌드~기동~tool 호출) · 사용자 보고

### Phase 4: CI·문서·릴리스

#### Task 7: CI green

**Description:** GitHub Actions에서 ci.yml 전 job(lint 4종 + pytest + 2아치
build-test) 통과하도록 정리. push하며 실패 요인 수정.

**Acceptance criteria:**
- [ ] `gh run list` 최신 run 전 job 성공

**Verification:**
- [ ] `gh run watch` green

**Dependencies:** T2, T6 · **Files:** ci.yml 미세수정 · **Scope:** S

#### Task 8: 스모크 스크립트 CI 편입

**Description:** linux-test용 smoke 스크립트(`crw-smoke.sh`)를 repo에 넣고
ci.yml build-test job에서 컨테이너 기동 후 실행하도록 편입 (amd64만 — QEMU
aarch64 기동은 느려서 빌드만).

**Acceptance criteria:**
- [ ] CI에서 smoke ①②③이 매 PR마다 실행·통과

**Verification:**
- [ ] 고의로 tool 이름을 깨는 브랜치에서 CI 실패 확인 후 revert

**Dependencies:** T7 · **Files:** scripts/smoke.sh, ci.yml · **Scope:** S

#### Task 9: 문서·아이콘·번역

**Description:** DOCS.md(HA MCP integration 연결 절차 — URL `http://03f32180-crw:8099/mcp`,
수동 등록 안내, AGPL-3.0 고지, 옵션 설명), `.README.j2` 한 단락, translations
en/ko 옵션 문자열, icon.png(256×256)/logo.png 생성, AGENTS.md 현행화.

**Acceptance criteria:**
- [ ] 문서 3종 + 번역 2종 + 이미지 2종 완비, markdownlint·yamllint 통과

**Verification:**
- [ ] app-preflight 전체 + `frenck/action-addon-linter` (CI) 통과

**Dependencies:** T6 · **Files:** DOCS.md, .README.j2, translations/*, icon/logo, AGENTS.md · **Scope:** M

#### Task 10: 초기 릴리스

**Description:** new-app-scaffold Part A §8 — `gh release create v0.1.0` →
build.yml이 `ghcr.io/saya6k/app-crw:0.1.0` + `:latest`·`:stable` 멀티아치
manifest 푸시 확인. **주의:** ha-apps에 `crw/`가 없어 notify dispatch의 sync가
불완전할 수 있음(Part B는 별도 작업) — 실패해도 릴리스 자체는 유효, 결과 보고.

**Acceptance criteria:**
- [ ] GHCR에 두 아치 manifest 존재 (`docker manifest inspect`)
- [ ] release-drafter가 다음 draft를 생성

**Verification:**
- [ ] `gh run watch` build.yml green(notify 제외 허용) + manifest inspect

**Dependencies:** T7, T8, T9 · **Files:** 0 · **Scope:** S

### Checkpoint D (완료)
- [ ] SPEC §9 Success Criteria 1·2·4 충족
- [ ] criteria 3(HA E2E)은 사용자 실기기 확인 항목으로 인계 (DOCS.md 절차 첨부)

---

## Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| crw prebuilt가 glibc 타깃 → Alpine(musl) 실행 불가 | High | T3 최초에 `file`/실행 확인. 불가 시 debian base 전환(브릿지·SearXNG 영향 없음) 또는 gcompat. fail-fast 배치 |
| SearXNG가 PyPI 미배포(git 설치) → 버전 pin·빌드 재현성 | Med | git tag pin + pip hash, 빌드 캐시. T5에서 확정 |
| crw /v1/search의 외부 SearXNG 연결 불가 (§11-1) | Low | bridge가 UDS 직접 호출로 대체 — 설계상 흡수됨 |
| 첫 릴리스 시 ha-apps dispatch 불완전 (Part B 미완) | Low | notify 실패 허용·보고. Part B는 후속 작업 |
| QEMU aarch64 빌드 시간 | Low | 빌드만 하고 smoke는 amd64 한정 |

## Open Questions (계획 단계에서 남김)

- ~~icon/logo 디자인~~ → 확정(사용자): SearXNG/Firecrawl 로고 활용.
  **SearXNG 브랜드 에셋 채택** (searxng repo `src/brand/`, 실제 번들 구성요소·
  AGPL 프로젝트 에셋) — Firecrawl 로고는 미사용 컴포넌트 브랜드라 오인 소지로
  회피, crw 마크가 있으면 조합 검토 (T9)
- 초기 버전 번호 v0.1.0 가정 (experimental)

## Parallelization

- T3·T5는 이론상 병렬 가능하나 같은 Dockerfile을 만지므로 순차 권장
- T9(문서)는 T6 이후 T7·T8과 병렬 가능
