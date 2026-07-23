// dev-context.test.js — node:test + node:assert 기반 통합 테스트
// 실제 dev-context.json을 건드리지 않도록 임시 파일을 사용한다.
import { test, describe, beforeEach, afterEach } from 'node:test'
import assert from 'node:assert/strict'
import { execFileSync, execFile } from 'node:child_process'
import { readFileSync, writeFileSync, unlinkSync, existsSync, rmSync } from 'node:fs'
import { join, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'
import { promisify } from 'node:util'
import { tmpdir } from 'node:os'

const execFileAsync = promisify(execFile)
const __dirname = dirname(fileURLToPath(import.meta.url))
const SCRIPT = join(__dirname, 'dev-context.js')

// 각 테스트가 독립된 임시 파일을 사용한다.
let CTX_PATH = null

function run(...args) {
  return execFileSync('node', [SCRIPT, ...args], {
    encoding: 'utf8',
    env: { ...process.env, DEV_CONTEXT_PATH: CTX_PATH },
  }).trim()
}

async function runExpectFail(...args) {
  try {
    await execFileAsync('node', [SCRIPT, ...args], {
      encoding: 'utf8',
      env: { ...process.env, DEV_CONTEXT_PATH: CTX_PATH },
    })
    throw new Error('프로세스가 성공했으나 실패 예상')
  } catch (err) {
    if (err.message === '프로세스가 성공했으나 실패 예상') throw err
    return err
  }
}

function readCtx() {
  return JSON.parse(readFileSync(CTX_PATH, 'utf8'))
}

function removeCtx() {
  if (existsSync(CTX_PATH)) unlinkSync(CTX_PATH)
}

// --- 테스트 ---

describe('dev-context.js', () => {
  beforeEach(() => {
    // 각 테스트 전 독립된 임시 파일 경로 생성 (파일은 생성 안 함)
    CTX_PATH = join(tmpdir(), `dev-context-test-${Date.now()}-${Math.random().toString(36).slice(2)}.json`)
  })
  afterEach(() => {
    // 임시 파일 정리
    if (CTX_PATH && existsSync(CTX_PATH)) unlinkSync(CTX_PATH)
    CTX_PATH = null
  })

  describe('register-topic', () => {
    test('정상 등록: spec:drafting 상태로 생성됨', () => {
      run('register-topic', '--topic=test-topic', '--spec=.tack/local/backlog/test-topic/spec.md')
      const ctx = readCtx()
      assert.equal(ctx.current_topic, 'test-topic')
      assert.equal(ctx.topics['test-topic'].phase, 'spec')
      assert.equal(ctx.topics['test-topic'].status, 'drafting')
      assert.equal(ctx.topics['test-topic'].spec, '.tack/local/backlog/test-topic/spec.md')
    })

    test('레거시 필드(current_spec, specConfirmed, planConfirmed) 자동 제거', () => {
      // 레거시 필드가 있는 구조 세팅
      writeFileSync(CTX_PATH, JSON.stringify({
        current_topic: null,
        current_spec: 'old/path',
        specConfirmed: true,
        planConfirmed: false,
        topics: {},
        updatedAt: new Date().toISOString(),
      }), 'utf8')
      run('register-topic', '--topic=legacy-test', '--spec=some/spec.md')
      const ctx = readCtx()
      assert.equal(ctx.current_spec, undefined)
      assert.equal(ctx.specConfirmed, undefined)
      assert.equal(ctx.planConfirmed, undefined)
    })

    test('topics 없는 legacy current_spec 파일에서도 등록 성공', () => {
      writeFileSync(CTX_PATH, JSON.stringify({
        current_spec: '.tack/local/backlog/legacy/spec.md',
        updatedAt: new Date().toISOString(),
      }), 'utf8')
      run('register-topic', '--topic=legacy-only', '--spec=.tack/local/backlog/legacy-only/spec.md')
      const ctx = readCtx()
      assert.equal(ctx.current_spec, undefined)
      assert.equal(ctx.current_topic, 'legacy-only')
      assert.equal(ctx.topics['legacy-only'].phase, 'spec')
      assert.equal(ctx.topics['legacy-only'].status, 'drafting')
    })

    test('파일 없을 때 자동 생성', () => {
      removeCtx()
      assert.equal(existsSync(CTX_PATH), false)
      run('register-topic', '--topic=new-topic', '--spec=some/spec.md')
      assert.equal(existsSync(CTX_PATH), true)
      const ctx = readCtx()
      assert.equal(ctx.topics['new-topic'].phase, 'spec')
    })

    test('이미 존재하는 토픽에 재등록 시도 → non-zero exit', async () => {
      run('register-topic', '--topic=dup-topic', '--spec=some/spec.md')
      const err = await runExpectFail('register-topic', '--topic=dup-topic', '--spec=other/spec.md')
      assert.notEqual(err.code, 0)
      assert.ok(err.stderr.includes('이미 존재합니다'))
    })

    test('부모 디렉토리 없는 중첩 경로에서도 파일 생성', () => {
      const topDir = join(tmpdir(), `nested-dc-${Date.now()}`)
      const nestedPath = join(topDir, 'deep', 'path', 'dev-context.json')
      try {
        execFileSync('node', [SCRIPT, 'register-topic', '--topic=nested-test', '--spec=spec.md'], {
          encoding: 'utf8',
          env: { ...process.env, DEV_CONTEXT_PATH: nestedPath },
        })
        assert.ok(existsSync(nestedPath), '중첩 경로에 파일이 생성되어야 함')
        const ctx = JSON.parse(readFileSync(nestedPath, 'utf8'))
        assert.equal(ctx.topics['nested-test'].phase, 'spec')
      } finally {
        rmSync(topDir, { recursive: true, force: true })
      }
    })
  })

  describe('update-state', () => {
    beforeEach(() => {
      run('register-topic', '--topic=t1', '--spec=some/spec.md')
    })

    test('유효 전환: spec:drafting → spec:reviewing 성공', () => {
      run('update-state', '--topic=t1', '--phase=spec', '--status=reviewing')
      const ctx = readCtx()
      assert.equal(ctx.topics['t1'].phase, 'spec')
      assert.equal(ctx.topics['t1'].status, 'reviewing')
    })

    test('유효 전환 체인: 전체 라이프사이클 순서 통과', () => {
      run('update-state', '--topic=t1', '--phase=spec', '--status=reviewing')
      run('update-state', '--topic=t1', '--phase=spec', '--status=confirmed')
      run('update-state', '--topic=t1', '--phase=plan', '--status=ready')
      run('update-state', '--topic=t1', '--phase=plan', '--status=reviewing')
      run('update-state', '--topic=t1', '--phase=plan', '--status=confirmed')
      run('update-state', '--topic=t1', '--phase=impl', '--status=in-progress')
      run('update-state', '--topic=t1', '--phase=review', '--status=in-progress')
      const ctx = readCtx()
      assert.equal(ctx.topics['t1'].phase, 'review')
      assert.equal(ctx.topics['t1'].status, 'in-progress')
    })

    test('무효 전환: spec:drafting → plan:ready는 non-zero exit', async () => {
      const err = await runExpectFail('update-state', '--topic=t1', '--phase=plan', '--status=ready')
      assert.notEqual(err.code, 0)
      assert.ok(err.stderr.includes('유효하지 않은 전환'))
    })

    test('무효 전환: spec:drafting → review:in-progress는 non-zero exit', async () => {
      const err = await runExpectFail('update-state', '--topic=t1', '--phase=review', '--status=in-progress')
      assert.notEqual(err.code, 0)
    })

    test('역방향 전환: spec:confirmed → spec:drafting은 허용 안 됨', async () => {
      run('update-state', '--topic=t1', '--phase=spec', '--status=reviewing')
      run('update-state', '--topic=t1', '--phase=spec', '--status=confirmed')
      const err = await runExpectFail('update-state', '--topic=t1', '--phase=spec', '--status=drafting')
      assert.notEqual(err.code, 0)
    })

    test('plan:reviewing → plan:ready 롤백 허용', () => {
      run('update-state', '--topic=t1', '--phase=spec', '--status=reviewing')
      run('update-state', '--topic=t1', '--phase=spec', '--status=confirmed')
      run('update-state', '--topic=t1', '--phase=plan', '--status=ready')
      run('update-state', '--topic=t1', '--phase=plan', '--status=reviewing')
      run('update-state', '--topic=t1', '--phase=plan', '--status=ready') // 롤백
      const ctx = readCtx()
      assert.equal(ctx.topics['t1'].phase, 'plan')
      assert.equal(ctx.topics['t1'].status, 'ready')
    })

    test('review:in-progress → impl:in-progress 롤백 허용 (리뷰 실패)', () => {
      run('update-state', '--topic=t1', '--phase=spec', '--status=reviewing')
      run('update-state', '--topic=t1', '--phase=spec', '--status=confirmed')
      run('update-state', '--topic=t1', '--phase=plan', '--status=ready')
      run('update-state', '--topic=t1', '--phase=plan', '--status=reviewing')
      run('update-state', '--topic=t1', '--phase=plan', '--status=confirmed')
      run('update-state', '--topic=t1', '--phase=impl', '--status=in-progress')
      run('update-state', '--topic=t1', '--phase=review', '--status=in-progress')
      run('update-state', '--topic=t1', '--phase=impl', '--status=in-progress') // 롤백
      const ctx = readCtx()
      assert.equal(ctx.topics['t1'].phase, 'impl')
      assert.equal(ctx.topics['t1'].status, 'in-progress')
    })

    test('동일 상태 전환은 no-op (idempotent)', () => {
      run('update-state', '--topic=t1', '--phase=spec', '--status=drafting') // 동일 상태
      const ctx = readCtx()
      assert.equal(ctx.topics['t1'].phase, 'spec')
      assert.equal(ctx.topics['t1'].status, 'drafting')
    })
  })

  describe('set-field', () => {
    beforeEach(() => {
      run('register-topic', '--topic=sf-test', '--spec=some/spec.md')
    })

    test('일반 필드 업데이트 성공', () => {
      run('set-field', '--topic=sf-test', '--field=specReview', '--value=.tack/local/backlog/sf-test/spec-review-001.md')
      const ctx = readCtx()
      assert.equal(ctx.topics['sf-test'].specReview, '.tack/local/backlog/sf-test/spec-review-001.md')
    })

    test('currentStory null 설정', () => {
      run('set-field', '--topic=sf-test', '--field=currentStory', '--value=Story3')
      run('set-field', '--topic=sf-test', '--field=currentStory', '--value=null')
      const ctx = readCtx()
      assert.equal(ctx.topics['sf-test'].currentStory, null)
    })

    test('phase 변경 시도 → 에러 (PROTECTED)', async () => {
      const err = await runExpectFail('set-field', '--topic=sf-test', '--field=phase', '--value=plan')
      assert.notEqual(err.code, 0)
      assert.ok(err.stderr.includes('update-state 전용'))
    })

    test('status 변경 시도 → 에러 (PROTECTED)', async () => {
      const err = await runExpectFail('set-field', '--topic=sf-test', '--field=status', '--value=confirmed')
      assert.notEqual(err.code, 0)
      assert.ok(err.stderr.includes('update-state 전용'))
    })

    test('current_topic 글로벌 필드 업데이트 (--topic 없이)', () => {
      run('register-topic', '--topic=other-topic', '--spec=other/spec.md')
      run('set-field', '--field=current_topic', '--value=sf-test')
      const ctx = readCtx()
      assert.equal(ctx.current_topic, 'sf-test')
    })

    test('current_topic null 설정', () => {
      run('set-field', '--field=current_topic', '--value=null')
      const ctx = readCtx()
      assert.equal(ctx.current_topic, null)
    })

    test('set-field --topic=X --field=current_topic → 에러', async () => {
      const err = await runExpectFail('set-field', '--topic=sf-test', '--field=current_topic', '--value=sf-test')
      assert.notEqual(err.code, 0)
      assert.ok(err.stderr.includes('--topic과 함께 사용할 수 없습니다'))
    })
  })

  describe('currentTask → currentStory 마이그레이션', () => {
    test('기존 currentTask 필드만 있으면 currentStory로 자동 마이그레이션 + currentTask 제거', () => {
      // 레거시 파일: currentTask만 존재
      writeFileSync(CTX_PATH, JSON.stringify({
        current_topic: 'legacy',
        topics: {
          legacy: {
            phase: 'impl',
            status: 'in-progress',
            spec: '.tack/local/active/legacy/spec.md',
            specReview: null,
            plan: '.tack/local/active/legacy/implementation-plan.md',
            planReview: null,
            currentTask: 'Task5',
            createdAt: new Date().toISOString(),
            updatedAt: new Date().toISOString(),
          },
        },
        updatedAt: new Date().toISOString(),
      }), 'utf8')

      // 어떤 쓰기 작업이든 readContext → writeContext 경로를 통과시키면 마이그레이션이 영속화된다
      run('set-field', '--topic=legacy', '--field=planReview', '--value=.tack/local/active/legacy/plan-review-001.md')
      const ctx = readCtx()
      assert.equal(ctx.topics.legacy.currentStory, 'Task5')
      assert.equal(Object.hasOwn(ctx.topics.legacy, 'currentTask'), false)
    })

    test('currentStory 이미 존재하면 마이그레이션 no-op (currentTask 보존)', () => {
      // 두 필드 모두 존재 — 마이그레이션 불가 케이스
      writeFileSync(CTX_PATH, JSON.stringify({
        current_topic: 'both',
        topics: {
          both: {
            phase: 'impl',
            status: 'in-progress',
            spec: '.tack/local/active/both/spec.md',
            specReview: null,
            plan: '.tack/local/active/both/implementation-plan.md',
            planReview: null,
            currentTask: 'OldT',
            currentStory: 'NewS',
            createdAt: new Date().toISOString(),
            updatedAt: new Date().toISOString(),
          },
        },
        updatedAt: new Date().toISOString(),
      }), 'utf8')

      run('set-field', '--topic=both', '--field=planReview', '--value=.tack/local/active/both/plan-review-001.md')
      const ctx = readCtx()
      // currentStory는 그대로, currentTask는 보존 (덮어쓰지 않음)
      assert.equal(ctx.topics.both.currentStory, 'NewS')
      assert.equal(ctx.topics.both.currentTask, 'OldT')
    })

    test('register-topic 초기화 시 currentStory: null 필드 생성, currentTask 키 부재', () => {
      run('register-topic', '--topic=fresh', '--spec=.tack/local/backlog/fresh/spec.md')
      const ctx = readCtx()
      assert.equal(ctx.topics.fresh.currentStory, null)
      assert.equal(Object.hasOwn(ctx.topics.fresh, 'currentTask'), false)
    })
  })

  describe('read', () => {
    beforeEach(() => {
      run('register-topic', '--topic=read-test', '--spec=.tack/local/backlog/read-test/spec.md')
    })

    test('read --topic=read-test --field=phase → "spec" 출력', () => {
      const out = run('read', '--topic=read-test', '--field=phase')
      assert.equal(out, 'spec')
    })

    test('read --topic=read-test --field=status → "drafting" 출력', () => {
      const out = run('read', '--topic=read-test', '--field=status')
      assert.equal(out, 'drafting')
    })

    test('read --field=current_topic → topic 이름 출력', () => {
      const out = run('read', '--field=current_topic')
      assert.equal(out, 'read-test')
    })

    test('read --topic=read-test --field=spec → spec 경로 출력', () => {
      const out = run('read', '--topic=read-test', '--field=spec')
      assert.equal(out, '.tack/local/backlog/read-test/spec.md')
    })

    test('존재하지 않는 토픽 읽기 → non-zero exit', async () => {
      const err = await runExpectFail('read', '--topic=nonexistent', '--field=phase')
      assert.notEqual(err.code, 0)
    })

    test('read --topic=X --field=current_topic → --topic과 함께 사용 불가 에러', async () => {
      const err = await runExpectFail('read', '--topic=read-test', '--field=current_topic')
      assert.notEqual(err.code, 0)
      assert.ok(err.stderr.includes('--topic과 함께 사용할 수 없습니다'))
    })

    test('read --field 미지정 → 사용법 안내를 stderr에 출력하고 non-zero exit', async () => {
      const err = await runExpectFail('read')
      assert.notEqual(err.code, 0)
      assert.ok(err.stderr.includes('--field'), 'stderr는 --field 키워드를 포함해야 한다')
      assert.ok(err.stderr.includes('사용 가능한 호출 형태'), 'stderr는 사용법 안내 헤더를 포함해야 한다')
    })
  })

  describe('config path (dot notation)', () => {
    // 1. read --field=config.dev_impl.auto_start (no --topic) — returns stored value on a line; empty line when unset.
    test('read config 점 경로: 설정된 값이 한 줄로 출력', () => {
      run('set-field', '--field=config.dev_impl.auto_start', '--value=true')
      const out = run('read', '--field=config.dev_impl.auto_start')
      assert.equal(out, 'true')
    })

    test('read config 점 경로: 미설정 시 빈 출력 (exit 0)', () => {
      // 파일도 없는 상태에서 read → 빈 줄 출력 (exit 0)
      const out = run('read', '--field=config.dev_impl.auto_start')
      assert.equal(out, '')
    })

    // 2. read --topic=<X> --field=config.dev_impl.auto_start — non-zero exit (config.* is global).
    test('read config 점 경로 + --topic → non-zero exit', async () => {
      run('register-topic', '--topic=cp-test', '--spec=some/spec.md')
      const err = await runExpectFail('read', '--topic=cp-test', '--field=config.dev_impl.auto_start')
      assert.notEqual(err.code, 0)
    })

    // 3. read with missing segment (config, config.dev_impl, or leaf) — empty output, exit 0.
    test('read config: config 키 자체 없으면 빈 줄 (exit 0)', () => {
      // 파일에 config 키가 없는 상태
      writeFileSync(CTX_PATH, JSON.stringify({
        current_topic: null,
        topics: {},
        updatedAt: new Date().toISOString(),
      }), 'utf8')
      const out = run('read', '--field=config.dev_impl.auto_start')
      assert.equal(out, '')
    })

    test('read config: 네임스페이스 없으면 빈 줄', () => {
      writeFileSync(CTX_PATH, JSON.stringify({
        current_topic: null,
        topics: {},
        config: {},
        updatedAt: new Date().toISOString(),
      }), 'utf8')
      const out = run('read', '--field=config.dev_impl.auto_start')
      assert.equal(out, '')
    })

    test('read config: leaf 키 없으면 빈 줄', () => {
      writeFileSync(CTX_PATH, JSON.stringify({
        current_topic: null,
        topics: {},
        config: { dev_impl: {} },
        updatedAt: new Date().toISOString(),
      }), 'utf8')
      const out = run('read', '--field=config.dev_impl.auto_start')
      assert.equal(out, '')
    })

    // 4. set-field config.dev_impl.auto_start = true → JSON boolean true
    test('set-field config: --value=true → JSON boolean true 저장', () => {
      run('set-field', '--field=config.dev_impl.auto_start', '--value=true')
      const ctx = readCtx()
      assert.equal(ctx.config.dev_impl.auto_start, true)
      assert.equal(typeof ctx.config.dev_impl.auto_start, 'boolean')
    })

    // 5. set-field config.dev_impl.auto_start = false → JSON boolean false
    test('set-field config: --value=false → JSON boolean false 저장', () => {
      run('set-field', '--field=config.dev_impl.auto_start', '--value=false')
      const ctx = readCtx()
      assert.equal(ctx.config.dev_impl.auto_start, false)
      assert.equal(typeof ctx.config.dev_impl.auto_start, 'boolean')
    })

    // 6. set-field config.some.count = 42 → JSON number 42
    test('set-field config: 정수 리터럴 → JSON number 저장', () => {
      run('set-field', '--field=config.some.count', '--value=42')
      const ctx = readCtx()
      assert.equal(ctx.config.some.count, 42)
      assert.equal(typeof ctx.config.some.count, 'number')
    })

    test('set-field config: 음의 정수 리터럴 → JSON number 저장', () => {
      run('set-field', '--field=config.some.count', '--value=-7')
      const ctx = readCtx()
      assert.equal(ctx.config.some.count, -7)
      assert.equal(typeof ctx.config.some.count, 'number')
    })

    // 7. set-field config.some.label = foo → JSON string "foo"
    test('set-field config: 일반 문자열 → JSON string 저장', () => {
      run('set-field', '--field=config.some.label', '--value=foo')
      const ctx = readCtx()
      assert.equal(ctx.config.some.label, 'foo')
      assert.equal(typeof ctx.config.some.label, 'string')
    })

    // 8. set-field auto-creates missing intermediate objects
    test('set-field config: 누락된 중간 객체 auto-create', () => {
      // 파일 없음 상태에서 바로 set-field
      removeCtx()
      run('set-field', '--field=config.dev_impl.auto_start', '--value=true')
      const ctx = readCtx()
      assert.equal(typeof ctx.config, 'object')
      assert.equal(typeof ctx.config.dev_impl, 'object')
      assert.equal(ctx.config.dev_impl.auto_start, true)
    })

    // 9. Schema initialization: after any set-field on config-less file, top-level `config` key persists as at least {}
    test('set-field: config 없는 기존 파일에 대해 임의 set-field 실행 후 최상위 config 키가 영속화됨', () => {
      // config 없는 토픽을 만들고 토픽 필드 set-field → config 키가 파일에 생겨야 함
      run('register-topic', '--topic=sch-test', '--spec=some/spec.md')
      run('set-field', '--topic=sch-test', '--field=plan', '--value=.tack/local/active/sch-test/plan.md')
      const ctx = readCtx()
      assert.ok(Object.hasOwn(ctx, 'config'), 'top-level config 키가 존재해야 함')
      assert.equal(typeof ctx.config, 'object')
      assert.ok(ctx.config !== null)
    })

    test('read config: config 없는 파일에서 read --field=config.X.Y → 빈 줄 (예외 아님)', () => {
      writeFileSync(CTX_PATH, JSON.stringify({
        current_topic: null,
        topics: {},
        updatedAt: new Date().toISOString(),
      }), 'utf8')
      const out = run('read', '--field=config.dev_impl.auto_start')
      assert.equal(out, '')
    })

    // 10. read depth > 2 rejected (non-zero exit)
    test('read config: 깊이 3 이상 → non-zero exit', async () => {
      const err = await runExpectFail('read', '--field=config.dev_impl.auto_start.extra')
      assert.notEqual(err.code, 0)
    })

    // 11. set-field depth 1 and depth 3+ rejected (with explicit --value=true)
    test('set-field config: 깊이 1 (config.X만) → non-zero exit', async () => {
      const err = await runExpectFail('set-field', '--field=config.dev_impl', '--value=true')
      assert.notEqual(err.code, 0)
    })

    test('set-field config: 깊이 3 이상 (config.a.b.c) → non-zero exit', async () => {
      const err = await runExpectFail('set-field', '--field=config.a.b.c', '--value=true')
      assert.notEqual(err.code, 0)
    })

    test('set-field config: 최상위 config 단독 → non-zero exit', async () => {
      const err = await runExpectFail('set-field', '--field=config', '--value=true')
      assert.notEqual(err.code, 0)
    })

    // 12. set-field --topic=X --field=config.* → non-zero exit
    test('set-field config 점 경로 + --topic → non-zero exit', async () => {
      run('register-topic', '--topic=cp-topic-test', '--spec=some/spec.md')
      const err = await runExpectFail('set-field', '--topic=cp-topic-test', '--field=config.dev_impl.auto_start', '--value=true')
      assert.notEqual(err.code, 0)
    })

    // 13. Regression: set-field --topic=X --field=plan --value=true stores literal string "true"
    test('회귀: 토픽 필드 set-field는 문자열 보존 (타입 추론 config-only)', () => {
      run('register-topic', '--topic=reg-test', '--spec=some/spec.md')
      run('set-field', '--topic=reg-test', '--field=plan', '--value=true')
      const ctx = readCtx()
      assert.equal(ctx.topics['reg-test'].plan, 'true')
      assert.equal(typeof ctx.topics['reg-test'].plan, 'string')
    })

    // 보안: 프로토타입 오염 방지 — __proto__, constructor, prototype 세그먼트 거부
    test('set-field config.__proto__.polluted → non-zero exit (프로토타입 오염 방어)', async () => {
      const err = await runExpectFail('set-field', '--field=config.__proto__.polluted', '--value=yes')
      assert.notEqual(err.code, 0)
      assert.ok(err.stderr.includes('예약된 키'))
      // Object.prototype이 오염되지 않았는지 간접 확인: 새 객체에 polluted 속성 부재
      assert.equal(({}).polluted, undefined)
    })

    test('set-field config.constructor.X → non-zero exit', async () => {
      const err = await runExpectFail('set-field', '--field=config.constructor.x', '--value=y')
      assert.notEqual(err.code, 0)
    })

    test('set-field config.ns.prototype → non-zero exit (key 자리의 예약어도 거부)', async () => {
      const err = await runExpectFail('set-field', '--field=config.dev_impl.prototype', '--value=y')
      assert.notEqual(err.code, 0)
    })

    test('read config.__proto__.toString → non-zero exit (정보 노출 방어)', async () => {
      const err = await runExpectFail('read', '--field=config.__proto__.toString')
      assert.notEqual(err.code, 0)
    })

    // 보안: Object.prototype 상속 속성이 own property로 읽히지 않음 (hasOwn 가드)
    test('read config.toString.name → 빈 줄 (상속 속성 반환 방지)', () => {
      // 파일이 없거나 config가 비었을 때 Object.prototype.toString이 상속 경로로 보이면 안 됨
      writeFileSync(CTX_PATH, JSON.stringify({ current_topic: null, topics: {}, updatedAt: new Date().toISOString() }), 'utf8')
      const out = run('read', '--field=config.toString.name')
      assert.equal(out, '')
    })

    test('read config.hasOwnProperty.name → 빈 줄 (상속 속성 반환 방지)', () => {
      writeFileSync(CTX_PATH, JSON.stringify({ current_topic: null, topics: {}, updatedAt: new Date().toISOString() }), 'utf8')
      const out = run('read', '--field=config.hasOwnProperty.name')
      assert.equal(out, '')
    })

    test('read config.valueOf.name → 빈 줄 (상속 속성 반환 방지)', () => {
      writeFileSync(CTX_PATH, JSON.stringify({ current_topic: null, topics: {}, updatedAt: new Date().toISOString() }), 'utf8')
      const out = run('read', '--field=config.valueOf.name')
      assert.equal(out, '')
    })

    test('set-field 로 저장된 own property는 정상적으로 읽힘 (hasOwn 가드 회귀 방어)', () => {
      run('set-field', '--field=config.dev_impl.auto_start', '--value=true')
      const out = run('read', '--field=config.dev_impl.auto_start')
      assert.equal(out, 'true')
    })

    // 14. JSON 배열 리터럴 지원
    test('set-field config: JSON 문자열 배열 → 네이티브 배열 저장', () => {
      run('set-field', '--field=config.docs.sourceFilter', '--value=[".claude/",".tack/"]')
      const ctx = readCtx()
      assert.deepEqual(ctx.config.docs.sourceFilter, ['.claude/', '.tack/'])
      assert.ok(Array.isArray(ctx.config.docs.sourceFilter))
    })

    test('read config: 배열 값 → 줄바꿈 구분 출력 (각 원소 한 줄)', () => {
      run('set-field', '--field=config.docs.sourceFilter', '--value=[".claude/",".tack/","CLAUDE.md"]')
      const out = run('read', '--field=config.docs.sourceFilter')
      assert.equal(out, '.claude/\n.tack/\nCLAUDE.md')
    })

    test('set-field config: 빈 배열 [] 저장 → 네이티브 빈 배열', () => {
      run('set-field', '--field=config.docs.sourceFilter', '--value=[]')
      const ctx = readCtx()
      assert.deepEqual(ctx.config.docs.sourceFilter, [])
      assert.ok(Array.isArray(ctx.config.docs.sourceFilter))
    })

    test('read config: 빈 배열 → 빈 출력 (미설정과 동일 동작)', () => {
      run('set-field', '--field=config.docs.sourceFilter', '--value=[]')
      const out = run('read', '--field=config.docs.sourceFilter')
      assert.equal(out, '')
    })

    test('set-field config: 비문자열 원소(숫자) → non-zero exit', async () => {
      const err = await runExpectFail('set-field', '--field=config.docs.sourceFilter', '--value=[1,2]')
      assert.notEqual(err.code, 0)
      assert.ok(err.stderr.includes('문자열 원소만 허용'))
    })

    test('set-field config: 비문자열 원소(null 포함) → non-zero exit', async () => {
      const err = await runExpectFail('set-field', '--field=config.docs.sourceFilter', '--value=[null]')
      assert.notEqual(err.code, 0)
      assert.ok(err.stderr.includes('문자열 원소만 허용'))
    })

    test('set-field config: [invalid (닫는 ] 없음) → 스칼라 문자열로 저장 (정규식 패턴 보호)', () => {
      // [A-Z].* 같은 정규식 스칼라를 보호하기 위해 '[...]' 패턴만 배열로 추론.
      // '[invalid'은 패턴 미매치 → 문자열 그대로 저장 (에러 아님).
      run('set-field', '--field=config.docs.sourceFilter', '--value=[invalid')
      const ctx = readCtx()
      assert.equal(ctx.config.docs.sourceFilter, '[invalid')
      assert.equal(typeof ctx.config.docs.sourceFilter, 'string')
    })

    test('set-field config: [A-Z].* 정규식 스칼라 → 문자열 저장 (배열 오탐 없음)', () => {
      run('set-field', '--field=config.git.branchPattern', '--value=[A-Z].*')
      const ctx = readCtx()
      assert.equal(ctx.config.git.branchPattern, '[A-Z].*')
      assert.equal(typeof ctx.config.git.branchPattern, 'string')
    })

    test('set-field config: 줄바꿈 포함 배열 원소 → non-zero exit', async () => {
      const err = await runExpectFail('set-field', '--field=config.docs.sourceFilter', '--value=["src/\\nlib/"]')
      assert.notEqual(err.code, 0)
      assert.ok(err.stderr.includes('줄바꿈'))
    })

    test('round-trip: 빈 배열은 split-and-filter 시 0 prefix로 해석', () => {
      run('set-field', '--field=config.docs.sourceFilter', '--value=[]')
      const out = run('read', '--field=config.docs.sourceFilter')
      const prefixes = out.split('\n').filter(Boolean)
      assert.equal(prefixes.length, 0)
    })

    test('회귀: 토픽 필드 set-field에는 배열 추론 미적용 (문자열 그대로 저장)', () => {
      run('register-topic', '--topic=arr-reg', '--spec=some/spec.md')
      run('set-field', '--topic=arr-reg', '--field=plan', '--value=["x"]')
      const ctx = readCtx()
      assert.equal(ctx.topics['arr-reg'].plan, '["x"]')
      assert.equal(typeof ctx.topics['arr-reg'].plan, 'string')
    })
  })

  describe('remove-topic', () => {
    test('토픽 제거 후 topics에서 삭제됨', () => {
      run('register-topic', '--topic=rm-test', '--spec=some/spec.md')
      run('remove-topic', '--topic=rm-test')
      const ctx = readCtx()
      assert.equal(ctx.topics['rm-test'], undefined)
    })

    test('current_topic이 제거된 토픽이면 다른 토픽으로 전환', () => {
      run('register-topic', '--topic=a', '--spec=spec-a.md')
      run('register-topic', '--topic=b', '--spec=spec-b.md')
      // b가 current_topic
      assert.equal(run('read', '--field=current_topic'), 'b')
      run('remove-topic', '--topic=b')
      const ctx = readCtx()
      // a로 전환
      assert.equal(ctx.current_topic, 'a')
    })

    test('마지막 토픽 제거 시 current_topic = null', () => {
      run('register-topic', '--topic=only', '--spec=spec.md')
      run('remove-topic', '--topic=only')
      const ctx = readCtx()
      assert.equal(ctx.current_topic, null)
    })

    test('존재하지 않는 토픽 제거 → non-zero exit', async () => {
      const err = await runExpectFail('remove-topic', '--topic=ghost')
      assert.notEqual(err.code, 0)
    })
  })

  describe('force-state', () => {
    test('역방향 복구: VALID_TRANSITIONS 없는 경로도 플래그 없이 성공', () => {
      run('register-topic', '--topic=ft', '--spec=spec.md')
      run('update-state', '--topic=ft', '--phase=spec', '--status=reviewing')
      // spec:reviewing → spec:drafting (역방향, E03/E04 사용 사례)
      run('force-state', '--topic=ft', '--phase=spec', '--status=drafting')
      const ctx = readCtx()
      assert.equal(ctx.topics.ft.phase, 'spec')
      assert.equal(ctx.topics.ft.status, 'drafting')
    })

    test('역방향 복구 시 stderr에 경고 출력', async () => {
      run('register-topic', '--topic=ft2', '--spec=spec.md')
      run('update-state', '--topic=ft2', '--phase=spec', '--status=reviewing')
      const result = await execFileAsync('node', [SCRIPT, 'force-state', '--topic=ft2', '--phase=spec', '--status=drafting'], {
        encoding: 'utf8',
        env: { ...process.env, DEV_CONTEXT_PATH: CTX_PATH },
      })
      assert.match(result.stderr, /VALID_TRANSITIONS를 우회해/)
      assert.match(result.stderr, /관리자 용도/)
    })

    test('순방향 점프는 --allow-unsafe-force 없으면 non-zero exit', async () => {
      run('register-topic', '--topic=ft2b', '--spec=spec.md')
      const err = await runExpectFail('force-state', '--topic=ft2b', '--phase=plan', '--status=ready')
      assert.notEqual(err.code, 0)
      assert.match(err.stderr, /순방향 점프/)
      assert.match(err.stderr, /allow-unsafe-force/)
    })

    test('순방향 점프는 --allow-unsafe-force 있으면 성공', () => {
      run('register-topic', '--topic=ft2c', '--spec=spec.md')
      run('force-state', '--topic=ft2c', '--phase=plan', '--status=ready', '--allow-unsafe-force')
      const ctx = readCtx()
      assert.equal(ctx.topics.ft2c.phase, 'plan')
      assert.equal(ctx.topics.ft2c.status, 'ready')
    })

    test('동일 상태는 no-op (idempotent)', () => {
      run('register-topic', '--topic=ft3', '--spec=spec.md')
      run('force-state', '--topic=ft3', '--phase=spec', '--status=drafting')
      const before = readCtx().topics.ft3.updatedAt
      run('force-state', '--topic=ft3', '--phase=spec', '--status=drafting')
      const after = readCtx().topics.ft3.updatedAt
      assert.equal(before, after)
    })

    test('updatedAt이 갱신됨', async () => {
      run('register-topic', '--topic=ft4', '--spec=spec.md')
      run('update-state', '--topic=ft4', '--phase=spec', '--status=reviewing')
      const before = readCtx().topics.ft4.updatedAt
      await new Promise(r => setTimeout(r, 5))
      // 역방향: reviewing → drafting
      run('force-state', '--topic=ft4', '--phase=spec', '--status=drafting')
      const after = readCtx().topics.ft4.updatedAt
      assert.notEqual(before, after)
    })

    test('--topic 누락 → non-zero exit', async () => {
      const err = await runExpectFail('force-state', '--phase=spec', '--status=drafting')
      assert.notEqual(err.code, 0)
    })

    test('--phase 누락 → non-zero exit', async () => {
      run('register-topic', '--topic=ft5', '--spec=spec.md')
      const err = await runExpectFail('force-state', '--topic=ft5', '--status=drafting')
      assert.notEqual(err.code, 0)
    })

    test('존재하지 않는 토픽 → non-zero exit', async () => {
      const err = await runExpectFail('force-state', '--topic=ghost', '--phase=spec', '--status=drafting')
      assert.notEqual(err.code, 0)
    })

    test('알 수 없는 상태 값 → non-zero exit', async () => {
      run('register-topic', '--topic=ft6', '--spec=spec.md')
      const err = await runExpectFail('force-state', '--topic=ft6', '--phase=garbage', '--status=junk')
      assert.notEqual(err.code, 0)
      assert.match(err.stderr, /알 수 없는 상태/)
    })

    test('--status 누락 → non-zero exit', async () => {
      run('register-topic', '--topic=ft8', '--spec=spec.md')
      const err = await runExpectFail('force-state', '--topic=ft8', '--phase=spec')
      assert.notEqual(err.code, 0)
    })

    test('__proto__ 토픽 이름 → non-zero exit', async () => {
      const err = await runExpectFail('force-state', '--topic=__proto__', '--phase=spec', '--status=drafting')
      assert.notEqual(err.code, 0)
    })

    test('constructor 토픽 이름 → non-zero exit', async () => {
      const err = await runExpectFail('force-state', '--topic=constructor', '--phase=spec', '--status=drafting')
      assert.notEqual(err.code, 0)
    })

    test('prototype 토픽 이름 → non-zero exit', async () => {
      const err = await runExpectFail('force-state', '--topic=prototype', '--phase=spec', '--status=drafting')
      assert.notEqual(err.code, 0)
    })

    test('update-state는 여전히 VALID_TRANSITIONS 강제 (force-state와 독립)', async () => {
      run('register-topic', '--topic=ft7', '--spec=spec.md')
      const err = await runExpectFail('update-state', '--topic=ft7', '--phase=plan', '--status=ready')
      assert.notEqual(err.code, 0)
      assert.match(err.stderr, /유효하지 않은 전환/)
    })
  })
})
