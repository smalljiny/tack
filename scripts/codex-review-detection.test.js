// adapter-codex-review의 새 리뷰 파일 탐지 회귀 테스트.
//
// `## Parsing the Decision` 절의 bash 코드 펜스 블록을 문서에서 **추출해 실제로 실행**한다.
// 정적 grep이 아니라 실행이어야 하는 이유는 이번 버그가 문법이 아니라 셸 의미론이기
// 때문이다 — zsh는 변수 치환 결과를 글롭 확장하지 않아 `ls "$DIR"/$PATTERN`이 리터럴
// 파일명을 찾고 실패한다. bash에서는 같은 줄이 정상 동작하므로 두 셸 매트릭스가 필수다.
//
// 실행: node --test scripts/codex-review-detection.test.js
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
import { readFileSync, writeFileSync, mkdtempSync, existsSync, rmSync } from 'node:fs'
import { spawnSync } from 'node:child_process'
import { tmpdir } from 'node:os'
import { join } from 'node:path'

const REPO_ROOT = `${import.meta.dirname}/..`
const FIXTURE_DIR = `${import.meta.dirname}/fixtures/codex-review-detection`

const CANON_SKILL = `${REPO_ROOT}/template/.claude/skills/adapter-codex-review/SKILL.md`
const PRE_FIX_FIXTURE = `${FIXTURE_DIR}/pre-fix-section.md`

const PARSING_ANCHOR = /^#{1,6}\s+Parsing the Decision\s*$/

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
  const lines = text.split('\n')
  const open = lines.findIndex((line) => /^\s*```bash\s*$/.test(line))
  if (open === -1) return null
  const close = lines.findIndex((line, i) => i > open && /^\s*```\s*$/.test(line))
  if (close === -1) return null
  return lines.slice(open + 1, close).join('\n')
}

/** `## Parsing the Decision` 절의 첫 bash 블록을 꺼낸다. */
function parsingBlock(markdown) {
  const section = sectionUnderHeading(markdown, PARSING_ANCHOR)
  assert.ok(section, '`## Parsing the Decision` 절을 찾지 못했다')
  const block = firstBashBlock(section)
  assert.ok(block, '`## Parsing the Decision` 절에 bash 코드 펜스 블록이 없다')
  return block
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

const NEW_FILE = 'spec-review-260729120000.md'

// seed 세 번째는 `NEW_FILE`보다 **뒤로** 정렬된다 (LC_ALL=C). 이 seed가 없으면 `comm -13`을
// 통째로 없애고 `tail -1` of AFTER만 써도 C2가 통과해, 케이스가 diff 의미론을 고정하지 못한다.
const SEED_FILES = [
  'spec-review-260101000000.md',
  'spec-review-260102000000.md',
  'spec-review-269999999999.md',
]

// `NEW_FILE`보다 뒤로 정렬되는 하위 디렉토리 이름. `-maxdepth 1`이 풀리면 `tail -1`이 이쪽
// 파일을 집으므로 깊이 경계가 관측된다.
const NESTED_DIR = 'zz-nested'

/** 코드 블록의 `PATTERN='…'` 대입값. */
function patternValue(block) {
  const value = block.match(/^PATTERN='([^']*)'/m)?.[1]
  assert.ok(value, '블록에서 `PATTERN=` 대입을 찾지 못했다')
  return value
}

/** 셸 글롭을 앵커된 정규식으로 변환한다 (파일명 shape 검증용). */
function globToRegExp(glob) {
  const escaped = glob.replace(/[.+^${}()|[\]\\]/g, '\\$&')
  return new RegExp(`^${escaped.replace(/\*/g, '[^/]*').replace(/\?/g, '[^/]')}$`)
}

/**
 * `codex exec …` 호출 한 줄만 스텁으로 치환한다.
 * 뒤따르는 `EXEC_EXIT=$?`가 스텁의 종료 코드를 그대로 받는다.
 * 주석 줄(`# 2. codex exec 실행`)은 치환 대상이 아니다.
 */
function stubCodexExec(block, stub) {
  const lines = block.split('\n')
  const idx = lines.findIndex((line) => /^\s*codex exec\s/.test(line))
  assert.notStrictEqual(idx, -1, '블록에서 `codex exec` 호출 줄을 찾지 못했다')
  return [...lines.slice(0, idx), stub, ...lines.slice(idx + 1)].join('\n')
}

// 생성된 tmpdir. anti-vacuity 케이스가 실행 **후** 디스크 존재를 assert하므로 즉시 지울 수
// 없다. 전체 실행이 끝난 뒤 한 번에 정리한다.
const SCRATCH_DIRS = []

/**
 * 블록을 격리된 tmpdir에서 지정 셸로 실행한다.
 * @param nestedCreates 스텁이 하위 디렉토리에도 리뷰 파일을 만들게 한다 (깊이 경계 통제).
 * @returns {{status, stdout, stderr, dir, newFilePath}}
 */
function runBlock(block, { shell, seeds, creates, nestedCreates = null }) {
  const { path: shellPath, args } = SHELLS[shell]
  assert.ok(shellPath, `${shell}이 resolve되지 않았다`)

  const dir = mkdtempSync(join(tmpdir(), 'codex-review-detection-'))
  SCRATCH_DIRS.push(dir)
  const canonPath = join(dir, 'spec.md')
  writeFileSync(canonPath, '# spec\n')
  for (const [name, decision] of seeds) writeFileSync(join(dir, name), `- Decision: ${decision}\n`)

  const newFilePath = join(dir, NEW_FILE)
  const writeReview = (path, decision) => `printf '%s\\n' '- Decision: ${decision}' > "${path}"`
  const stubLines =
    creates === null ? ['true'] : [writeReview(`$REVIEW_DIR/${NEW_FILE}`, creates)]
  if (nestedCreates !== null) {
    stubLines.unshift(
      `mkdir -p "$REVIEW_DIR/${NESTED_DIR}"`,
      writeReview(`$REVIEW_DIR/${NESTED_DIR}/${NEW_FILE}`, nestedCreates),
    )
  }

  const script = `CANON_PATH=${JSON.stringify(canonPath)}\n${stubCodexExec(block, stubLines.join('\n'))}\n`
  const scriptPath = join(dir, 'run.sh')
  writeFileSync(scriptPath, script)

  const env = { ...process.env, LC_ALL: 'C' }
  delete env.BASH_ENV
  delete env.ENV
  delete env.ZDOTDIR

  const result = spawnSync(shellPath, [...args, scriptPath], {
    encoding: 'utf8',
    env,
    timeout: 10_000,
  })
  return { status: result.status, stdout: result.stdout, stderr: result.stderr, dir, newFilePath }
}

// --- 케이스 정의 -------------------------------------------------------------
//
// C2의 새 파일 decision 텍스트는 seed와 다르다 — "새 파일을 골랐다"와 "아무 파일이나
// 골랐다"가 구분되지 않으면 어느 쪽이든 통과하는 공허한 assertion이 된다.

const READY_SEEDS = SEED_FILES.map((name) => [name, 'READY'])

const CASES = {
  C1: { label: '기존 0개 → 새 파일 1개', seeds: [], creates: 'READY', expect: '- Decision: READY' },
  C2: {
    label: '기존 3개(READY) → 새 파일 1개(NOT READY)',
    seeds: READY_SEEDS,
    creates: 'NOT READY',
    expect: '- Decision: NOT READY',
  },
  C3: { label: '새 파일 생성 없음', seeds: READY_SEEDS, creates: null, expect: null },
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
  test('새 파일·seed 파일명이 모두 블록의 PATTERN shape를 만족한다', () => {
    const re = globToRegExp(patternValue(parsingBlock(read(CANON_SKILL))))
    assert.match(NEW_FILE, re)
    for (const name of SEED_FILES) assert.match(name, re)
  })
})

describe('수정된 블록: C1·C2·C3 × zsh·bash', () => {
  for (const shell of ['zsh', 'bash']) {
    for (const [id, testCase] of Object.entries(CASES)) {
      test(`${shell} / ${id} — ${testCase.label}`, () => {
        const block = parsingBlock(read(CANON_SKILL))
        const result = runBlock(block, { shell, seeds: testCase.seeds, creates: testCase.creates })

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
})

describe('탐지 깊이 경계: -maxdepth 1', () => {
  // `-maxdepth 1`이 없으면 find가 하위 디렉토리까지 훑는다. 리뷰 디렉토리 하위에 `fixture/`
  // 같은 서브디렉토리를 두는 토픽이 실재하므로 경계가 풀리면 중첩 파일이 탐지 대상이 된다.
  // `NESTED_DIR`가 `NEW_FILE`보다 뒤로 정렬되므로 경계가 풀리면 `tail -1`이 중첩 파일을 집어
  // stdout이 달라진다.
  for (const shell of ['zsh', 'bash']) {
    test(`${shell} — 하위 디렉토리의 리뷰 파일은 선택되지 않는다`, () => {
      const block = parsingBlock(read(CANON_SKILL))
      const result = runBlock(block, {
        shell,
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
  for (const id of ['C1', 'C2']) {
    const testCase = CASES[id]

    test(`zsh / ${id} — 버그를 재현한다 (exit 1 + 파일은 디스크에 존재)`, () => {
      const block = parsingBlock(read(PRE_FIX_FIXTURE))
      const result = runBlock(block, { shell: 'zsh', seeds: testCase.seeds, creates: testCase.creates })

      assert.strictEqual(result.status, 1, `stdout: ${result.stdout}`)
      assert.match(result.stderr, new RegExp(NO_NEW_FILE_MESSAGE))
      assert.ok(
        existsSync(result.newFilePath),
        '스텁이 만든 리뷰 파일이 디스크에 없다 — 정상 실패(C3)와 구분되지 않는다',
      )
    })

    test(`bash / ${id} — 원래 동작대로 통과한다`, () => {
      const block = parsingBlock(read(PRE_FIX_FIXTURE))
      const result = runBlock(block, { shell: 'bash', seeds: testCase.seeds, creates: testCase.creates })

      assert.strictEqual(result.status, 0, `stderr: ${result.stderr}`)
      assert.strictEqual(result.stdout.trim(), testCase.expect)
    })
  }
})
