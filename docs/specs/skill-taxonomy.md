5-tier 스킬 분류 체계

> **문서 성격**: tack이 배포하는 하네스의 **스킬 분류 체계**를 확정하는 권위 참조 문서다. 5-tier prefix 규약, 슬래시 커맨드 노출의 단일 진실 원천(`user-invocable: true`), command-file-0(skills-only) 모델을 정의한다. canonical 규칙은 `template/.claude/rules/common/component-boundaries.md`가 강제하며, 이 문서는 그 아키텍처를 서술한다.
>
> **확정일**: 2026-07-23 · **원천 결정**: E3-S1 (dossier A3/OQ4 — skills-only)

## 1. 개요

tack 하네스의 모든 프롬프트 로직은 **스킬 하나의 시스템**에 앉는다. 워크플로우 진입점·재사용 단위 로직·외부 도구 어댑터·기술 패턴 가이드·하네스 인프라를 별도 command 시스템 없이 동일한 스킬 시스템 안에서 **prefix로 tier를 구분**하고, 슬래시 커맨드 노출은 **frontmatter 플래그로 투영**한다.

두 축이 이 체계를 정의한다:

- **분류 축 (tier)**: 스킬 이름의 prefix(`flow-`/`wf-`/`adapter-`/`stack-`/`meta-`)가 역할·호출 방식·배치 기준을 결정한다.
- **노출 축 (user-invocable)**: SKILL.md frontmatter의 `user-invocable: true`가 슬래시 커맨드 노출을 결정한다 — **tier와 무관**하다.

두 축은 직교한다. tier는 "이 스킬이 무엇인가"를, `user-invocable`은 "사용자가 직접 부를 수 있는가"를 각각 독립적으로 답한다.

**command file 0 (skills-only)**: 별도 command 파일은 노출 채널이 아니다. `template/.claude/`에 `commands/` 디렉토리는 존재하지 않으며, 사용자 직접 호출 진입점은 전부 `user-invocable: true` 스킬로 노출된다.

## 2. 5-tier 체계

| Tier | Prefix | 역할 | 호출 방식 | user-invocable | 판별 기준 |
|------|--------|------|-----------|:---:|----------|
| Orchestration | `flow-` | 워크플로우 단계 전체 소유 — 상태 머신·시퀀싱·dev-context 전환 | 사용자 직접 (`/flow-impl`) | **true** | 사용자가 직접 시작하는 진입점인가? |
| Unit | `wf-` | 재사용 단위 작업 — 오케스트레이터·에이전트가 Load | 스킬 Load 지시 | 미설정 | 항상 실행 가능하며 내부 전제 조건 없는가? |
| Adapter | `adapter-` | 외부 도구 래퍼 — 가용성 게이트·폴백 보유 | 오케스트레이터·다른 스킬이 Load | 미설정 | 외부 도구 없으면 자체 skip/fallback하는가? |
| Stack | `stack-` | 기술 패턴 가이드 — capabilities 기반 발견 | skill-registry 탐색 | 미설정 | 기술 지식 제공인가? |
| Meta | `meta-` | 하네스 인프라 — 스킬 생성·상태·관리 | 직접 로드 **또는 사용자 직접** | **필요 시 true** | 하네스 자체를 관리하는가? |

### 2.1 tier 결정 흐름

새 스킬을 작성할 때 아래 의사결정 트리를 따른다. 첫 매칭에서 tier가 결정된다.

```
하네스 자체(스킬 생성·상태 관리·인프라)를 관리하는가?
  → 예  : meta-*  (직접 로드 또는 사용자 직접)
  → 아니오
      사용자가 직접 타이핑해서 시작하는가?
        → 예  : flow-*  (user-invocable: true 명시)
        → 아니오
            외부 도구 없으면 skip/fallback을 자체 선택하는가?
              → 예  : adapter-*
              → 아니오
                  기술 스택 패턴 가이드인가?
                    → 예  : stack-*
                    → 아니오 : wf-* (단위 작업)
```

### 2.2 prefix 예외

두 스킬은 5-tier prefix를 갖지 않으며, 의도된 예외다:

| 스킬 | 성격 |
|------|------|
| `learned/` | `/meta-harness-learn`이 자동 저장하는 패턴 저장소 — 개별 스킬이 아닌 컨테이너 |
| `skill-registry/` | capabilities 발견 허브 — tier-less 인프라 |

## 3. user-invocable SSOT

슬래시 커맨드 노출의 유일한 판정 기준은 SKILL.md frontmatter의 `user-invocable: true`다.

- **노출**: `user-invocable: true` → `/<skill-name>` 슬래시 커맨드로 노출.
- **비노출**: 미설정 또는 `false` → 오케스트레이터·에이전트·skill-registry 경유로만 호출.
- **tier 무관**: `flow-` 스킬은 관례상 전부 `true`이고, `meta-` 스킬도 사용자 직접 호출 진입점이면 `true`다. tier가 노출 여부를 결정하지 않는다.

플랫폼 버전별 기본값 차이를 회피하기 위해, 노출 대상 스킬은 frontmatter에 `user-invocable: true`를 **명시**한다. 스킬 노출은 SKILL.md frontmatter가 결정하며, 스킬을 command 파일로 감싸 노출하지 않는다.

## 4. 하네스 인프라 meta 스킬

하네스 관리 진입점은 `meta-*` tier의 `user-invocable: true` 스킬로 노출된다. 결정 트리 first-match("하네스 자체를 관리하는가? → meta-")를 만족하는 사용자 직접 호출 스킬이다.

| 스킬 | 슬래시 노출 | 역할 |
|------|------------|------|
| `meta-add-language-rules` | `/meta-add-language-rules` | 언어별 규칙 파일(coding-style·security·testing) 스캐폴딩 |
| `meta-harness-audit` | `/meta-harness-audit` | 하네스 건강 감사 — 우선순위 스코어카드 |
| `meta-harness-learn` | `/meta-harness-learn` | 세션 반복 패턴 추출 → 재사용 스킬 저장 |
| `meta-codex-setup` | `/meta-codex-setup` | codex CLI 상태 확인 + `config.codex.*` 캐시 갱신 |

`meta-codex-setup`은 codex CLI를 래핑하는 adapter 성격도 있으나, 결정 트리 first-match(하네스 상태 관리)가 우선하고 사용자 직접 호출 진입점이므로 `meta-`로 배정된다.

**슬래시 이름은 flat**하다. 스킬 이름이 flat(`meta-harness-audit`)이므로 노출 이름도 flat(`/meta-harness-audit`)이며, 콜론 네임스페이스 형태(`/harness:audit`)를 사용하지 않는다.

## 5. Delegation Pattern

스킬을 다른 스킬·에이전트·문서에서 호출할 때는 다음 한 줄 형태를 사용한다.

```
Load `.claude/skills/<name>/SKILL.md` and follow its process.
```

규칙 파일이나 contract 문서를 명시 로드할 때도 같은 형태를 사용한다.

```
Load <rule-path> and follow its process.
```

`flow-*` 스킬은 단위 로직을 직접 정의하지 않고, 재사용 가능한 분리 단위 로직은 `wf-*`·`adapter-*` 스킬로 추출해 위임한다. 이미 다른 스킬에 존재하는 로직(중복)이나 재사용 가능한 분리 단위 로직을 `flow-*`가 직접 정의하면 위반이다.

## 6. Codex 대칭

Codex 측(`template/.codex/`·`template/AGENTS.md.jinja`)은 `skills/`만 포함하며 command 디렉토리·command/skill 이분법이 없다. tack의 skills-only 모델은 Claude·Codex 양쪽에서 대칭이다.

## 7. 제약사항

- **command 파일은 노출 채널이 아니다** — `template/.claude/`에 `commands/` 디렉토리는 없다. 새 사용자 진입점은 command 파일이 아닌 `user-invocable: true` 스킬로 만든다.
- **user-invocable은 명시** — 플랫폼 기본값에 의존하지 않고 노출 대상 스킬 frontmatter에 `true`를 직접 적는다.
- **tier는 배치를, user-invocable은 노출을** — 두 결정을 섞지 않는다. `meta-` 스킬이라고 자동 노출되지 않고, `user-invocable: true`라고 tier가 바뀌지 않는다.
- **canonical 규칙 우선** — 이 문서는 아키텍처 서술이며, 강제 규칙은 `template/.claude/rules/common/component-boundaries.md`가 소유한다. 충돌 시 규칙이 우선한다.
- **대상 트리는 `template/` 소스** — 배포된 destination의 스킬 구조는 이 source 트리의 렌더 결과다. 루트 `.claude/`는 pre-M1 부트스트랩 레퍼런스로 이 체계의 관리 대상이 아니다.
- **tier별 컴포넌트 개수를 문서에 기록하지 않는다** — 개수는 스킬을 추가·제거할 때마다 바뀌지만 이를 갱신하는 소유자가 없다. Copier 렌더도 `flow-init`도 tier 개수를 다시 쓰지 않으므로, 기록된 숫자는 다음 스킬 추가 시점에 곧바로 stale된다. tier 구성은 prefix 규약과 개별 열거로 서술하고, 실제 개수가 필요하면 `template/.claude/skills/` 트리를 직접 센다. 개수는 트리 하나에만 유효하다는 제약도 있다 — 같은 tier라도 루트 부트스트랩 `.claude/`와 `template/.claude/`의 스킬 수가 다르므로 두 트리를 동시에 만족하는 단일 숫자가 존재하지 않는다.
