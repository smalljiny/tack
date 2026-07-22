# Diagnostic Patterns

> stack-prompt REFINE 단계가 lazy-load해 사용하는 진단 카탈로그.
> prompt-master `references/patterns.md`의 37개 credit-killing 패턴 중 하네스 컨텍스트 적용 불가 3개(image AI 전용 2개, emotional task description 1개)를 제외한 34개를 6 카테고리로 그룹핑했다.

이 카탈로그는 사용자가 보낸 프롬프트가 underperform하거나 EVAL이 fail로 떨어졌을 때 원인 패턴을 빠르게 식별하기 위한 참조표다. 각 행은 `#ID | Pattern | Bad Example | Fixed` 컬럼으로 구성되며, ID는 prompt-master 원본 패턴 번호를 보존한다. 출처와 라이선스는 문서 말미 footer 참조.

---

## Task 카테고리 (6개)

| # | Pattern | Bad Example | Fixed |
|---|---------|-------------|-------|
| #1 | **Vague task verb** | "help me with my code" | "Refactor `getUserData()` to use async/await and handle null returns" |
| #2 | **Two tasks in one prompt** | "explain AND rewrite this function" | Split into two prompts: explain first, rewrite second |
| #3 | **No success criteria** | "make it better" | "Done when the function passes existing unit tests and handles null input without throwing" |
| #4 | **Over-permissive agent** | "do whatever it takes" | Explicit allowed actions list + explicit forbidden actions list |
| #6 | **Build-the-whole-thing** | "build my entire app" | Break into Prompt 1 (scaffold), Prompt 2 (core feature), Prompt 3 (polish) |
| #7 | **Implicit reference** | "now add the other thing we discussed" | Always restate the full task — never reference "the thing we discussed" |

---

## Context 카테고리 (6개)

| # | Pattern | Bad Example | Fixed |
|---|---------|-------------|-------|
| #8 | **Assumed prior knowledge** | "continue where we left off" | Include Memory Block with all prior decisions |
| #9 | **No project context** | "write a cover letter" | "PM role at B2B fintech, 2yr SWE experience transitioning to product, shipped 3 features as tech lead" |
| #10 | **Forgotten stack** | New prompt contradicts prior tech choice | Always include Memory Block with established stack |
| #11 | **Hallucination invite** | "what do experts say about X?" | "Cite only sources you are certain of. If uncertain, say so explicitly rather than guessing." |
| #12 | **Undefined audience** | "write something for users" | "Non-technical B2B buyers, no coding knowledge, decision-maker level" |
| #13 | **No mention of prior failures** | (blank) | "I already tried X and it didn't work because Y. Do not suggest X." |

---

## Format 카테고리 (4개) — image AI 전용 패턴 제외

| # | Pattern | Bad Example | Fixed |
|---|---------|-------------|-------|
| #14 | **Missing output format** | "explain this concept" | "3 bullet points, each under 20 words, with a one-sentence summary at top" |
| #15 | **Implicit length** | "write a summary" | "Write a summary in exactly 3 sentences" |
| #16 | **No role assignment** | (blank) | "You are a senior backend engineer specializing in Node.js and PostgreSQL" |
| #17 | **Vague aesthetic adjectives** | "make it look professional" | "Monochrome palette, 16px base font, 24px line height, no decorative elements" |

---

## Scope 카테고리 (6개)

| # | Pattern | Bad Example | Fixed |
|---|---------|-------------|-------|
| #20 | **No scope boundary** | "fix my app" | "Fix only the login form validation in `src/auth.js`. Touch nothing else." |
| #21 | **No stack constraints** | "build a React component" | "React 18, TypeScript strict, no external libraries, Tailwind only" |
| #22 | **No stop condition for agents** | "build the whole feature" | Explicit stop conditions + ✅ checkpoint output after each step |
| #23 | **No file path for IDE AI** | "update the login function" | "Update `handleLogin()` in `src/pages/Login.tsx` only" |
| #24 | **Wrong template for tool** | GPT-style prose prompt used in Cursor | Adapt to File-Scope Template (Template G) |
| #25 | **Pasting entire codebase** | Full repo context every prompt | Scope to only the relevant function and file |

---

## Reasoning 카테고리 (5개)

| # | Pattern | Bad Example | Fixed |
|---|---------|-------------|-------|
| #26 | **No CoT for logic task** | "which approach is better?" | "Think through both approaches step by step before recommending" |
| #27 | **Adding CoT to reasoning models** | "think step by step" sent to o1/o3 | Remove it — reasoning models think internally, CoT instructions degrade output |
| #28 | **Expecting inter-session memory** | "you already know my project" | Always re-provide the Memory Block in every new session |
| #29 | **Contradicting prior work** | New prompt ignores earlier architecture | Include Memory Block with all established decisions |
| #30 | **No grounding rule for factual tasks** | "summarize what experts say about X" | "Use only information you are highly confident is accurate. Say [uncertain] if not." |

---

## Agentic 카테고리 (7개)

| # | Pattern | Bad Example | Fixed |
|---|---------|-------------|-------|
| #31 | **No starting state** | "build me a REST API" | "Empty Node.js project, Express installed, `src/app.js` exists" |
| #32 | **No target state** | "add authentication" | "`/src/middleware/auth.js` with JWT verify. `POST /login` and `POST /register` in `/src/routes/auth.js`" |
| #33 | **Silent agent** | No progress output | "After each step output: ✅ [what was completed]" |
| #34 | **Unlocked filesystem** | No file restrictions | "Only edit files inside `src/`. Do not touch `package.json`, `.env`, or any config file." |
| #35 | **No human review trigger** | Agent decides everything autonomously | "Stop and ask before: deleting any file, adding any dependency, or changing the database schema" |
| #36 | **Vague first turn on Opus 4.7** | "fix the auth bug" with no scope, no files, no criteria | Opus 4.7 reads prompts literally — it no longer fills implicit context like 4.6 did. Use Template M. Front-load intent, file scope, constraints, and acceptance criteria. |
| #37 | **Context rot on long sessions** | Keeps correcting in the same session for 60+ turns | New task = new session. Use /rewind instead of correcting. /compact at ~50% context. Subagents for file-heavy investigation. |
