---
version: 5
---

# tack 방향 설정 dossier

이 디렉토리는 차세대 개발 하네스 **tack**의 **방향 설정 dossier**다. tack의 실제 구현은 **별도 새 저장소**에서 이뤄진다.

## 이 저장소(현 harness)에서의 작업 범위

현재 프로젝트(harness)를 기준으로:
1. **개선점 검토** — 현 harness에서 모호·불일치·구조적 한계를 짚는다.
2. **자료 수집** — 방향 결정에 필요한 검증·조사 결과를 모은다.
3. **방향 결정** — tack이 취할 용어·구조·저장소·배포 방향을 확정한다.

**여기서 하지 않는 것**: tack 구현 코드, 정식 flow spec/plan. 이들은 확정 방향을 입력으로 받아 **새 저장소**에서 진행한다. 이 dossier는 그 핸드오프 자료다.

## 종합 (핸드오프 진입점)

**`handoff.md`** — 모든 확정 결정 + 남은 것 + 핸드오프 체크리스트를 한 문서로 종합. 새 저장소 spec 입력의 시작점. (아래 개별 문서는 세부 근거.)

## 결정 인덱스

| 문서 | 내용 | 상태 |
|------|------|------|
| `glossary.md` | 용어 확정 — 제품 정체성(tack/tack repo/target project), 작업 계층(epic>story>task>subtask) + Type 부착 계층(§1.1: Type=task / 컨테이너=story / 국면=subtask), gate(5), command/skill, 상태 | 🟢 전 항목 확정 |
| `session-model.md` | 세션 운영 모델 — 메인(hub)/워크트리 분리, 경계=`spec:confirmed` | 🟢 확정 |
| `context-store.md` | 컨텍스트 저장소 — 장치 간 공유(remote-context-store 흡수), GitHub/로컬/Mongo 역할 배분 | 🟢 확정 |
| (glossary OQ1) | 배포 — base는 도구-중립(플러그인-only 배제), 패키징 = per-project Copier | 🟢 확정 |
| `delta-model-proposal.md` | brownfield delta(B1) + EARS(B2) 결합 시안 — delta requirement를 EARS+scenario로, MVP=프레이밍, 안정ID 병합은 연기 | 🟡 제안(spec에서 채택 결정) |

## 수집 자료 (research/)

| 문서 | 내용 |
|------|------|
| `research/plugin-provisioning.md` | Claude 플러그인의 비-Claude 파일 provision — 가능하나 스큐 재발로 base 부적합 |
| `research/base-packaging.md` | 도구-중립 base 패키징 — **Copier** 표준 적합 (update-화해·git-tag 단일버전·uv 정렬) |
| `research/cmux-deployment.md` | cmux/Vercel Skills 배포 모델 참고 — 다중에이전트 배포 solved 검증, 단 skill 스코프 한정 |
| `research/global-vs-perproject.md` | global vs per-project 검토 — **per-project(Copier) 확정** (계약 타이밍 통제) |
| `research/upgrade-method.md` | 하네스 업그레이드 — `copier update`(migrations·롤백·커밋된 버전기록), tracked 전환 긴장 |
| `research/github-issue-mechanism.md` | GitHub 이슈 — ⚠ 부분 폐기(조사 기록). **최종**: epic/story = 이슈 라벨(`type:epic`·`type:story`) + sub-issues, native Issue Types·Projects 미채택, 상태는 Mongo |
| `research/command-shadowing.md` | command file 잔존 — skills-only 확정, shadowing은 설계로 회피(버그 영역 회피) |
| `research/harness-directions.md` | 하네스 베스트 프랙티스 조사 — 추가 개선 방향(brownfield delta·EARS·design분리·risk routing) + 스터디 대상(SpecRoute·Spec Kit·OpenSpec·Kiro) |
| `research/risk-tier-b3-b4.md` | B3(design 분리)+B4(risk routing/consensus) 평가 — 하나의 per-story 위험도 tier로 통합, delta가 신호. 경량 채택·무거운 기계장치 연기 |
| `research/skeleton-first-b6.md` | B6 skeleton-first 구현 + 2단 게이트 리뷰 — 골격(스텁 체인)→함수별 구현, flow/unit 리뷰 분리로 리뷰 피로↓. 실사례(DisC·architecture-scaffold·full-review) 검증 |

## 확정 방향 요약 (OQ1~OQ4 🟢 전부 확정)

`glossary.md`의 Open Questions는 모두 확정됐다. 세부 근거는 `research/`.
- OQ1 배포·업그레이드 🟢 확정 — **per-project Copier**(도구-중립 base, 플러그인-only 배제). 근거 `base-packaging.md`·`global-vs-perproject.md`·`upgrade-method.md`·`plugin-provisioning.md`
- OQ2 GitHub 이슈 메커니즘 🟢 확정 — epic/story 타입 = **이슈 라벨**(`type:epic`·`type:story`), 계층 = **sub-issues**. native 커스텀 Issue Types 미채택(개인·조직 repo 균일)
- OQ3 워크플로우 저장소 🟢 확정 — **MongoDB shared registry + CLI 대시보드**(GitHub Projects 폐기). 남은 세부는 Mongo 스냅샷·`list_topics` 필드 스키마
- OQ4 command file 🟢 확정 — **skills-only, command file 0**, shadowing은 설계로 회피. 근거 `command-shadowing.md`

## 핸드오프

확정 방향 → 새 tack 저장소의 초기 spec 입력. 현 harness는 개선 교훈의 출처(reference)이지 구현 대상이 아니다.
