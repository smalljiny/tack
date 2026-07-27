// 위험 tier 라우팅 정적 assertion.
//
// 편집 대상이 전부 `template/` 하위이고 이 저장소의 hub 세션은 부트스트랩 하네스로
// 동작하므로, 편집한 template 컴포넌트는 이 저장소에서 실행되지 않는다. 따라서
// 라이브 실행 대신 합성 plan fixture를 입력으로 두고 편집된 template 파일에
// 라우팅 규칙·Type 분기·stage 분기·fallback 문구가 존재하는지 정적으로 검증한다.
//
// 실행: node --test scripts/risk-routing-assertions.test.js
// 경로는 cwd가 아니라 이 파일의 위치를 기준으로 해석하므로 어느 디렉토리에서 호출해도 동작한다.
//
// Node 요구 사항: `import.meta.dirname`(≥20.11)과 package.json 없는 `.js`의 ESM 자동
// 감지(≥22.7)를 사용한다. 이 파일은 `_subdirectory: template` 밖이라 배포 대상이 아니며
// 이 저장소의 개발 환경에서만 실행된다.
//
// anti-vacuity는 두 층으로 검증한다.
//   1. 통제군 fixture — 라우팅 규칙이 전혀 없는 별개 컴포넌트 본문에 6개 assertion 전부 실패
//   2. 절 삭제 통제 — 실제 대상 파일에서 각 assertion이 겨냥하는 절만 제거하면 그 assertion 실패
// 2층이 없으면 assertion이 대상 파일의 다른 위치에 우연히 존재하는 토큰으로 통과할 수 있다.

import { test, describe } from 'node:test'
import assert from 'node:assert'
import { readFileSync } from 'node:fs'

const REPO_ROOT = `${import.meta.dirname}/..`
const FIXTURE_DIR = `${import.meta.dirname}/fixtures/risk-routing`

const TARGETS = {
  planner: `${REPO_ROOT}/template/.claude/agents/planner.md`,
  flowImpl: `${REPO_ROOT}/template/.claude/skills/flow-impl/SKILL.md`,
  flowReview: `${REPO_ROOT}/template/.claude/skills/flow-review/SKILL.md`,
  riskRouting: `${REPO_ROOT}/template/.claude/skills/wf-risk-routing/SKILL.md`,
}

// 각 assertion이 겨냥하는 절의 heading 앵커. 절 삭제 통제의 입력이기도 하다.
const ANCHORS = {
  plannerDecomposition: /^#{1,6}\s+4\.7\.5\./,
  flowImplTypeRouting: /^#{1,6}\s+5\..*Story Type/,
  flowReviewStageBranch: /^#{1,6}\s+5-B\./,
}

const NORMAL_FALLBACK_SENTENCE = '필드가 없는 Story는 `normal`로 간주한다'
const DELEGATION_LITERAL =
  'Load `.claude/skills/wf-risk-routing/SKILL.md` and follow its process.'

const read = (path) => readFileSync(path, 'utf8')
const readFixture = (name) => read(`${FIXTURE_DIR}/${name}`)

// --- markdown 절 추출 -------------------------------------------------------

/**
 * fenced code block 안의 `#` 라인은 heading으로 세지 않는다.
 * 출력 형식 템플릿이 코드 블록으로 들어 있는 파일에서 절 경계가 어긋나는 것을 막는다.
 */
function headingMask(lines) {
  let inFence = false
  return lines.map((line) => {
    if (/^\s*```/.test(line)) {
      inFence = !inFence
      return false
    }
    return !inFence && /^#{1,6}\s/.test(line)
  })
}

/** heading 앵커에 일치하는 절의 범위 [start, end)를 돌려준다. 없으면 null. */
function sectionRange(text, anchor) {
  const lines = text.split('\n')
  const isHeading = headingMask(lines)
  const start = lines.findIndex((line, i) => isHeading[i] && anchor.test(line))
  if (start === -1) return null
  let end = start + 1
  while (end < lines.length && !isHeading[end]) end += 1
  return { lines, start, end }
}

/** heading 앵커에 일치하는 절 본문. 없으면 null. */
function sectionUnderHeading(text, anchor) {
  const range = sectionRange(text, anchor)
  if (!range) return null
  return range.lines.slice(range.start, range.end).join('\n')
}

/** heading 앵커에 일치하는 절을 제거한 텍스트. 절이 없으면 원문 그대로. */
function withoutSection(text, anchor) {
  const range = sectionRange(text, anchor)
  if (!range) return text
  return [...range.lines.slice(0, range.start), ...range.lines.slice(range.end)].join('\n')
}

// --- fixture 파싱 -----------------------------------------------------------

/**
 * 합성 plan 조각에서 Story Type과 Risk Tier를 추출한다.
 * Risk Tier 필드가 없으면 tier는 null이다 (fallback 케이스).
 */
function parseStoryFragment(markdown) {
  const type = markdown.match(/^- \*\*Type\*\*:\s*(\S+)/m)?.[1] ?? null
  const tier = markdown.match(/^- \*\*Risk Tier\*\*:\s*(low|normal|high)\b/m)?.[1] ?? null
  return { type, tier }
}

// --- assertion 함수 (검사 대상 텍스트, fixture) → 판정 ------------------------
//
// 모든 함수는 텍스트를 첫 인자로 받아, 통제군 텍스트와 절 삭제 텍스트에 같은 함수를
// 그대로 적용할 수 있게 한다.

/** (1) planner가 high + tdd/refactor Story를 scaffold로 분해하는 규칙을 담는가. */
function hasPlannerDecompositionRule(text, story) {
  if (!(story.tier === 'high' && (story.type === 'tdd' || story.type === 'refactor'))) return false
  const section = sectionUnderHeading(text, ANCHORS.plannerDecomposition)
  if (!section) return false
  return (
    /\bscaffold\b/.test(section) &&
    /\bhigh\b/.test(section) &&
    /\btdd\b/.test(section) &&
    /\brefactor\b/.test(section) &&
    /분해/.test(section) &&
    /throwing stub/.test(section)
  )
}

/** (2) flow-impl이 scaffold Type을 별도 처리 경로로 라우팅하는가. */
function hasScaffoldTypeRouting(text) {
  const section = sectionUnderHeading(text, ANCHORS.flowImplTypeRouting)
  if (!section) return false
  const hasBranch = /\*\*Type: `scaffold`\*\*/.test(section)
  const skipsTddSpecialist = /tdd-specialist를 호출하지 않는다/.test(section)
  const hasTypeEnum = /\*\*Type\*\*:.*\bscaffold\b/.test(text)
  return hasBranch && skipsTddSpecialist && hasTypeEnum
}

/** (3) flow-review가 stage 1 → lock → stage 2 분기를 담는가. */
function hasStageBranch(text) {
  const section = sectionUnderHeading(text, ANCHORS.flowReviewStageBranch)
  if (!section) return false
  return (
    /stage 1/.test(section) &&
    /stage 2/.test(section) &&
    /`lock == locked`/.test(section) &&
    /`lock == blocked`/.test(section) &&
    /topicTier == high/.test(section)
  )
}

/** (4) wf-risk-routing이 Risk Tier 필드 부재를 normal로 처리하는 fallback을 담는가. */
function hasNormalFallback(text, story) {
  if (story.tier !== null) return false
  return text.includes(NORMAL_FALLBACK_SENTENCE)
}

/** (5)(6) 소비자 파일이 표준 위임 문구 리터럴을 담는가. */
function hasDelegationLiteral(text) {
  return text.includes(DELEGATION_LITERAL)
}

// --- 핵심 assertion 4개 -----------------------------------------------------

describe('core assertions on edited template components', () => {
  test('(1) planner defines the scaffold decomposition rule for high + tdd/refactor', () => {
    const story = parseStoryFragment(readFixture('plan-high-tdd.md'))
    assert.deepStrictEqual(story, { type: 'tdd', tier: 'high' })
    assert.ok(
      hasPlannerDecompositionRule(read(TARGETS.planner), story),
      'planner.md §4.7.5에 high + tdd/refactor → scaffold 분해 규칙이 없습니다',
    )
  })

  test('(2) flow-impl routes the scaffold Story Type', () => {
    assert.ok(
      hasScaffoldTypeRouting(read(TARGETS.flowImpl)),
      'flow-impl/SKILL.md Step 5에 scaffold Type 라우팅이 없습니다',
    )
  })

  test('(3) flow-review branches stage 1 -> lock -> stage 2', () => {
    assert.ok(
      hasStageBranch(read(TARGETS.flowReview)),
      'flow-review/SKILL.md Step 5-B에 stage 1 → lock → stage 2 분기가 없습니다',
    )
  })

  test('(4) wf-risk-routing falls back to normal when the tier field is absent', () => {
    const story = parseStoryFragment(readFixture('plan-no-tier.md'))
    assert.strictEqual(story.tier, null)
    assert.ok(
      hasNormalFallback(read(TARGETS.riskRouting), story),
      'wf-risk-routing/SKILL.md에 필드 부재 → normal fallback이 없습니다',
    )
  })
})

// --- 소비자 위임 assertion 2개 ----------------------------------------------

describe('consumer delegation assertions', () => {
  test('(5) flow-impl carries the standard delegation literal', () => {
    assert.ok(
      hasDelegationLiteral(read(TARGETS.flowImpl)),
      'flow-impl/SKILL.md에 표준 위임 문구가 없습니다',
    )
  })

  test('(6) flow-review carries the standard delegation literal', () => {
    assert.ok(
      hasDelegationLiteral(read(TARGETS.flowReview)),
      'flow-review/SKILL.md에 표준 위임 문구가 없습니다',
    )
  })
})

// --- anti-vacuity 통제군 (1층: 무관한 컴포넌트 본문) --------------------------
//
// 라우팅 규칙이 전혀 없는 컴포넌트 본문에 같은 6개 assertion을 적용하면 모두
// 실패해야 한다. 하나라도 통과하면 그 assertion은 vacuous하며 실제 규칙 부재를
// 잡아내지 못한다.

describe('anti-vacuity control (unrelated component body)', () => {
  test('all six assertions fail on the control fixture', () => {
    const control = readFixture('control-no-rules.md')
    const highTddStory = parseStoryFragment(readFixture('plan-high-tdd.md'))
    const noTierStory = parseStoryFragment(readFixture('plan-no-tier.md'))

    const verdicts = {
      '(1) planner decomposition': hasPlannerDecompositionRule(control, highTddStory),
      '(2) scaffold Type routing': hasScaffoldTypeRouting(control),
      '(3) stage branch': hasStageBranch(control),
      '(4) normal fallback': hasNormalFallback(control, noTierStory),
      '(5) delegation literal in the flow-impl slot': hasDelegationLiteral(control),
      '(6) delegation literal in the flow-review slot': hasDelegationLiteral(control),
    }

    const passed = Object.entries(verdicts)
      .filter(([, verdict]) => verdict === true)
      .map(([name]) => name)

    assert.deepStrictEqual(
      passed,
      [],
      `통제군에서 통과한 assertion이 있습니다 (vacuous): ${passed.join(', ')}`,
    )
  })
})

// --- anti-vacuity 통제군 (2층: 실제 대상 파일에서 해당 절만 삭제) --------------
//
// 각 assertion이 겨냥하는 절을 실제 대상 파일에서 제거하면 그 assertion만 실패해야
// 한다. 1층 통제군은 무관한 본문에 대한 실패만 증명하므로, 대상 파일의 다른 위치에
// 우연히 존재하는 토큰으로 통과하는 경우를 잡지 못한다.

describe('anti-vacuity control (section removed from the real target file)', () => {
  test('(1) fails when planner §4.7.5 is removed', () => {
    const story = parseStoryFragment(readFixture('plan-high-tdd.md'))
    const mutated = withoutSection(read(TARGETS.planner), ANCHORS.plannerDecomposition)
    assert.notStrictEqual(mutated, read(TARGETS.planner), '절이 제거되지 않았습니다 (앵커 불일치)')
    assert.strictEqual(hasPlannerDecompositionRule(mutated, story), false)
  })

  test('(2) fails when the flow-impl Story Type routing step is removed', () => {
    const mutated = withoutSection(read(TARGETS.flowImpl), ANCHORS.flowImplTypeRouting)
    assert.notStrictEqual(mutated, read(TARGETS.flowImpl), '절이 제거되지 않았습니다 (앵커 불일치)')
    assert.strictEqual(hasScaffoldTypeRouting(mutated), false)
  })

  test('(3) fails when the flow-review 5-B branch is removed', () => {
    const mutated = withoutSection(read(TARGETS.flowReview), ANCHORS.flowReviewStageBranch)
    assert.notStrictEqual(
      mutated,
      read(TARGETS.flowReview),
      '절이 제거되지 않았습니다 (앵커 불일치)',
    )
    assert.strictEqual(hasStageBranch(mutated), false)
  })

  test('(4) fails when the normal fallback sentence is removed', () => {
    const story = parseStoryFragment(readFixture('plan-no-tier.md'))
    const original = read(TARGETS.riskRouting)
    const mutated = original.split(NORMAL_FALLBACK_SENTENCE).join('')
    assert.notStrictEqual(mutated, original, 'fallback 문장이 제거되지 않았습니다')
    assert.strictEqual(hasNormalFallback(mutated, story), false)
  })

  test('(5)(6) each consumer fails when its own delegation literal is removed', () => {
    for (const key of ['flowImpl', 'flowReview']) {
      const original = read(TARGETS[key])
      const mutated = original.split(DELEGATION_LITERAL).join('')
      assert.notStrictEqual(mutated, original, `${key}에 위임 문구가 없습니다`)
      assert.strictEqual(hasDelegationLiteral(mutated), false, `${key} 위임 assertion이 vacuous합니다`)
    }
  })
})
