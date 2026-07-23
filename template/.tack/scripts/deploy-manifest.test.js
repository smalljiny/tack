// deploy-manifest.test.js — node:test + node:assert 기반 통합 테스트
// list-src / read-files / write 서브커맨드를 임시 디렉토리·파일로 검증한다.
import { test, describe, beforeEach, afterEach } from 'node:test'
import assert from 'node:assert/strict'
import { spawnSync } from 'node:child_process'
import { mkdirSync, writeFileSync, readFileSync, existsSync, rmSync, symlinkSync } from 'node:fs'
import { join, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'
import { tmpdir } from 'node:os'

const __dirname = dirname(fileURLToPath(import.meta.url))
const SCRIPT = join(__dirname, 'deploy-manifest.js')

// 각 테스트가 독립된 임시 작업 디렉토리를 사용한다.
let WORK_DIR = null

function workPath(...segments) {
  return join(WORK_DIR, ...segments)
}

// stderr 캡처가 필요하므로 spawnSync 로 직접 실행한다.
function runRaw(...args) {
  const result = spawnSync('node', [SCRIPT, ...args], { encoding: 'utf8' })
  // node 자체를 띄우지 못한 경우(ENOENT 등): status 가 null 이라 일반 검증을 통과해버림. 즉시 throw.
  if (result.error) throw result.error
  return result
}

function run(...args) {
  const result = runRaw(...args)
  if (result.status !== 0) {
    throw new Error(
      `프로세스가 실패했으나 성공 예상 (exit=${result.status})\nstdout: ${result.stdout}\nstderr: ${result.stderr}`
    )
  }
  return result
}

function runExpectFail(...args) {
  const result = runRaw(...args)
  if (result.status === 0) {
    throw new Error(
      `프로세스가 성공했으나 실패 예상\nstdout: ${result.stdout}\nstderr: ${result.stderr}`
    )
  }
  return result
}

describe('deploy-manifest.js', () => {
  beforeEach(() => {
    WORK_DIR = join(tmpdir(), `deploy-manifest-test-${Date.now()}-${Math.random().toString(36).slice(2)}`)
    mkdirSync(WORK_DIR, { recursive: true })
  })
  afterEach(() => {
    if (WORK_DIR && existsSync(WORK_DIR)) {
      rmSync(WORK_DIR, { recursive: true, force: true })
    }
    WORK_DIR = null
  })

  describe('list-src', () => {
    test('빈 src/ → 빈 출력 + exit 0', () => {
      const srcDir = workPath('src')
      mkdirSync(srcDir, { recursive: true })
      const result = run('list-src', srcDir)
      assert.equal(result.stdout, '')
    })

    test('중첩 파일이 src/ 기준 상대 경로로 정렬되어 줄 단위 출력', () => {
      const srcDir = workPath('src')
      mkdirSync(join(srcDir, '.claude', 'agents'), { recursive: true })
      mkdirSync(join(srcDir, '.tack', 'scripts'), { recursive: true })
      writeFileSync(join(srcDir, 'CLAUDE.md'), 'root\n', 'utf8')
      writeFileSync(join(srcDir, '.claude', 'agents', 'planner.md'), 'a\n', 'utf8')
      writeFileSync(join(srcDir, '.tack', 'scripts', 'helper.js'), 'h\n', 'utf8')

      const result = run('list-src', srcDir)
      const lines = result.stdout.split('\n').filter(Boolean)
      const expected = [
        '.claude/agents/planner.md',
        '.tack/scripts/helper.js',
        'CLAUDE.md',
      ].sort((a, b) => a.localeCompare(b))
      assert.deepEqual(lines, expected)
    })

    test('빈 디렉토리는 결과에 포함되지 않음 (파일만)', () => {
      const srcDir = workPath('src')
      mkdirSync(join(srcDir, '.claude', 'empty-skill'), { recursive: true })
      mkdirSync(join(srcDir, '.tack'), { recursive: true })
      writeFileSync(join(srcDir, '.tack', 'note.md'), 'n\n', 'utf8')

      const result = run('list-src', srcDir)
      const lines = result.stdout.split('\n').filter(Boolean)
      assert.deepEqual(lines, ['.tack/note.md'])
    })

    test('비존재 src/ → non-zero exit + stderr 메시지', () => {
      const ghost = workPath('does-not-exist')
      const result = runExpectFail('list-src', ghost)
      assert.notEqual(result.status, 0)
      assert.ok(result.stderr.length > 0, 'stderr 비어 있으면 안 됨')
    })

    test('인자 누락 → non-zero exit', () => {
      const result = runExpectFail('list-src')
      assert.notEqual(result.status, 0)
    })

    test('심볼릭 링크는 따라가지 않음 (회귀 보호)', () => {
      const srcDir = workPath('src')
      const outsideDir = workPath('outside')
      mkdirSync(srcDir, { recursive: true })
      mkdirSync(outsideDir, { recursive: true })
      writeFileSync(join(srcDir, 'real.md'), 'r\n', 'utf8')
      writeFileSync(join(outsideDir, 'should-not-appear.md'), 'x\n', 'utf8')
      // src/ 안에 외부 디렉토리/파일을 가리키는 심링크를 만든다.
      try {
        symlinkSync(outsideDir, join(srcDir, 'link-to-outside'))
        symlinkSync(join(outsideDir, 'should-not-appear.md'), join(srcDir, 'link-to-file.md'))
      } catch (e) {
        // 일부 환경(특히 Windows)에서 심링크 권한이 없으면 테스트를 스킵하는 대신 명확히 실패한다.
        // POSIX 환경에서는 이 경로가 동작해야 한다.
        throw e
      }

      const result = run('list-src', srcDir)
      const lines = result.stdout.split('\n').filter(Boolean)
      // 실제 파일만 포함, 심링크는 isFile()=false 또는 외부 descend 안 됨.
      assert.deepEqual(lines, ['real.md'])
    })
  })

  describe('read-files', () => {
    test('정상 매니페스트 → files 배열을 줄 단위 출력', () => {
      const manifestPath = workPath('manifest.json')
      writeFileSync(manifestPath, JSON.stringify({
        manifest_version: 1,
        deployed_at: '2026-05-04T00:00:00.000Z',
        source: { commit: null, branch: null },
        files: ['.claude/agents/a.md', '.tack/scripts/x.js', 'CLAUDE.md'],
      }, null, 2) + '\n', 'utf8')

      const result = run('read-files', manifestPath)
      const lines = result.stdout.split('\n').filter(Boolean)
      assert.deepEqual(lines, ['.claude/agents/a.md', '.tack/scripts/x.js', 'CLAUDE.md'])
    })

    test('비존재 파일 → 빈 출력 + exit 0 + stderr 경고', () => {
      const ghost = workPath('no-such-manifest.json')
      const result = runRaw('read-files', ghost)
      assert.equal(result.status, 0)
      assert.equal(result.stdout, '')
      assert.ok(result.stderr.length > 0, 'stderr 경고 필요')
    })

    test('손상 JSON → 빈 출력 + exit 0 + stderr 경고', () => {
      const broken = workPath('broken.json')
      writeFileSync(broken, '{ this is not valid json', 'utf8')
      const result = runRaw('read-files', broken)
      assert.equal(result.status, 0)
      assert.equal(result.stdout, '')
      assert.ok(result.stderr.length > 0, 'stderr 경고 필요')
    })

    test('files 키 누락 → 빈 출력 + exit 0 + stderr 경고', () => {
      const noFiles = workPath('no-files.json')
      writeFileSync(noFiles, JSON.stringify({ manifest_version: 1 }), 'utf8')
      const result = runRaw('read-files', noFiles)
      assert.equal(result.status, 0)
      assert.equal(result.stdout, '')
      assert.ok(result.stderr.length > 0, 'stderr 경고 필요')
    })

    test('files 가 배열이 아님 → 빈 출력 + exit 0 + stderr 경고', () => {
      const notArray = workPath('not-array.json')
      writeFileSync(notArray, JSON.stringify({ files: 'oops' }), 'utf8')
      const result = runRaw('read-files', notArray)
      assert.equal(result.status, 0)
      assert.equal(result.stdout, '')
      assert.ok(result.stderr.length > 0, 'stderr 경고 필요')
    })

    test('인자 누락 → non-zero exit', () => {
      const result = runExpectFail('read-files')
      assert.notEqual(result.status, 0)
    })

    test('의심스러운 경로(.. / 절대경로 / 줄바꿈) 는 무시 + stderr 경고', () => {
      const malicious = workPath('malicious.json')
      writeFileSync(malicious, JSON.stringify({
        manifest_version: 1,
        files: [
          '.claude/agents/safe.md',
          '../../../etc/passwd',
          '/etc/passwd',
          'foo/../bar.md',
          'with\nnewline.md',
          '.tack/another-safe.md',
        ],
      }), 'utf8')

      const result = run('read-files', malicious)
      const lines = result.stdout.split('\n').filter(Boolean)
      // 안전한 항목만 출력
      assert.deepEqual(lines, ['.claude/agents/safe.md', '.tack/another-safe.md'])
      // 의심스러운 경로 4건이 stderr 로 보고됨
      assert.ok(result.stderr.includes('의심스러운 경로'), 'stderr 에 경고 필요')
      assert.ok(result.stderr.includes('../../../etc/passwd'), '.. 경고')
      assert.ok(result.stderr.includes('/etc/passwd'), '절대경로 경고')
    })

    test('files 배열에 string 이 아닌 엔트리는 무시 (조용히)', () => {
      const mixed = workPath('mixed.json')
      writeFileSync(mixed, JSON.stringify({
        manifest_version: 1,
        files: ['ok.md', 42, null, { nested: 'obj' }, 'also-ok.md'],
      }), 'utf8')

      const result = run('read-files', mixed)
      const lines = result.stdout.split('\n').filter(Boolean)
      assert.deepEqual(lines, ['ok.md', 'also-ok.md'])
    })
  })

  describe('write', () => {
    test('files-list 의 줄을 정렬·중복제거해 files 에 기록', () => {
      const filesList = workPath('files.txt')
      writeFileSync(filesList, '.tack/x.js\nCLAUDE.md\n.claude/a.md\nCLAUDE.md\n', 'utf8')
      const target = workPath('target', '.tack', '.deploy-manifest.json')

      run('write', target, filesList, '--commit=abc123', '--branch=main')

      const manifest = JSON.parse(readFileSync(target, 'utf8'))
      // SUT 로직을 미러링하지 않도록 기대 값을 리터럴로 고정한다 (localeCompare 정렬 + 중복 제거 확정값).
      assert.deepEqual(manifest.files, ['.claude/a.md', '.tack/x.js', 'CLAUDE.md'])
    })

    test('manifest_version=1, deployed_at ISO8601 UTC, source 채워짐', () => {
      const filesList = workPath('files.txt')
      writeFileSync(filesList, 'a\nb\n', 'utf8')
      const target = workPath('out', '.tack', '.deploy-manifest.json')

      run('write', target, filesList, '--commit=deadbeef', '--branch=develop')

      const manifest = JSON.parse(readFileSync(target, 'utf8'))
      assert.equal(manifest.manifest_version, 1)
      // ISO8601 UTC: 끝이 'Z'
      assert.match(manifest.deployed_at, /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/)
      assert.equal(manifest.source.commit, 'deadbeef')
      assert.equal(manifest.source.branch, 'develop')
    })

    test('--commit= 빈 값 → source.commit = null', () => {
      const filesList = workPath('files.txt')
      writeFileSync(filesList, 'a\n', 'utf8')
      const target = workPath('out', '.tack', '.deploy-manifest.json')

      run('write', target, filesList, '--commit=', '--branch=main')

      const manifest = JSON.parse(readFileSync(target, 'utf8'))
      assert.equal(manifest.source.commit, null)
      assert.equal(manifest.source.branch, 'main')
    })

    test('--branch= 빈 값 → source.branch = null', () => {
      const filesList = workPath('files.txt')
      writeFileSync(filesList, 'a\n', 'utf8')
      const target = workPath('out', '.tack', '.deploy-manifest.json')

      run('write', target, filesList, '--commit=abc', '--branch=')

      const manifest = JSON.parse(readFileSync(target, 'utf8'))
      assert.equal(manifest.source.commit, 'abc')
      assert.equal(manifest.source.branch, null)
    })

    test('부모 디렉토리 없을 때 자동 생성', () => {
      const filesList = workPath('files.txt')
      writeFileSync(filesList, 'a\n', 'utf8')
      const target = workPath('deep', 'nested', 'path', '.tack', '.deploy-manifest.json')
      assert.equal(existsSync(dirname(target)), false)

      run('write', target, filesList, '--commit=abc', '--branch=main')

      assert.equal(existsSync(target), true)
      const manifest = JSON.parse(readFileSync(target, 'utf8'))
      assert.deepEqual(manifest.files, ['a'])
    })

    test('빈 files-list → files: []', () => {
      const filesList = workPath('files.txt')
      writeFileSync(filesList, '', 'utf8')
      const target = workPath('out', '.tack', '.deploy-manifest.json')

      run('write', target, filesList, '--commit=abc', '--branch=main')

      const manifest = JSON.parse(readFileSync(target, 'utf8'))
      assert.deepEqual(manifest.files, [])
    })

    test('files-list 에 빈 줄/공백 줄 섞여도 무시', () => {
      const filesList = workPath('files.txt')
      writeFileSync(filesList, 'a\n\n  \nb\n', 'utf8')
      const target = workPath('out', '.tack', '.deploy-manifest.json')

      run('write', target, filesList, '--commit=abc', '--branch=main')

      const manifest = JSON.parse(readFileSync(target, 'utf8'))
      assert.deepEqual(manifest.files, ['a', 'b'])
    })

    test('JSON 들여쓰기 2칸 + 끝 개행', () => {
      const filesList = workPath('files.txt')
      writeFileSync(filesList, 'a\n', 'utf8')
      const target = workPath('out', '.tack', '.deploy-manifest.json')

      run('write', target, filesList, '--commit=abc', '--branch=main')

      const raw = readFileSync(target, 'utf8')
      assert.ok(raw.endsWith('\n'), '끝에 개행 필요')
      assert.ok(raw.includes('  "manifest_version"'), '2칸 들여쓰기 필요')
    })

    test('files-list 파일 비존재 → non-zero exit', () => {
      const target = workPath('out', '.tack', '.deploy-manifest.json')
      const result = runExpectFail('write', target, workPath('no-such-list.txt'), '--commit=abc', '--branch=main')
      assert.notEqual(result.status, 0)
    })

    test('인자 누락 → non-zero exit', () => {
      const result = runExpectFail('write')
      assert.notEqual(result.status, 0)
    })
  })

  describe('unknown subcommand', () => {
    test('알 수 없는 서브커맨드 → non-zero exit + 사용 가능한 목록 출력', () => {
      const result = runExpectFail('garbage-cmd')
      assert.notEqual(result.status, 0)
      assert.ok(result.stderr.includes('list-src'), 'list-src 안내 필요')
      assert.ok(result.stderr.includes('read-files'), 'read-files 안내 필요')
      assert.ok(result.stderr.includes('write'), 'write 안내 필요')
    })

    test('서브커맨드 누락 → non-zero exit', () => {
      const result = runExpectFail()
      assert.notEqual(result.status, 0)
    })
  })
})
