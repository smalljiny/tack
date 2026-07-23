---
version: 2
---

현행 Opus는 리터럴 해석이 강해, hedge·강조형 스캐폴딩·CoT 명시 지시 같은 표현이 의도와 달리 약한 지시·과활성화·adaptive thinking 충돌로 처리된다. 이 가이드는 그 리터럴 해석 강화 경향에 대응하는 7 규칙을 근거·예시·적용 대상과 함께 정의한다.

이 파일은 두 채널로 적용된다 — (a) `.claude/rules/common/` 자동 로드를 통해 모든 Claude 세션의 베이스라인 컨텍스트로 부착되고, (b) 메타 컴포넌트(`meta-skill-creator`, `planner`, `prompt-engineer`)가 컴포넌트 작성 직전 표준 문구 `` `Load .claude/rules/common/prompt-authoring.md and follow its process.` ``로 명시 로드한다.

> **Provenance**: 이 7 규칙은 Opus 4.6→4.7 전환기의 리터럴 해석 강화 연구에서 도출됐으며, 현행 Opus에도 유효하다. 원 연구 문서는 본 저장소에 별도로 존재하지 않으므로, 아래 §1 표의 `연구 §1 항목 #` 열이 각 규칙의 도출 출처 표기를 겸한다.

## 1. 규칙 ↔ 행동 변경 매핑

| 작성 규칙 # | 연구 §1 항목 # | 한 줄 요약 |
|------------|---------------|-----------|
| 1. hedge 제거 | 1 | `try to` / `if possible` 등 hedge가 약한 지시로 처리되어 누락 위험이 커진다 |
| 2. 스코프 명시 | 2 | 스코프 미명시 시 첫 매칭 항목에만 적용되어 배치 처리가 누락된다 |
| 3. anti-laziness 스캐폴딩 제거 | 3 | `CRITICAL: You MUST` 같은 강조형이 과활성화 트리거로 작동한다 |
| 4. 필터 지시 제거 또는 정량화 | 4 | `be conservative` 같은 필터어가 충실히 적용되어 recall이 떨어진다 |
| 5. CoT 명시 지시 제거 | 5 | `think step by step` 명시 지시가 현행 Opus의 adaptive thinking과 충돌한다 |
| 6. 첫 turn 정보 front-load | 6 | 핵심 정보를 도입부에 배치하지 않으면 후속 turn에서 품질이 저하된다 |
| 7. 도구 호출 트리거 명시 | 7 | 도구 호출 기본 빈도가 낮아져 호출 시점·조건을 직접 진술해야 한다 |

## 2. 7가지 작성 규칙

### 규칙 1. hedge 제거 — 명령형으로 진술

- **규칙**: `try to`, `if possible`, `attempt to`, `consider`, "가능하면", "되도록", "최대한" 같은 hedge를 삭제하고 평이한 명령형으로 진술한다.
- **근거**: 연구 §1 항목 1 — 현행 Opus는 hedge를 약한 지시로 처리해 지시가 누락될 확률이 높아진다. 과거 정중함의 신호였던 hedge가 현행 Opus에서는 우선순위 하향 신호가 된다.
- **Before (안티 패턴)**:

  ```
  If possible, try to validate the input before saving. Consider adding a type
  check when feasible.
  ```

- **After (권장)**:

  ```
  Validate the input before saving. Add a type check.
  ```

- **적용 대상**: 에이전트, 스킬, 커맨드, 규칙 모두.

### 규칙 2. 스코프 명시 — 적용 범위를 직접 진술

- **규칙**: "X에 Y를 적용한다"는 지시는 스코프(전부 / 특정 항목 / 첫 번째 / 마지막 등)를 명시한다. 배치 처리·다중 파일 작업은 "모든", "각", "전체" 같은 양화사를 명시한다.
- **근거**: 연구 §1 항목 2 — 스코프 미명시 시 현행 Opus는 첫 매칭 항목에만 적용하고 종료한다. 맥락에서 배치 의도를 추론하지 않고 진술된 스코프만 따른다.
- **Before (안티 패턴)**:

  ```
  Update the version field to 2.
  ```

- **After (권장)**:

  ```
  Update the version field to 2 in every component file under .claude/agents/.
  ```

- **적용 대상**: 에이전트, 스킬, 커맨드, 규칙 모두 (특히 일괄 처리 지시가 있는 커맨드).

### 규칙 3. anti-laziness 스캐폴딩 제거 — 평이한 명령형

- **규칙**: `CRITICAL:`, `IMPORTANT:`, `You MUST`, `MUST` 강조형, "절대로", "반드시 X해야만 한다" 같은 강조 스캐폴딩을 삭제하고 평이한 명령형으로 진술한다. 단순 "한다" 종결형은 OK.
- **근거**: 연구 §1 항목 3 — 현행 Opus는 강조형 스캐폴딩을 과활성화 트리거로 처리해, 모든 단계에서 동일 검증을 반복하거나 무관한 항목까지 차단하는 over-cautious 동작이 나타난다.
- **Before (안티 패턴)**:

  ```
  CRITICAL: You MUST verify the schema before EVERY single write. IMPORTANT:
  do NOT skip this step under ANY circumstances.
  ```

- **After (권장)**:

  ```
  Verify the schema before each write.
  ```

- **적용 대상**: 에이전트, 스킬, 커맨드, 규칙 모두.

### 규칙 4. 필터 지시 제거 또는 정량화 — recall 저하 방지

- **규칙**: `be conservative`, `only if confident`, `when very sure`, "보수적으로", "확실할 때만" 같은 추상 필터어를 삭제한다. 필터링이 정말 필요하면 객관적 임계값(점수 ≥ N, 카테고리 == X 등)으로 대체한다.
- **근거**: 연구 §1 항목 4 — 현행 Opus는 추상 필터어를 충실히 적용해 borderline 케이스를 모두 버린다. 결과적으로 recall이 떨어지고 사용자가 기대하는 후보가 누락된다.
- **Before (안티 패턴)**:

  ```
  Return matches only when you are highly confident. Be conservative.
  ```

- **After (권장)**:

  ```
  Return matches with similarity score >= 0.7. Sort by score descending.
  ```

- **적용 대상**: 에이전트(특히 reviewer, classifier), 스킬(검색·필터링 단계).

### 규칙 5. CoT 명시 지시 제거 — adaptive thinking 신뢰

- **규칙**: `think step by step`, `let's think carefully`, "단계별로 사고하라", "차근차근 추론하라" 같은 CoT 명시 지시를 삭제한다. 현행 Opus는 작업 복잡도에 맞춰 자체적으로 사고 깊이를 조절한다.
- **근거**: 연구 §1 항목 5 — 명시적 CoT 지시는 현행 Opus의 adaptive thinking 회로와 충돌해, 단순 작업에 과도한 추론을 강제하거나 추론 형식이 산출물 형식과 섞이는 부작용을 일으킨다.
- **Before (안티 패턴)**:

  ```
  Think step by step. Let's think carefully about each option before answering.
  Then provide the final classification.
  ```

- **After (권장)**:

  ```
  Provide the final classification.
  ```

- **적용 대상**: 에이전트, 스킬(특히 분류·판정 단계).

### 규칙 6. 첫 turn 정보 front-load — 핵심 정보를 도입부에 배치

- **규칙**: 역할·목표·산출물 형식·제약 조건 같은 핵심 정보를 프롬프트 도입부 한 블록에 모은다. 후속 섹션이나 사용자 turn에 흩어 두지 않는다.
- **근거**: 연구 §1 항목 6 — 현행 Opus는 첫 turn의 attention 가중치가 높아 도입부에 없는 정보는 후속 turn에서 검색 비용이 커지고 따르지 않을 확률이 올라간다.
- **Before (안티 패턴)**:

  ```
  You are a code reviewer.
  ## Step 1
  Read the diff.
  ## Step 5
  By the way, only review TypeScript files. Output as JSON with fields
  {file, severity, message}.
  ```

- **After (권장)**:

  ```
  You are a code reviewer.

  Scope: TypeScript files only.
  Output: JSON array of {file, severity, message}.

  ## Step 1
  Read the diff.
  ```

- **적용 대상**: 에이전트, 스킬, 커맨드.

### 규칙 7. 도구 호출 트리거 명시 — 호출 시점·조건을 직접 진술

- **규칙**: 도구 사용이 기대되면 "X 조건이면 도구 Y를 호출한다" 형태로 호출 시점·조건을 명시한다. "필요하면 도구를 사용하라" 같은 모호한 진술은 사용하지 않는다.
- **근거**: 연구 §1 항목 7 — 현행 Opus는 도구 호출 기본 빈도가 낮아져, 모호한 진술 하에서는 도구를 호출하지 않고 추론으로 대체한다. 명시 트리거가 있어야 호출이 일관된다.
- **Before (안티 패턴)**:

  ```
  Use tools as needed to gather information.
  ```

- **After (권장)**:

  ```
  Before answering, call Read on the file referenced in the user message.
  When the user references a directory, call Glob with pattern "**/*.md".
  ```

- **적용 대상**: 에이전트(도구 보유), 스킬(도구 호출 단계 포함).

## 3. 적용 대상 요약

행=7가지 규칙, 열=컴포넌트 유형. 셀 표기 — 필수 / 권장 / 해당 없음.

| 규칙 | 에이전트 | 스킬 | 커맨드 | 규칙(rules) |
|------|---------|------|--------|-------------|
| 1. hedge 제거 | 필수 | 필수 | 필수 | 필수 |
| 2. 스코프 명시 | 필수 | 필수 | 필수 (배치 지시 포함) | 권장 |
| 3. anti-laziness 스캐폴딩 제거 | 필수 | 필수 | 필수 | 필수 |
| 4. 필터 지시 제거 또는 정량화 | 필수 (reviewer·classifier) | 필수 (필터링 단계) | 권장 | 해당 없음 |
| 5. CoT 명시 지시 제거 | 필수 | 필수 (판정 단계) | 권장 | 해당 없음 |
| 6. 첫 turn 정보 front-load | 필수 | 필수 | 필수 | 권장 |
| 7. 도구 호출 트리거 명시 | 필수 (도구 보유) | 권장 (도구 호출 단계) | 해당 없음 | 해당 없음 |
