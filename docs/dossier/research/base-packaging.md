---
version: 1
---

# 자료: 도구-중립 base 패키징 방식

**조사 대상 (OQ1 열린 결정)**: tack의 도구-중립 base(`.claude`+`CLAUDE.md`·`.codex`+`AGENTS.md`·`.harness`를 target project에 배치)를 어떤 방식으로 패키징·배포하는가 — 현 복사 스크립트(`deploy-harness.sh`) 유지 vs 버전드 인스톨러.

**요구 조건**: ①one-command INIT ②**버전 추적 UPDATE + 로컬 커스터마이징 화해**(핵심) ③단일 버전 소스(계약 정합) ④버전 substrate ⑤런타임 의존 최소 ⑥cross-platform. init-once 파일(`CLAUDE.md`·`AGENTS.md`·`commit-scopes.md`)과 always-resync 파일(skills·agents·rules·contracts) 구분 필요.

**출처**: general-purpose 에이전트 웹 조사(2026-07-21, 공식 문서 인용) + **adapter-exa `/answer` 교차검증 완료**(2026-07-21).

## 결론 — Copier가 표준 적합

| 후보 | INIT | UPDATE+화해 | 버전 | 런타임 | uv 정렬 | 판정 |
|------|------|-------------|------|--------|---------|------|
| **Copier** | `uvx copier copy` | **네이티브** (diff+conflict marker) | git tag (PEP 440, `.copier-answers.yml` `_commit`) | Python via uvx | ✅ | **채택 후보** |
| cruft(+cookiecutter) | ✅ | 약함(patch, `_skip_if_exists` 등가물 없음) | git hash | Python | 부분 | 차선 |
| degit / GitHub template | ✅ | ❌ 스캐폴딩 전용 | 없음 | Node/git | ✗ | 탈락(요구2 실패) |
| git submodule/subtree | 부분 | 수동(raw merge) | git ref | git | 중립 | 탈락(**서브디렉토리**에 materialize, 루트 배치 불가) |
| npm+npx / Homebrew / curl\|sh | ✅ | 직접 구현해야 | semver/tag | Node/brew/sh | ✗/중립 | 화해 엔진 자작 필요 |
| PyPI+uvx 자작 CLI | ✅ | 직접 구현 | semver/tag | uvx | ✅ | Copier 재발명 |

## Copier가 맞는 이유

- **UPDATE 네이티브**: `copier update`가 (원 버전에서 재생성 → 로컬 diff 계산 → 최신 템플릿으로 갱신 → 로컬 diff 재적용, 충돌 시 `git merge` 스타일 마커). 유일하게 화해를 **기본 제공**.
- **버전 = git tag**: `.copier-answers.yml`의 `_commit`이 정확한 ref 기록. 최신 tag를 PEP 440으로 비교해 checkout.
- **init-once ↔ always-resync 매핑**: `_skip_if_exists`가 정확히 이 구분. `CLAUDE.md`·`AGENTS.md`·`commit-scopes.md`를 여기 넣으면 update 시 미갱신, 나머지(skills·agents·rules·contracts)는 매 update 재동기화.
- **단일 버전 소스**: 번들 전체가 한 템플릿 repo·한 git tag → 양 도구 파일이 버전 정합(계약 스큐 없음). **플러그인/하이브리드가 못 준 보장을 구조적으로 제공.**
- **uv 정렬**: `uvx copier ...`. Track 2(uv 전환)·graphify와 툴체인 일치.
- **현 스크립트의 엄격한 상위호환**: `deploy-harness.sh`의 skip-if-exists 로직을 저유지보수로 대체.

**주의(문서 확인 + adapter-exa 교차검증)**: update 시 target이 **git repo이고 working tree clean**이어야 함(공식 문서 best practice로 확인). 템플릿은 git tag 보유 repo여야 함. **`uvx copier update` 동작 확인** — Copier는 uvx로 실행 가능하고 update 서브커맨드도 동일. `pawamoy/copier-uv`(uv 기반 Python용 Copier 템플릿) 존재가 Copier+uv 패턴을 방증.

## 방향 함의

- **OQ1 패키징 = Copier 템플릿(uvx 실행) 유력.** "복사 스크립트 vs 버전드 인스톨러"의 답 → **버전드(Copier)**.
- **§0 유보 층 이름 도출**: Copier 채택 시 **tack repo = Copier 템플릿(원천)**, **target project = 생성된 인스턴스**. §0에서 배포 모델 대기로 미뤘던 "원천/템플릿/인스턴스" 이름이 **template → generated project**로 구체화 가능.
- **미해결(설계 시 검토)**: clean-git-repo 제약과 worktree 워크플로우의 상호작용 — harness 업데이트(`copier update`)는 미커밋 변경 없는 clean 경계에서 수행하는 유지보수 op이므로 impl 중 실행과 충돌 안 함. 단 spec 단계에서 "언제 tack을 update하는가" 절차 명시 필요.

## 인용
- Copier updating — copier.readthedocs.io/en/stable/updating/
- Copier configuring(`skip_if_exists`) — copier.readthedocs.io/en/stable/configuring/
- Answer file mgmt(`_commit`, PEP 440 tag) — deepwiki.com/copier-org/copier/4.2
- uv tools — docs.astral.sh/uv/guides/tools/
- cruft vs copier — blenddata.nl/en/blogs/cruft-vs-copier-automating-template-updates-at-scale
