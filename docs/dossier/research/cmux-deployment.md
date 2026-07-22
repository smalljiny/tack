---
version: 1
---

# 자료: cmux 스킬 배포 모델 (참고)

**조사 대상**: 사용자 제안 — cmux(터미널 제어 스킬)의 배포 모델(https://cmux.com/ko/docs/skills)을 tack 배포 참고자료로 검토.

**출처**: adapter-exa `/contents`(cmux 문서) + `/answer`(Vercel Skills CLI), 2026-07-21.

## cmux가 쓰는 두 배포 경로

1. **`skills.sh` (curl\|bash 인스톨러)**: `curl -fsSL .../skills.sh | bash`. 옵션 `--ref <branch|tag|commit>`(버전 핀), `--dest`, `--skill <name>`(선택 설치), `--list`, `--dry-run`, 체크아웃-로컬 모드.
2. **Vercel Skills CLI**: `npx skills add manaflow-ai/cmux -g -y`.

**설치 대상**: 기본 `~/.codex/skills`(또는 `$CODEX_HOME/skills`, `--dest`) — **글로벌 스킬 디렉토리**. 각 스킬 = `SKILL.md` + references + `agents/openai.yaml`(Codex 메타).

## Vercel Skills CLI (`vercel-labs/skills`) — novel 발견

- **다중 에이전트 범용 패키지 매니저**: SKILL.md 기반. **40+ 에이전트 지원(Claude Code·Codex·Cursor 포함)** — 한 소스가 여러 에이전트 관례로 동시 설치.
- **스코프**: 프로젝트 스코프 기본(VC 커밋), `-g`로 글로벌.
- **메커니즘**: symlink 권장(단일 원천 → 갱신 시 연결된 모든 에이전트 자동 반영), 미지원 시 물리 복사.
- **업데이트**: `npx skills check` / `npx skills update`(최신 GitHub tree SHA 재설치).
- 출처: vercel-labs-skills.mintlify.app, github.com/vercel-labs/skills

→ **"한 소스 → Claude+Codex 동시 배포"가 이미 해결된 표준 패턴**임을 입증(플러그인이 못 준 것). tack의 도구-중립 base 방향을 강하게 검증.

## tack에의 함의 — 참고하되 base로는 Copier 유지

**결정적 구분: cmux 스킬은 standalone 능력, tack 스킬은 harness-coupled.**

- cmux 스킬(터미널 제어)은 **프로젝트 무관 standalone 능력** → 글로벌 설치(`~/.codex/skills`)가 타당. 계약·프로젝트 상태와 결합 없음.
- tack의 스킬은 `.harness/contracts/`·rules·dev-context와 **버전 결합**돼 있다(서로 참조). 스킬을 글로벌 채널로 분리하면 스킬 버전과 계약 버전이 어긋나 **우리가 계속 피해온 스큐 재발**.

**따라서:**
- **base = Copier 유지** — tack은 스킬만이 아니라 hooks·contracts·scripts·context 파일(CLAUDE.md/AGENTS.md)·config까지 배포하고, 이들이 한 버전으로 결합돼야 한다. Vercel Skills는 **SKILL.md 스코프에 한정**돼 hooks/contracts/scripts를 못 싣는다 → 전체 base 불가.
- **Vercel Skills 역할**: (a) 도구-중립·다중에이전트 배포가 solved임을 검증(방향 확신), (b) tack 스킬을 `skills` 생태계·cmux 스타일 사용자에게 **선택적 interop**로 노출할지는 별개 결정(부차). base 대체 아님.
- **cmux `skills.sh`**: 앞서 후보였던 "bespoke curl 인스톨러"의 실전 검증 사례. Copier 대비 update-화해가 약해 base로는 열위.

## 방향 함의

- OQ1 base = **Copier 유지·강화**(다중에이전트 배포가 solved임이 재확인되나, tack의 harness-coupled 특성이 per-project 단일버전을 요구).
- **신규 부차 결정(spec)**: tack 스킬을 Vercel Skills 생태계에 선택적 발행할지(cmux interop·표준 정렬 vs 스큐 관리 부담).

## 인용
- cmux skills — cmux.com/ko/docs/skills (skills.sh, npx skills add, ~/.codex/skills)
- Vercel Skills 소개 — vercel-labs-skills.mintlify.app/introduction
- Vercel Skills 설치 — vercel-labs-skills.mintlify.app/guides/installation-methods
- Vercel Agent Skills — vercel.com/docs/agent-resources/skills.md
