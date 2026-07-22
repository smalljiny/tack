#!/usr/bin/env node
/**
 * codex 상태를 감지하여 dev-context.json의 config.codex.*에 캐시한다.
 * session-start.js와 /codex:setup 양쪽에서 사용하는 단일 진실 원천.
 *
 * 사용법:
 *   node .claude/scripts/codex/detect-and-cache.js
 *   node .claude/scripts/codex/detect-and-cache.js --force   (TTL 무시하고 강제 갱신)
 */

import { existsSync, readdirSync } from 'fs'
import { join, resolve, sep } from 'path'
import { spawnSync } from 'child_process'
import { homedir } from 'os'

const cwd = process.env.PWD || process.cwd()
const devContextScript = join(cwd, '.harness/scripts/dev-context.js')

const TTL_MS = 60 * 60 * 1000  // 1시간

const args = process.argv.slice(2)
const force = args.includes('--force')

/**
 * config.codex 4개 필드를 원자적으로 저장한다. 오류는 조용히 무시한다.
 */
function writeCodexCache({ available, authenticated, version, checked_at }) {
  const fields = [
    ['config.codex.available',      String(available)],
    ['config.codex.authenticated',  String(authenticated)],
    ['config.codex.version',        version],
    ['config.codex.checked_at',     checked_at],
  ]
  for (const [field, value] of fields) {
    try {
      spawnSync('node', [devContextScript, 'set-field', `--field=${field}`, `--value=${value}`], {
        stdio: 'ignore',
      })
    } catch {
      // 무음 실패
    }
  }
}

/**
 * config.codex.available=false와 함께 4개 필드 전체를 초기화한다.
 */
function setCodexUnavailable() {
  writeCodexCache({
    available: false,
    authenticated: false,
    version: '',
    checked_at: new Date().toISOString(),
  })
}

/**
 * config.codex.checked_at을 읽어 TTL 이내이면 true를 반환한다.
 */
function isCacheValid() {
  if (!existsSync(devContextScript)) return false
  try {
    const result = spawnSync('node', [devContextScript, 'read', '--field=config.codex.checked_at'], {
      encoding: 'utf-8',
      stdio: ['ignore', 'pipe', 'ignore'],
    })
    const raw = (result.stdout ?? '').trim()
    if (!raw) return false
    const ts = Date.parse(raw)
    return !isNaN(ts) && Date.now() - ts < TTL_MS
  } catch {
    return false
  }
}

/**
 * ~/.claude/plugins/cache/openai-codex/codex/<version>/scripts/codex-companion.mjs
 * 패턴으로 companion을 탐지하여 semver 내림차순 최신 경로를 반환한다.
 * containment 검증 포함. 없으면 null 반환.
 */
function findCompanionPath() {
  try {
    const baseDir = join(homedir(), '.claude/plugins/cache/openai-codex/codex')
    if (!existsSync(baseDir)) return null

    const resolvedBase = resolve(baseDir)

    const versions = readdirSync(baseDir, { withFileTypes: true })
      .filter(d => d.isDirectory())
      .map(d => d.name)
      .filter(v => /^\d+\.\d+\.\d+$/.test(v))  // 끝 앵커로 경로 이탈 방지

    if (versions.length === 0) return null

    // semver 내림차순 정렬 (major.minor.patch 숫자 비교)
    versions.sort((a, b) => {
      const pa = a.split('.').map(Number)
      const pb = b.split('.').map(Number)
      for (let i = 0; i < 3; i++) {
        if ((pb[i] ?? 0) !== (pa[i] ?? 0)) return (pb[i] ?? 0) - (pa[i] ?? 0)
      }
      return 0
    })

    const companionPath = join(baseDir, versions[0], 'scripts/codex-companion.mjs')

    // containment 검증: join 결과가 baseDir 밖을 참조하지 않는지 확인
    if (!resolve(companionPath).startsWith(resolvedBase + sep)) return null

    return existsSync(companionPath) ? companionPath : null
  } catch {
    return null
  }
}

/**
 * codex 상태를 감지하여 dev-context.json에 저장한다.
 * --force 없이 호출 시 TTL 이내면 스킵한다.
 */
function detectAndCacheCodex() {
  if (!existsSync(devContextScript)) return

  if (!force && isCacheValid()) return

  try {
    const companionPath = findCompanionPath()
    if (!companionPath) {
      setCodexUnavailable()
      return
    }

    const result = spawnSync('node', [companionPath, 'setup', '--json'], {
      encoding: 'utf-8',
      timeout: 8000,
      killSignal: 'SIGKILL',
    })

    if (result.status !== 0 || !result.stdout) {
      setCodexUnavailable()
      return
    }

    let parsed
    try {
      parsed = JSON.parse(result.stdout)
    } catch {
      setCodexUnavailable()
      return
    }

    writeCodexCache({
      available:     Boolean(parsed.ready && parsed.codex?.available),
      authenticated: Boolean(parsed.auth?.loggedIn && parsed.auth?.verified),
      version:       typeof parsed.codex?.detail === 'string' ? parsed.codex.detail : '',
      checked_at:    new Date().toISOString(),
    })
  } catch {
    setCodexUnavailable()
  }
}

detectAndCacheCodex()
