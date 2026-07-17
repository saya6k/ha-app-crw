# ha-app-crw TODO

상세: [tasks/plan.md](plan.md) · 스펙: [SPEC.md](../SPEC.md)

## Phase 1: Scaffold
- [x] T1 로컬 repo scaffold (wardrowbe 템플릿, slug=crw, 워크플로 2-track)
- [x] T2 GitHub repo 셋업 (create·CATALOG_PAT·workflow 권한·push)
- [x] Checkpoint A: lint green + push 완료 → 사용자 보고

## Phase 2: 슬라이스 1 — web_scrape E2E
- [x] T3 Dockerfile + crw-server 서비스 (musl 검증·UDS §11-2 확정 — static binary, UDS 미지원→127.0.0.1)
- [x] T4 bridge 골격 + web_scrape + discovery announce + pytest
- [x] Checkpoint B: scrape가 /mcp 경유 E2E 동작 (aarch64 로컬 검증, amd64는 CI)

## Phase 3: 슬라이스 2 — web_search E2E
- [x] T5 SearXNG 서비스 — fastcrw sidecar 패턴으로 변경(사용자 지시): crw pin 버전, loopback 8080, 검색은 crw /v1/search 경유
- [x] T6 web_search (jxlarrea scheme) + 옵션 wiring — bridge → crw /v1/search 경유
- [x] Checkpoint C: smoke ①②③ 전부 통과 (aarch64)

## Phase 4: CI·문서·릴리스
- [ ] T7 CI green (GitHub Actions 전 job)
- [ ] T8 스모크 스크립트 CI 편입 (amd64)
- [ ] T9 문서·아이콘·번역 (DOCS/.README.j2/en·ko/icon·logo/AGPL 고지)
- [ ] T10 초기 릴리스 v0.1.0 → GHCR 멀티아치 확인
- [ ] Checkpoint D: Success Criteria 1·2·4 충족, 3(HA E2E)은 사용자 인계
