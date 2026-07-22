# Authoring Patterns

> stack-prompt PROPOSE 단계가 lazy-load해 사용하는 작성 가이드.
> Template M 8개 필드 + Claude/Claude Code 라우팅 규칙 11항목 + 2025-2026 리서치 인사이트 5항목을 큐레이션해 단일 진입점으로 제공한다.

이 문서는 prompt-master(`references/prompt-master/`)의 검증된 템플릿·라우팅 규칙을 발췌하고, 별도 리서치 보고서의 인사이트로 보강한 결과다. 출처와 라이선스는 문서 말미 footer 참조.

---

## 1. Template M — Opus 4.7 Task Brief

복잡·다단계·에이전틱 Task 작성에 사용한다. Opus 4.7은 프롬프트를 문자 그대로 읽으므로(literal interpretation), 첫 턴에 모든 정보를 front-load해 두 번째 턴이 필요 없게 만든다.

8개 필수 필드:

| # | 필드 | 역할 |
|---|------|------|
| 1 | **Objective** | 무엇을 만들/고치/산출할지 한 문장. 접근 방식에 영향이 있으면 WHY를 함께 적는다. |
| 2 | **Context** | 현재 상태 — 관련 파일, 동작, 이미 깔린 스택, 시도했지만 실패한 것. |
| 3 | **Target State** | 완료 시점의 모습 — 변경 파일, 산출 동작, 통과해야 할 테스트. 가능하면 binary로. |
| 4 | **Scope** | 작업 가능한 파일/디렉토리(`Work only in:`)와 절대 만지지 말 것(`Do NOT touch:`)을 명시. |
| 5 | **Constraints** | 스택 버전, 네이밍 규칙, 의존성 추가 금지 등. `Only make changes directly requested.`를 포함해 over-engineering을 차단한다. |
| 6 | **Acceptance Criteria** | binary 체크박스 항목들. "통과/실패"로 판정 가능한 형태. |
| 7 | **Stop Conditions** | `Stop and ask before:` 다음에 파일 삭제·의존성 추가·DB 스키마 변경·Scope 외 수정 등 위험 동작을 나열. |
| 8 | **Progress** | 각 스텝 완료 후 `✅ [완료한 것] — [영향 받은 파일]` 형식으로 리포트. |

선택 블록:
- **Thinking depth** — 필요할 때만 추가. 기본은 무지정(adaptive thinking).
- **Session Strategy** (Claude Code 한정) — `New session` / `Continue` / `Subagent` / `Compact first` 중 하나.

Template M의 원형 텍스트와 Session Strategy 블록은 `references/prompt-master/references/templates.md`의 "Template M — Opus 4.7 Task Brief" 섹션 참조.

---

## 2. Claude / Claude Code Routing Rules — 11항목

Opus 4.7 / Claude Code에서 우선 적용할 라우팅 규칙 11개. prompt-master `SKILL.md`의 `Claude (claude.ai, Claude API, Claude 4.x)`(lines 71-78) + `Claude Code`(lines 160-172) 섹션에서 큐레이션.

1. **literal interpretation 전제** — Claude 4.x는 지시를 literal interpretation 한다. Opus 4.7은 더 엄격하다. 명시되지 않은 것은 추론하지 않으므로 hedge 없이 명시적으로 적는다.

2. **XML tags로 구조화** — 멀티섹션 프롬프트는 XML tags로 구획한다: `<context>`, `<task>`, `<constraints>`, `<output_format>`. 자연어 헤더보다 안정적이다.

3. **Over-engineering 차단** — Claude Opus 4.x는 기본적으로 과설계 경향이 있다. `Only make changes directly requested. Do not add features or refactor beyond what was asked.`를 명시한다.

4. **WHY를 함께 제공** — `Provide context and reasoning WHY, not just WHAT — Claude generalizes better from explanations`. 의도를 알면 일반화 품질이 올라간다.

5. **출력 포맷·길이 명시** — Always specify output format and length explicitly. Opus 4.7은 verbosity를 task 복잡도에 적응시키므로, 다운스트림이 길이/스타일에 의존하면 반드시 명시한다.

6. **첫 턴에 front-load** — Front-load everything in one turn — intent, constraints, acceptance criteria, relevant files. 추가 turn마다 reasoning overhead와 토큰 비용이 누적된다.

7. **"think step by step" 금지** — Do NOT add "think step by step" or fixed thinking budget instructions. Opus 4.7은 adaptive thinking으로 깊이를 자동 조절한다. 깊이를 바꾸려면 `Think carefully before responding`(↑) 또는 `Prioritize responding quickly`(↓)로 표현한다.

8. **Stop conditions는 MANDATORY** — Claude Code에서 Stop conditions are MANDATORY — runaway loops are the biggest credit killer. Template M의 Stop Conditions 블록을 항상 채운다.

9. **file/directory scope 앵커** — Always scope to specific files and directories — never give a global instruction without a path anchor. 글로벌 지시는 file/directory scope를 동반해야 한다.

10. **human review 트리거 명시** — `Stop and ask before deleting any file, adding any dependency, or affecting the database schema`. 파괴적 동작 전 human review를 강제한다.

11. **Session hygiene** — `Session hygiene matters: new task = new session.` `/rewind`로 중간 수정하고, `/compact`은 50% 컨텍스트에서 (90%가 아니라) 실행한다. 새 Task는 새 세션으로 시작한다.

---

## 3. Research Insights (2025-2026)

리서치 보고서 §1.1-1.4 + Key Takeaways에서 흡수한 5개 인사이트. 위 라우팅 규칙을 보강·재맥락화한다.

- **Hedge 금지 — "try to" 류 약화어 제거**. Opus 4.7에서는 hedge / try to / "if possible" / "you might want to" 같은 약화어가 4.6에서 polite intensifier였던 것과 달리 지시를 약화시킨다. 단정형으로 전환한다 (research §1.2).

- **anti-laziness 스캐폴딩 비활성화**. 이전 모델용 anti-laziness 강화 어구(`CRITICAL You MUST` / `CRITICAL: You MUST...`)는 Opus 4.7에서 over-trigger를 유발한다. 평범한 어조(`Use this tool when...`)로 다이얼 다운한다 (research §1.2).

- **xhigh가 Claude Code 기본값**. Opus 4.7의 Claude Code 기본 effort는 xhigh다. 프롬프트에서 effort 레벨을 따로 지정하지 말 것 — 이미 set 돼 있다. `max`는 diminishing returns·overthinking 위험이 크다 (research §1.1).

- **progressive disclosure / 500줄 제한**. 스킬·에이전트 프롬프트는 progressive disclosure를 따른다: SKILL.md는 ≤500줄, references는 한 단계 깊이까지, 100줄 초과 reference 파일은 목차를 둔다. lazy-load로 attention budget을 보존한다 (research §3.5, Key Takeaway 9).

- **degrees of freedom 매칭**. Skill 작성자는 task fragility에 degrees of freedom을 맞춘다 — 파괴적/취약 작업(DB 마이그레이션 등)은 정확한 스크립트(low freedom), 열린 작업(코드 리뷰 등)은 일반 방향(high freedom). 너무 높은 altitude(`be helpful`)도 너무 낮은 altitude(brittle if-else)도 모두 실패한다 (research §3.3, Key Takeaway 10).
