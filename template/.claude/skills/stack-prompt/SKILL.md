---
version: 7
name: stack-prompt
description: Prompt domain skill defining PROPOSE→EVAL→REFINE cycle for prompt type Stories. Provides strategy-specific eval logic (direct/rubric/judge), pass_count metric, and stagnation signals. Lazy-loads reference/authoring-patterns.md and reference/diagnostic-patterns.md. Loop control and persistence owned by the calling agent. Workflow-only — direct-load by `prompt-engineer` agent; not exposed via skill-registry.
origin: harness
---

# stack-prompt

`prompt` 타입 Story의 평가 절차를 정의한다.
`prompt-engineer` 에이전트가 이 스킬을 로드하고 따른다.

## Known Limitation: Prediction-Based Evaluation

`direct`, `rubric`, `judge` 세 전략 모두 평가자 자신의 추론으로 출력을 예측하고 점수를 산출한다 (실제 API 호출 없음). 이는 비용·속도를 위한 의도적 설계 결정이며, 아래 제한을 수반한다:

- **Self-judgment bias**: 프롬프트를 작성한 동일한 컨텍스트가 평가도 수행하므로 Acceptance 달성이 실제 품질을 보장하지 않는다.
- **No runtime evidence**: 커밋된 프롬프트가 실제 입력에서 동작할 것을 이 스킬이 보장할 수 없다.

실제 API 호출 기반 평가가 필요하면 호출자 에이전트가 `Bash` 도구로 직접 구현해야 한다.

## Non-Goals

다음은 이 스킬의 범위 밖이다:

- **Loop control** — 반복 여부, 최대 반복 횟수, 반복 종료 결정은 호출자 에이전트가 담당
- **Persistence** — 프롬프트 파일 저장은 호출자 에이전트가 담당
- **전략 선택 외 Story 관리** — currentStory 갱신, 커밋, 상태 전환은 호출자 담당

---

## Eval Case 읽기

Eval Case 형식은 `.tack/contracts/implementation-plan.md`의 `## Prompt Task Eval Schema` 섹션에 정의돼 있다. 전략 태그(`[rubric]`, `[judge]`)가 없으면 `direct`로 해석한다.

Pass 임계값:
- `direct`: Expected와 일치 여부 (boolean)
- `rubric`: Eval Case의 `Pass: score >= N` 필드에서 N을 읽는다
- `judge`: `Pass: judge verdict == ACCEPT` — verdict는 아래 절차가 산출

---

## PROPOSE — 프롬프트 초안 작성 절차

Consult `reference/authoring-patterns.md` for skeleton and Claude Code rules.

호출자 에이전트에게 제공하는 작성 가이드:

1. Story의 Goal·Tasks·Completion Criteria(Eval Cases)를 읽는다
2. 변경 대상 파일의 현재 내용을 읽는다
3. Eval Cases의 Input 패턴을 분석해 처리해야 할 시나리오를 파악한다
4. 프롬프트 초안을 구성한다:
   - 명확한 역할 정의
   - 구체적인 지시사항
   - 필요 시 few-shot 예시
5. 초안 텍스트를 산출한다 — **저장은 호출자가 담당**

---

## EVAL — 전략별 평가 절차

각 Eval Case의 전략을 확인하고 해당 절차를 실행해 pass(1) 또는 fail(0)을 산출한다.

### `direct` 전략

1. 평가자(이 스킬을 로드한 에이전트) 자신의 추론으로 현재 프롬프트가 Input에 어떻게 응답할지 예측한다 (외부 API 호출 없음 — self-judgment임을 인지하고 보수적으로 판정)
2. Expected와 비교: 일치 → pass(1), 불일치 → fail(0)
3. 불일치 원인을 메모한다 (REFINE 단계에서 활용)

### `rubric` 전략

1. Eval Case의 Input에 현재 프롬프트를 적용했을 때의 응답을 추론한다
2. Criteria와 Rubric 앵커(1점·5점 설명)를 읽는다
3. **CoT before verdict**: 단계별 추론을 먼저 작성한다
4. 마지막 줄에 `SCORE: N` (정수, 1-5) 고정 패턴 + 이유 한 줄을 출력한다
5. `N >= Pass 임계값` → pass(1), 미달 → fail(0)

루브릭 설계 원칙:
- 기준 하나당 판정 하나 (criteria decomposition)
- Rubric 필드에 1점·5점 앵커 설명 필수
- CoT before verdict: 판정 전 추론 단계 먼저
- `SCORE: N` 고정 패턴 + 이유 한 줄

### `judge` 전략

1. Eval Case의 Input·Expected·Judge Criteria를 읽는다
2. 다음 형식으로 Claude-as-judge 평가를 실행한다:
   ```
   평가 기준: <Judge Criteria>
   기대 동작: <Expected>
   실제 응답 예측: <현재 프롬프트 적용 결과 추론>
   CoT: <단계별 판단 근거>
   VERDICT: ACCEPT | REJECT
   ```
3. `ACCEPT` → pass(1), `REJECT` → fail(0)

---

## 공통 메트릭: pass_count

전략별 이진 변환:

| 전략 | 통과(1) 조건 | 실패(0) 조건 |
|---|---|---|
| `direct` | Expected 일치 | 불일치 |
| `rubric` | score >= Pass 임계값 | score < 임계값 |
| `judge` | verdict == ACCEPT | verdict == REJECT |

`pass_count = Σ(각 Eval 통과 여부)`. 호출자 에이전트는 이 값을 매 반복마다 기록해 정체 신호를 판단한다.

---

## REFINE — 실패 패턴 분류 및 수정 가이드

Consult `reference/diagnostic-patterns.md` for failure category lookup.

호출자 에이전트에게 제공하는 수정 가이드 (저장·루프 진행은 호출자 담당):

| 실패 패턴 | 수정 전략 |
|---|---|
| 지시사항 불명확 (Expected와 다른 방향 응답) | 지시문 재작성 (더 구체적으로) |
| 예시 부족 (패턴 미인식) | few-shot 예시 추가 |
| 제약 조건 미적용 | 명시적 제약 추가 |
| 과도한 일반화 | 조건 분기 또는 예외 케이스 명시 |

수정된 프롬프트 텍스트를 산출하면 호출자가 파일에 저장하고 다음 반복을 시작한다.

---

## 정체 신호 정의

호출자 에이전트가 정체를 판단할 기준:

**정체 조건**: 연속 2회 반복에서 pass_count 증가 없음.

정체 메시지 형식 (호출자가 사용자에게 보고):
```
정체 감지: <N>회 반복 동안 pass_count가 <X>에서 개선되지 않았습니다.
실패 패턴: <요약>
현재 최선 초안이 파일에 저장되어 있습니다.
수동 검토 후 /flow-impl을 재실행하거나, 스펙의 Eval Cases를 수정하세요.
```

---

## 종료 신호 (호출자가 검사)

| 신호 | 조건 |
|---|---|
| **SUCCESS** | pass_count ≥ Acceptance N (Story Completion Criteria에서 읽음) |
| **MAX_ITER** | 반복 횟수 == 최대 한도 (호출자 정책, 권장값 5회) |
| **STAGNATION** | 연속 2회 pass_count 증가 없음 |

신호에 따른 동작(저장, 보고, 루프 종료)은 호출자 에이전트가 결정한다.

---

## 성공 보고 형식 (호출자가 사용)

```
PROPOSE→EVAL→REFINE 완료
  반복 횟수: N회
  최종 pass_count: X/M
  Acceptance: 통과
  저장 파일: <path>
```
