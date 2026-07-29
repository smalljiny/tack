// adapter-codex-review의 새 리뷰 파일 탐지 회귀 테스트.
//
// `## Parsing the Decision` 절의 bash 코드 펜스 블록을 문서에서 **추출해 실제로 실행**한다.
// 정적 grep이 아니라 실행이어야 하는 이유는 이번 버그가 문법이 아니라 셸 의미론이기
// 때문이다 — zsh는 변수 치환 결과를 글롭 확장하지 않아 `ls "$DIR"/$PATTERN`이 리터럴
// 파일명을 찾고 실패한다. bash에서는 같은 줄이 정상 동작하므로 두 셸 매트릭스가 필수다.
//
// 두 번째 층은 전수 스캔 게이트다 — 같은 유형의 변수-글롭이 template 스킬 문서 전체에서
// 0건임을 강제한다.
//
// 스캔 범위: `template/.claude/skills/**/SKILL.md`의 `bash` 코드 펜스 **안쪽**만. 확장하지
// 않는다. 넓은 범위(`agents/*.md`, `*.sh` 포함) 사전 조사에서 실제 위반 0건, false positive
// 2건(`learned/bash-set-u-empty-array/SKILL.md` 산문, `stack-backend/SKILL.md` JS 템플릿
// 리터럴)만 나왔다 — 확장은 위반 커버리지를 늘리지 않고 오탐 억제 작업만 늘린다. 펜스 바깥
// 산문을 제외하는 이유도 같다: 좁은 범위에서도 `learned/` 산문 줄이 오탐으로 걸린다.
//
// 강제 술어의 실제 경계: "**같은 bash 펜스 블록 안에서 리터럴 따옴표 대입으로 선언된**
// 글롭-값 변수의 unquoted 확장". 범위 밖 — 따옴표 없는 대입(`PATTERN=*.md`), 블록 간 참조
// (블록 A에서 대입, 블록 B에서 사용), 명령 치환 대입(`PATTERN=$(cat globs.txt)`), 배열
// (`PATTERNS=('*.md')` + `${PATTERNS[0]}`). 현재 코퍼스에 이 shape의 실제 사례는 없다.
// `stripQuotedSpans`도 escape(`\"`)·같은 종류의 중첩 따옴표·heredoc 본문을 해석하지 않아
// `VAR="$(cmd "$G")"` 형태와 주석 줄의 `$G` 언급은 오탐 방향으로 걸린다.
//
// 실행: node --test scripts/codex-review-detection.test.js
// 이 명령이 유일한 실행법이다. `wf-verification` Gate 4에는 등록하지 않는다 — Gate 4는
// `pnpm test`/`pnpm test:coverage`를 실행하는데 이 저장소에 루트 `package.json`이 없어
// 실행 자체가 불가하다.
// 경로는 cwd가 아니라 이 파일의 위치를 기준으로 해석하므로 어느 디렉토리에서 호출해도 동작한다.
//
// Node 요구 사항: `import.meta.dirname`(≥20.11)과 package.json 없는 `.js`의 ESM 자동
// 감지(≥22.7)를 사용한다. 이 파일은 `_subdirectory: template` 밖이라 배포 대상이 아니며
// 이 저장소의 개발 환경에서만 실행된다.
//
// 셸 격리: 추출된 블록은 `zsh -f`와 `bash --noprofile --norc`로 실행하고 자식 환경에서
// `BASH_ENV`·`ENV`·`ZDOTDIR`를 제거한다. zsh는 비대화형 스크립트에서도 `.zshenv`를 읽고 그
// 안의 별칭을 확장하므로, 격리하지 않으면 개발자의 `alias ls=…` 하나로 anti-vacuity 통제가
// 조용히 green이 된다 (bash는 비대화형에서 별칭을 확장하지 않아 대칭이 깨진다). `setopt
// GLOB_SUBST`는 반대로 fixture 케이스를 red로 만들어 fail-safe다. `LC_ALL=C`로 `sort`·`comm`
// 콜레이션도 고정한다. `zsh -f`가 막지 못하는 `/etc/zshenv`는 macOS 기본 배포에 없다.
//
// anti-vacuity: 수정 **전** 블록을 체크인 fixture(`fixtures/codex-review-detection/`)로
// 두고 같은 파이프라인에 통과시켜, zsh에서 C1·C2가 실패하고 bash에서 통과함을 고정한다.
// `git show` 재구성은 fresh clone·squash 후 깨지므로 쓰지 않는다.
//
// 이 테스트는 루트 배포 사본(`.claude/skills/…`) 경로를 참조하지 않는다 — `.git/info/exclude`
// 로 untracked라 fresh clone에 존재하지 않는다.

import { test, describe, after } from 'node:test'
import assert from 'node:assert'
import { readFileSync, writeFileSync, mkdtempSync, existsSync, rmSync, globSync } from 'node:fs'
import { spawnSync } from 'node:child_process'
import { tmpdir } from 'node:os'
import { join } from 'node:path'

const REPO_ROOT = `${import.meta.dirname}/..`
const FIXTURE_DIR = `${import.meta.dirname}/fixtures/codex-review-detection`

const CANON_SKILL = `${REPO_ROOT}/template/.claude/skills/adapter-codex-review/SKILL.md`
const PRE_FIX_FIXTURE = `${FIXTURE_DIR}/pre-fix-section.md`

// 전수 스캔의 유일한 수집 경로. `scripts/fixtures/` 하위는 이 glob에 포함되지 않으며,
// fixture는 `PRE_FIX_FIXTURE`를 직접 읽는 별개 진입점으로 탐지기에 들어간다.
const SKILL_GLOB = `${REPO_ROOT}/template/.claude/skills/**/SKILL.md`
const NEGATIVE_CONTROL_SKILL = `${REPO_ROOT}/template/.claude/skills/learned/bash-set-u-empty-array/SKILL.md`

const PARSING_ANCHOR = /^#{1,6}\s+Parsing the Decision\s*$/
const PHASE_ROUTING_ANCHOR = /^#{1,6}\s+2\.\s+phase:status/
const ISOLATION_ANCHOR = /^#{1,6}\s+Isolation via DEV_CONTEXT_PATH\s*$/

const read = (path) => readFileSync(path, 'utf8')

// --- markdown 절·코드블록 추출 ----------------------------------------------

/**
 * fenced code block 안의 `#` 라인은 heading으로 세지 않는다.
 * 코드 블록 안 주석(`# 1. 실행 전 …`)이 절 경계를 끊는 것을 막는다.
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

const headingLevel = (line) => line.match(/^(#{1,6})\s/)?.[1].length ?? 0

/** heading 앵커에 일치하는 절의 범위 [start, end)를 돌려준다. 없으면 null. */
function sectionRange(text, anchor) {
  const lines = text.split('\n')
  const isHeading = headingMask(lines)
  const start = lines.findIndex((line, i) => isHeading[i] && anchor.test(line))
  if (start === -1) return null
  const level = headingLevel(lines[start])
  let end = start + 1
  while (end < lines.length && !(isHeading[end] && headingLevel(lines[end]) <= level)) end += 1
  return { lines, start, end }
}

/** heading 앵커에 일치하는 절 본문. 없으면 null. */
function sectionUnderHeading(text, anchor) {
  const range = sectionRange(text, anchor)
  if (!range) return null
  return range.lines.slice(range.start, range.end).join('\n')
}

/** 텍스트 안의 첫 번째 ```bash 펜스 블록 본문. 없으면 null. */
function firstBashBlock(text) {
  const block = allBashBlocks(text)[0]
  return block ? block.lines.join('\n') : null
}

/** 지정 절의 첫 bash 블록을 꺼낸다. */
function sectionBlock(markdown, anchor, label) {
  const section = sectionUnderHeading(markdown, anchor)
  assert.ok(section, `${label} 절을 찾지 못했다`)
  const block = firstBashBlock(section)
  assert.ok(block, `${label} 절에 bash 코드 펜스 블록이 없다`)
  return block
}

/** `## Parsing the Decision` 절의 첫 bash 블록. */
const parsingBlock = (markdown) =>
  sectionBlock(markdown, PARSING_ANCHOR, '`## Parsing the Decision`')

/** `### 2. phase:status → 실행 스킬 결정` 절의 첫 bash 블록 (REVIEW_KIND 생산자). */
const phaseRoutingBlock = (markdown) =>
  sectionBlock(markdown, PHASE_ROUTING_ANCHOR, '`### 2. phase:status`')

/**
 * 텍스트 안의 모든 ```bash 펜스 블록을 원문 줄 번호와 함께 돌려준다.
 * @returns {{lines: string[], startLine: number}[]} startLine은 블록 첫 줄의 1-based 원문 줄 번호
 */
function allBashBlocks(text) {
  const lines = text.split('\n')
  const blocks = []
  let open = -1
  for (let i = 0; i < lines.length; i += 1) {
    if (open === -1) {
      if (/^\s*```bash\s*$/.test(lines[i])) open = i
      continue
    }
    if (/^\s*```\s*$/.test(lines[i])) {
      blocks.push({ lines: lines.slice(open + 1, i), startLine: open + 2 })
      open = -1
    }
  }
  return blocks
}

// --- 변수-글롭 탐지기 (Story 2) ----------------------------------------------
//
// 정의는 spec §3.3의 "확장 직후 글롭 메타문자" 문구를 쓰지 않는다 — 그 정의는 정작 이번
// 버그(`ls "$REVIEW_DIR"/$PATTERN`)를 매치하지 못한다. 소스 텍스트에는 확장에 인접한 글롭
// 메타문자가 없고, `$PATTERN`이 *담고 있는 값*이 글롭이기 때문이다. 대신 대입값을 본다.

const GLOB_METACHARS = /[*?[]/

/** 줄에서 single·double quoted span을 제거한다. 줄 단위로만 처리한다. */
function stripQuotedSpans(line) {
  let out = ''
  let quote = null
  for (const ch of line) {
    if (quote) {
      if (ch === quote) quote = null
      continue
    }
    if (ch === "'" || ch === '"') {
      quote = ch
      continue
    }
    out += ch
  }
  return out
}

const GLOB_ASSIGNMENT = /^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)=(?:'([^']*)'|"([^"]*)")/

/** 한 블록에서 글롭 메타문자를 값에 담은 따옴표 대입의 변수명 집합 G. */
function globValuedVars(blockLines) {
  const globVars = new Set()
  for (const line of blockLines) {
    const assignment = line.match(GLOB_ASSIGNMENT)
    if (!assignment) continue
    const value = assignment[2] ?? assignment[3]
    if (GLOB_METACHARS.test(value)) globVars.add(assignment[1])
  }
  return globVars
}

/**
 * 글롭 값을 담은 변수가 따옴표 없이 확장되는 위치를 찾는다.
 *
 * 3단계 — (1) 입력에서 bash 펜스 블록만 취한다 (펜스 바깥 산문은 대상이 아니다).
 * (2) 블록마다 글롭 메타문자를 값에 포함한 따옴표 대입 `VAR='…'` / `VAR="…"`의 변수명
 * 집합 G를 만든다. 대입 인식은 줄 앞(선택적 `export `)에 앵커해 주석 줄이 G를 오염시키지
 * 못하게 한다. (3) 같은 블록의 각 줄에서 quoted span을 **줄 단위로** 제거한 뒤 남은
 * 텍스트에 `$VAR`·`${VAR}` (VAR ∈ G)가 있으면 위반이다. 제거를 블록 단위로 하면 한 줄의
 * 미종결 따옴표가 뒤따르는 줄들을 통째로 삼킨다.
 *
 * @param {string} markdown bash 펜스를 포함한 문서 텍스트
 * @returns {{line: number, varName: string}[]} line은 1-based 원문 줄 번호
 */
function detectViolations(markdown) {
  const violations = []
  for (const block of allBashBlocks(markdown)) {
    const globVars = globValuedVars(block.lines)
    if (globVars.size === 0) continue

    // varName은 `[A-Za-z_][A-Za-z0-9_]*`에 갇혀 있어 정규식 메타문자가 들어올 수 없다.
    const matchers = [...globVars].map((varName) => [
      varName,
      new RegExp(`\\$\\{?${varName}\\}?(?![A-Za-z0-9_])`),
    ])

    block.lines.forEach((line, i) => {
      const bare = stripQuotedSpans(line)
      for (const [varName, expansion] of matchers) {
        if (expansion.test(bare)) violations.push({ line: block.startLine + i, varName })
      }
    })
  }
  return violations
}

/** 탐지기가 실제로 stage 3까지 검사하는 블록 수 (G가 비지 않은 블록). */
function scannedBlockCount(markdown) {
  return allBashBlocks(markdown).filter((block) => globValuedVars(block.lines).size > 0).length
}

// --- 실행 하네스 -------------------------------------------------------------

/** `command -v`로 셸 경로를 resolve한다. 없으면 null. */
function resolveShell(name) {
  const probe = spawnSync('/bin/sh', ['-c', `command -v ${name}`], { encoding: 'utf8' })
  const path = probe.stdout.trim()
  return probe.status === 0 && path ? path : null
}

// skip이 아니라 실패로 처리한다 — 매트릭스가 조용히 반쪽으로 도는 것을 막는다 (T1.3).
const SHELLS = {
  zsh: { path: resolveShell('zsh'), args: ['-f'] },
  bash: { path: resolveShell('bash'), args: ['--noprofile', '--norc'] },
}

// 어댑터는 spec-review·plan-review 두 phase가 같은 Parsing 블록을 공유한다. 한쪽만 검증하면
// `PATTERN`이 한 phase로 하드코딩돼도 green으로 남으므로 매트릭스를 두 kind로 돌린다.
const REVIEW_KINDS = ['spec-review', 'plan-review']

const newFileFor = (kind) => `${kind}-260729120000.md`

// seed 세 번째는 새 파일보다 **뒤로** 정렬된다 (LC_ALL=C). 이 seed가 없으면 `comm -13`을
// 통째로 없애고 `tail -1` of AFTER만 써도 C2가 통과해, 케이스가 diff 의미론을 고정하지 못한다.
const seedFilesFor = (kind) => [
  `${kind}-260101000000.md`,
  `${kind}-260102000000.md`,
  `${kind}-269999999999.md`,
]

// 새 파일보다 뒤로 정렬되는 하위 디렉토리 이름 (`spec-`·`plan-` 둘 다 `z`보다 앞선다).
// `-maxdepth 1`이 풀리면 `tail -1`이 이쪽 파일을 집으므로 깊이 경계가 관측된다.
const NESTED_DIR = 'zz-nested'

/** 코드 블록의 `PATTERN=` 대입값. `$REVIEW_KIND` 확장은 `kind`로 치환해 해석한다. */
function patternValue(block, kind) {
  const raw = block.match(/^PATTERN=(?:'([^']*)'|"([^"]*)")/m)
  assert.ok(raw, '블록에서 `PATTERN=` 대입을 찾지 못했다')
  const value = raw[1] ?? raw[2]
  // `${REVIEW_KIND}`·`$REVIEW_KIND`뿐 아니라 `${REVIEW_KIND:?msg}` 같은 기본값 형태도
  // 바인딩된 경우의 확장 결과로 해석한다.
  return value.replace(/\$\{REVIEW_KIND[^}]*\}|\$REVIEW_KIND\b/g, kind)
}

/** 셸 글롭을 앵커된 정규식으로 변환한다 (파일명 shape 검증용). */
function globToRegExp(glob) {
  const escaped = glob.replace(/[.+^${}()|[\]\\]/g, '\\$&')
  return new RegExp(`^${escaped.replace(/\*/g, '[^/]*').replace(/\?/g, '[^/]')}$`)
}

// 따옴표 span을 지운 뒤 판정한다 — `echo "… after codex exec (exit=…)"` 같은 **메시지 안의**
// `codex exec`를 호출로 오인해 에러 출력을 스텁으로 덮어쓰지 않기 위해서다.
const isCodexExecCall = (line) =>
  !/^\s*#/.test(line) && /(^|\s)codex exec\s/.test(stripQuotedSpans(line))

/**
 * `codex exec …` 호출 줄을 **전부** 스텁으로 치환한다. 블록은 `TIMEOUT_BIN` 유무로 갈리는
 * if/else 두 분기를 갖고, 실행 시 정확히 한 분기만 돈다 — 양쪽을 같은 스텁으로 바꿔야
 * 어느 환경에서도 스텁이 한 번 실행된다. 뒤따르는 `EXEC_EXIT=$?`가 종료 코드를 받는다.
 * 주석 줄(`# 2. codex exec 실행`)은 치환 대상이 아니다.
 */
function stubCodexExec(block, stub) {
  const lines = block.split('\n')
  assert.ok(lines.some(isCodexExecCall), '블록에서 `codex exec` 호출 줄을 찾지 못했다')
  return lines.map((line) => (isCodexExecCall(line) ? stub : line)).join('\n')
}

// 생성된 tmpdir. anti-vacuity 케이스가 실행 **후** 디스크 존재를 assert하므로 즉시 지울 수
// 없다. 전체 실행이 끝난 뒤 한 번에 정리한다.
const SCRATCH_DIRS = []

const scratchDir = () => {
  const dir = mkdtempSync(join(tmpdir(), 'codex-review-detection-'))
  SCRATCH_DIRS.push(dir)
  return dir
}

/** 스크립트 텍스트를 격리된 셸로 실행한다. rcfile·로케일 격리는 여기 한 곳에서 건다. */
function runScript(shell, script, dir = scratchDir()) {
  const { path: shellPath, args } = SHELLS[shell]
  assert.ok(shellPath, `${shell}이 resolve되지 않았다`)

  const scriptPath = join(dir, 'run.sh')
  writeFileSync(scriptPath, `${script}\n`)

  const env = { ...process.env, LC_ALL: 'C' }
  delete env.BASH_ENV
  delete env.ENV
  delete env.ZDOTDIR

  const result = spawnSync(shellPath, [...args, scriptPath], {
    encoding: 'utf8',
    env,
    timeout: 10_000,
  })
  return { status: result.status, stdout: result.stdout, stderr: result.stderr, dir }
}

/**
 * 블록을 격리된 tmpdir에서 지정 셸로 실행한다.
 * @param nestedCreates 스텁이 하위 디렉토리에도 리뷰 파일을 만들게 한다 (깊이 경계 통제).
 * @returns {{status, stdout, stderr, dir, newFilePath}}
 */
function runBlock(
  block,
  {
    shell,
    kind,
    seeds,
    creates,
    nestedCreates = null,
    execExit = 0,
    bindKind = true,
    bindCanon = true,
  },
) {
  const dir = scratchDir()
  const canonPath = join(dir, 'spec.md')
  writeFileSync(canonPath, '# spec\n')
  for (const [name, decision] of seeds) writeFileSync(join(dir, name), `- Decision: ${decision}\n`)

  const newFile = newFileFor(kind)
  const newFilePath = join(dir, newFile)
  const writeReview = (path, decision) => `printf '%s\\n' '- Decision: ${decision}' > "${path}"`
  const stubLines = creates === null ? ['true'] : [writeReview(`$REVIEW_DIR/${newFile}`, creates)]
  if (nestedCreates !== null) {
    stubLines.unshift(
      `mkdir -p "$REVIEW_DIR/${NESTED_DIR}"`,
      writeReview(`$REVIEW_DIR/${NESTED_DIR}/${newFile}`, nestedCreates),
    )
  }
  // 서브셸로 종료 코드만 설정한다 — 스크립트를 끝내지 않으면서 `EXEC_EXIT=$?`가 받는다.
  if (execExit !== 0) stubLines.push(`(exit ${execExit})`)

  // REVIEW_KIND는 스킬 Step 2가 바인딩하는 변수다. 여기서 주입해야 Parsing 블록의
  // `PATTERN` 파생이 두 phase 모두에서 검증된다. `bindKind: false`는 Step 2와 다른 셸
  // 호출로 이 블록을 실행한 상황을 재현한다 (셸 상태는 호출 간에 유지되지 않는다).
  const canonLine = bindCanon ? `CANON_PATH=${JSON.stringify(canonPath)}\n` : ''
  const kindLine = bindKind ? `REVIEW_KIND=${JSON.stringify(kind)}\n` : ''
  const preamble = `${canonLine}${kindLine}`
  const script = `${preamble}${stubCodexExec(block, stubLines.join('\n'))}`

  return { ...runScript(shell, script, dir), newFilePath }
}

// --- 케이스 정의 -------------------------------------------------------------
//
// C2의 새 파일 decision 텍스트는 seed와 다르다 — "새 파일을 골랐다"와 "아무 파일이나
// 골랐다"가 구분되지 않으면 어느 쪽이든 통과하는 공허한 assertion이 된다.

const casesFor = (kind) => {
  const readySeeds = seedFilesFor(kind).map((name) => [name, 'READY'])
  return {
    C1: { label: '기존 0개 → 새 파일 1개', seeds: [], creates: 'READY', expect: '- Decision: READY' },
    C2: {
      label: '기존 3개(READY) → 새 파일 1개(NOT READY)',
      seeds: readySeeds,
      creates: 'NOT READY',
      expect: '- Decision: NOT READY',
    },
    C3: { label: '새 파일 생성 없음', seeds: readySeeds, creates: null, expect: null },
  }
}

const NO_NEW_FILE_MESSAGE = 'No new review file found'

// --- 테스트 -----------------------------------------------------------------

after(() => {
  for (const dir of SCRATCH_DIRS) rmSync(dir, { recursive: true, force: true })
})

describe('셸 resolve', () => {
  test('zsh와 bash가 모두 resolve된다 (skip 아닌 실패)', () => {
    assert.ok(SHELLS.zsh.path, 'zsh을 resolve하지 못했다 — 매트릭스를 반쪽으로 실행하지 않는다')
    assert.ok(SHELLS.bash.path, 'bash를 resolve하지 못했다 — 매트릭스를 반쪽으로 실행하지 않는다')
  })
})

describe('스텁 파일명이 PATTERN에 매칭된다', () => {
  for (const kind of REVIEW_KINDS) {
    test(`${kind} — 새 파일·seed 파일명이 모두 블록의 PATTERN shape를 만족한다`, () => {
      const re = globToRegExp(patternValue(parsingBlock(read(CANON_SKILL)), kind))
      assert.match(newFileFor(kind), re)
      for (const name of seedFilesFor(kind)) assert.match(name, re)
    })
  }

  test('PATTERN이 한 phase로 하드코딩돼 있지 않다', () => {
    // 두 kind의 PATTERN이 같으면 블록이 한 phase 전용이라는 뜻이다. 이 어댑터는
    // spec-review·plan-review가 같은 블록을 공유하므로 kind마다 달라져야 한다.
    const block = parsingBlock(read(CANON_SKILL))
    const patterns = REVIEW_KINDS.map((kind) => patternValue(block, kind))
    assert.deepStrictEqual(patterns, ['spec-review-*.md', 'plan-review-*.md'])
  })
})

describe('수정된 블록: C1·C2·C3 × zsh·bash × spec-review·plan-review', () => {
  for (const kind of REVIEW_KINDS) {
    for (const shell of ['zsh', 'bash']) {
      for (const [id, testCase] of Object.entries(casesFor(kind))) {
        test(`${kind} / ${shell} / ${id} — ${testCase.label}`, () => {
          const block = parsingBlock(read(CANON_SKILL))
          const result = runBlock(block, {
            shell,
            kind,
            seeds: testCase.seeds,
            creates: testCase.creates,
          })

          if (testCase.expect === null) {
            assert.strictEqual(result.status, 1, `stderr: ${result.stderr}`)
            assert.match(result.stderr, new RegExp(NO_NEW_FILE_MESSAGE))
            return
          }
          assert.strictEqual(result.status, 0, `stderr: ${result.stderr}`)
          assert.strictEqual(result.stdout.trim(), testCase.expect)
        })
      }
    }
  }
})

describe('codex 호출 지점은 한 곳이다', () => {
  // 호출자는 `Invocation Pattern → Parsing the Decision` 순서로 두 절을 따르라고 지시한다.
  // 두 절이 각각 codex를 실행하면 리뷰 1회당 두 번 돌고 리뷰 파일도 2개 생긴다. 그런데
  // BEFORE 스냅샷이 Parsing 블록 안에서 찍히므로 `comm -13`은 여전히 1건을 돌려준다 —
  // 탐지 로직만으로는 이중 실행이 관측되지 않으므로 호출 지점 수를 직접 고정한다.
  test('자동 판정 플로우의 codex exec 호출은 Parsing 블록 안에만 있다', () => {
    // 제외는 **위치** 기준이다. 줄 내용으로 제외하면 정본 두 줄을 그대로 복사해 다른 절에
    // 되붙이는 회귀 — 이 게이트가 막아야 할 가장 자연스러운 형태 — 가 통과해 버린다.
    // `Isolation via DEV_CONTEXT_PATH`는 fixture dev-context로 수동 실험할 때 쓰는 예시이고
    // Execution Sequence에 들어 있지 않으므로 스코프에서 뺀다.
    const text = read(CANON_SKILL)
    const ranges = [PARSING_ANCHOR, ISOLATION_ANCHOR].map((anchor) => {
      const range = sectionRange(text, anchor)
      assert.ok(range, `${anchor} 절을 찾지 못했다`)
      return range
    })
    const inAllowedSection = (no) => ranges.some(({ start, end }) => no > start && no <= end)

    const callsOutside = allBashBlocks(text)
      .flatMap((block) => block.lines.map((line, i) => ({ line, no: block.startLine + i })))
      .filter(({ line, no }) => isCodexExecCall(line) && !inAllowedSection(no))

    assert.deepStrictEqual(callsOutside, [], `허용 절 밖 호출: ${JSON.stringify(callsOutside)}`)
  })

  test('Parsing 블록의 호출은 TIMEOUT_BIN 분기 2줄뿐이고 -s workspace-write를 유지한다', () => {
    const calls = parsingBlock(read(CANON_SKILL)).split('\n').filter(isCodexExecCall)

    // if/else 두 분기 — 실행 시 한쪽만 돈다.
    assert.strictEqual(calls.length, 2, JSON.stringify(calls))
    for (const call of calls) assert.match(call, /codex exec -s workspace-write /)
    assert.ok(
      calls.some((call) => /"\$TIMEOUT_BIN" 120 /.test(call)),
      'timeout 래퍼 분기가 없다',
    )
  })
})

describe('Step 2 phase 라우팅 블록 (REVIEW_KIND 생산자)', () => {
  // Parsing 블록(소비자)만 실행하고 생산자를 정적으로 두면, 이 토픽이 세운 원칙
  // ("문서 블록은 추출해 실제로 실행한다")이 새로 추가된 블록에 적용되지 않는다.
  const ROUTING = [
    { phase: 'spec', status: 'reviewing', expect: 'spec-review' },
    { phase: 'plan', status: 'reviewing', expect: 'plan-review' },
    { phase: 'impl', status: 'in-progress', expect: null },
    { phase: '', status: '', expect: null },
  ]

  for (const shell of ['zsh', 'bash']) {
    for (const { phase, status, expect } of ROUTING) {
      test(`${shell} — ${phase || '(빈값)'}:${status || '(빈값)'} → ${expect ?? '실행 불가'}`, () => {
        const block = phaseRoutingBlock(read(CANON_SKILL))
        const result = runScript(shell, [
          `PHASE=${JSON.stringify(phase)}`,
          `STATUS=${JSON.stringify(status)}`,
          block,
          'printf %s "$REVIEW_KIND"',
        ].join('\n'))

        if (expect === null) {
          // 표의 `기타` 행 — 조용히 빠져나가면 소비자가 원인과 무관한 메시지를 낸다.
          assert.notStrictEqual(result.status, 0, `stdout: ${result.stdout}`)
          assert.match(result.stderr, /adapter-codex-review를 실행할 수 없습니다/)
          return
        }
        assert.strictEqual(result.status, 0, `stderr: ${result.stderr}`)
        assert.strictEqual(result.stdout, expect)
      })
    }
  }
})

describe('선행 단계 미바인딩은 조용히 실패하지 않는다', () => {
  // Parsing 블록을 선행 절과 다른 Bash 호출로 실행하면 두 변수가 빈다. 가드가 없으면
  // PATTERN이 '-*.md'가 되거나 REVIEW_DIR가 '.'가 되어 find가 0건을 돌려주고
  // "No new review file found"로 끝나는데, 이는 이 토픽이 고치려던 버그와 증상·stderr가
  // 동일하다. 두 변수 모두 대칭으로 통제한다.
  const UNBOUND = [
    { label: 'REVIEW_KIND', opts: { bindKind: false }, expect: /REVIEW_KIND/ },
    { label: 'CANON_PATH', opts: { bindCanon: false }, expect: /CANON_PATH/ },
  ]

  for (const shell of ['zsh', 'bash']) {
    for (const { label, opts, expect } of UNBOUND) {
      test(`${shell} — unbound ${label}는 즉시 실패한다`, () => {
        const block = parsingBlock(read(CANON_SKILL))
        const result = runBlock(block, {
          shell,
          kind: 'spec-review',
          seeds: [],
          creates: 'READY',
          ...opts,
        })

        assert.notStrictEqual(result.status, 0, `stdout: ${result.stdout}`)
        assert.match(result.stderr, expect)
        assert.doesNotMatch(result.stderr, new RegExp(NO_NEW_FILE_MESSAGE))
      })
    }
  }
})

describe('실패한 codex exec는 판정으로 통과하지 않는다', () => {
  // Failure Handling 표는 `codex exec ... exits non-zero`에 manual fallback을 규정한다.
  // 가드가 없으면 실패한 실행이 남긴 부분 파일의 `- Decision:` 줄이 유효 판정으로 통과한다 —
  // 새 파일이 **존재하므로** "새 파일 없음" 가드로는 걸러지지 않는다.
  for (const shell of ['zsh', 'bash']) {
    test(`${shell} — 파일을 남기고 실패한 실행은 exit 1 + 판정 미출력`, () => {
      const block = parsingBlock(read(CANON_SKILL))
      const result = runBlock(block, {
        shell,
        kind: 'spec-review',
        seeds: [],
        creates: 'READY',
        execExit: 1,
      })

      assert.notStrictEqual(result.status, 0, `stdout: ${result.stdout}`)
      assert.doesNotMatch(result.stdout, /- Decision:/)
      assert.ok(
        existsSync(result.newFilePath),
        '스텁이 파일을 남기지 않았다 — 이 케이스가 "새 파일 없음" 가드와 구분되지 않는다',
      )
    })
  }
})

describe('탐지 깊이 경계: -maxdepth 1', () => {
  // `-maxdepth 1`이 없으면 find가 하위 디렉토리까지 훑는다. 리뷰 디렉토리 하위에 `fixture/`
  // 같은 서브디렉토리를 두는 토픽이 실재하므로 경계가 풀리면 중첩 파일이 탐지 대상이 된다.
  // `NESTED_DIR`가 새 파일보다 뒤로 정렬되므로 경계가 풀리면 `tail -1`이 중첩 파일을 집어
  // stdout이 달라진다.
  for (const shell of ['zsh', 'bash']) {
    test(`${shell} — 하위 디렉토리의 리뷰 파일은 선택되지 않는다`, () => {
      const block = parsingBlock(read(CANON_SKILL))
      const result = runBlock(block, {
        shell,
        kind: 'spec-review',
        seeds: [],
        creates: 'READY',
        nestedCreates: 'NOT READY',
      })

      assert.strictEqual(result.status, 0, `stderr: ${result.stderr}`)
      assert.strictEqual(result.stdout.trim(), '- Decision: READY')
    })
  }
})

describe('anti-vacuity: 수정 전 fixture 블록', () => {
  // 판별자 — zsh 실패 케이스에서 스텁이 만든 리뷰 파일이 실행 후에도 디스크에 존재함을
  // 함께 assert한다. 이것이 없으면 "새 파일이 없어서 올바르게 실패했다"(수정된 블록의 C3)와
  // "존재하는 파일을 못 봐서 실패했다"(수정 전 블록의 C1·C2)가 동일한 exit 1 + 동일한
  // stderr로 구분되지 않는다.
  // fixture는 수정 전 원문이라 `PATTERN='spec-review-*.md'`를 그대로 담는다 — `REVIEW_KIND`
  // 파생 이전 상태다. 따라서 kind는 spec-review 하나로 고정한다.
  const FIXTURE_KIND = 'spec-review'
  const fixtureCases = casesFor(FIXTURE_KIND)

  for (const id of ['C1', 'C2']) {
    const testCase = fixtureCases[id]
    const runFixture = (shell) =>
      runBlock(parsingBlock(read(PRE_FIX_FIXTURE)), {
        shell,
        kind: FIXTURE_KIND,
        seeds: testCase.seeds,
        creates: testCase.creates,
      })

    test(`zsh / ${id} — 버그를 재현한다 (exit 1 + 파일은 디스크에 존재)`, () => {
      const result = runFixture('zsh')

      assert.strictEqual(result.status, 1, `stdout: ${result.stdout}`)
      assert.match(result.stderr, new RegExp(NO_NEW_FILE_MESSAGE))
      assert.ok(
        existsSync(result.newFilePath),
        '스텁이 만든 리뷰 파일이 디스크에 없다 — 정상 실패(C3)와 구분되지 않는다',
      )
    })

    test(`bash / ${id} — 원래 동작대로 통과한다`, () => {
      const result = runFixture('bash')

      assert.strictEqual(result.status, 0, `stderr: ${result.stderr}`)
      assert.strictEqual(result.stdout.trim(), testCase.expect)
    })
  }
})

describe('변수-글롭 전수 스캔', () => {
  test('template 스킬 문서 전체에서 위반 0건', () => {
    const files = globSync(SKILL_GLOB).sort()
    assert.ok(files.length > 0, `수집된 SKILL.md가 0건 — glob이 매칭에 실패했다: ${SKILL_GLOB}`)

    // 검사 표면이 0이면 "위반 0건"과 "아무것도 검사하지 않았다"가 구분되지 않는다. 파싱된
    // 블록 수가 아니라 **G가 비지 않아 stage 3까지 도달한 블록 수**를 센다 — 파싱 수는
    // 대부분의 블록이 stage 2에서 단락되는 사실을 가려 실제보다 넓은 커버리지를 주장한다.
    let blockCount = 0
    let scanned = 0
    const found = []
    for (const file of files) {
      const text = read(file)
      blockCount += allBashBlocks(text).length
      scanned += scannedBlockCount(text)
      for (const violation of detectViolations(text)) found.push({ file, ...violation })
    }

    assert.ok(blockCount > 0, '수집된 bash 블록이 0건 — glob이 매칭에 실패했다')
    assert.ok(scanned > 0, '글롭-값 변수를 가진 bash 블록이 0건 — 검사 표면이 비었다')
    assert.deepStrictEqual(
      found,
      [],
      `글롭 값을 담은 변수의 unquoted 확장: ${JSON.stringify(found, null, 2)}`,
    )
  })

  test('anti-vacuity — 수정 전 fixture에서 정확히 2건을 잡는다', () => {
    // 합성 `$VAR*` 케이스가 아니라 실제 `ls "$REVIEW_DIR"/$PATTERN` 두 줄로 탐지기를 통제한다.
    const text = read(PRE_FIX_FIXTURE)
    const violations = detectViolations(text)

    assert.strictEqual(violations.length, 2, JSON.stringify(violations))
    const lines = text.split('\n')
    const targets = violations.map((v) => lines[v.line - 1])
    assert.match(targets[0], /^BEFORE_FILES=/)
    assert.match(targets[1], /^AFTER_FILES=/)
    for (const violation of violations) assert.strictEqual(violation.varName, 'PATTERN')
  })

  test('과탐 통제 — set -u 빈 배열 패턴은 위반이 아니다', () => {
    // `${arr[@]+"${arr[@]}"}`는 글롭-값 대입을 갖지 않으므로 stage 2에서 단락된다. 이 통제가
    // 고정하는 것은 **stage 2의 폭**이다 — 대입 인식이 `[`를 담은 확장까지 G에 넣도록
    // 넓어지면 red가 된다. stage 3(`$VAR` 매처)의 폭은 이 파일이 stage 3에 도달하지 않으므로
    // 고정하지 않는다.
    const text = read(NEGATIVE_CONTROL_SKILL)
    assert.ok(allBashBlocks(text).length > 0, '통제 대상 파일에 bash 블록이 없다')
    assert.strictEqual(scannedBlockCount(text), 0)
    assert.deepStrictEqual(detectViolations(text), [])
  })

  test('quoted span 제거는 줄 단위다 — 미종결 따옴표가 뒤 줄을 삼키지 않는다', () => {
    // plan이 명시한 결정이지만 실제 코퍼스의 G-블록에는 미종결 따옴표 줄이 없어, 이 통제가
    // 없으면 블록 단위 제거로 바꿔도 전수 스캔이 green으로 남는다.
    const markdown = [
      '```bash',
      "PATTERN='*.md'",
      'echo "미종결 따옴표가 여기서 시작한다',
      'ls "$DIR"/$PATTERN',
      '```',
    ].join('\n')

    const violations = detectViolations(markdown)
    assert.deepStrictEqual(violations, [{ line: 4, varName: 'PATTERN' }])
  })
})
