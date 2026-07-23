#!/usr/bin/env node
// deploy-manifest.js — deploy 매니페스트 JSON I/O + src/ 파일 열거 헬퍼
// 사용법:
//   node .tack/scripts/deploy-manifest.js list-src <src-dir>
//   node .tack/scripts/deploy-manifest.js read-files <manifest-path>
//   node .tack/scripts/deploy-manifest.js write <target-manifest> <files-list-path> --commit=<sha> --branch=<name>
//   node .tack/scripts/deploy-manifest.js strip-gitignore-block <gitignore-path>

import { readFileSync, writeFileSync, existsSync, mkdirSync, renameSync, readdirSync, statSync } from 'node:fs'
import { join, relative, dirname } from 'node:path'

const SUBCOMMANDS = ['list-src', 'read-files', 'write', 'strip-gitignore-block']

function die(msg) {
  process.stderr.write(msg + '\n')
  process.exit(1)
}

function warn(msg) {
  process.stderr.write(msg + '\n')
}

// --key=value 옵션 + positional 인자 분리
function parseArgs(argv) {
  const opts = {}
  const positional = []
  for (const arg of argv) {
    const m = arg.match(/^--([^=]+)=(.*)$/)
    if (m) {
      opts[m[1]] = m[2]
    } else if (/^--[a-zA-Z]/.test(arg)) {
      // boolean flag (값 없음): --flag → opts.flag = true
      opts[arg.slice(2)] = true
    } else {
      positional.push(arg)
    }
  }
  return { opts, positional }
}

function cmdListSrc(positional) {
  if (positional.length < 1) {
    die('list-src: src 디렉토리 인자 필요 (예: list-src src/)')
  }
  const srcDir = positional[0]
  if (!existsSync(srcDir)) {
    die(`list-src: src 디렉토리가 존재하지 않습니다: ${srcDir}`)
  }
  const st = statSync(srcDir)
  if (!st.isDirectory()) {
    die(`list-src: src 경로가 디렉토리가 아닙니다: ${srcDir}`)
  }

  // 직접 재귀: readdirSync({recursive:true})는 심링크 디렉토리를 descent 해 외부 파일을
  // 결과에 포함시키므로 사용 불가. lstat 의미의 isSymbolicLink() 로 심링크는 모두 스킵한다.
  const files = []
  const stack = [srcDir]
  while (stack.length > 0) {
    const dir = stack.pop()
    for (const ent of readdirSync(dir, { withFileTypes: true })) {
      if (ent.isSymbolicLink()) continue
      const full = join(dir, ent.name)
      if (ent.isDirectory()) {
        stack.push(full)
      } else if (ent.isFile()) {
        files.push(relative(srcDir, full))
      }
    }
  }
  files.sort((a, b) => a.localeCompare(b))
  if (files.length > 0) {
    process.stdout.write(files.join('\n') + '\n')
  }
}

function cmdReadFiles(positional) {
  if (positional.length < 1) {
    die('read-files: 매니페스트 경로 인자 필요')
  }
  const manifestPath = positional[0]
  if (!existsSync(manifestPath)) {
    warn(`read-files: 매니페스트 파일이 없습니다 (첫 deploy 가능성): ${manifestPath}`)
    return
  }
  let raw
  try {
    raw = readFileSync(manifestPath, 'utf8')
  } catch (e) {
    warn(`read-files: 매니페스트 읽기 실패: ${e.message}`)
    return
  }
  let data
  try {
    data = JSON.parse(raw)
  } catch (e) {
    warn(`read-files: 매니페스트 JSON 파싱 실패: ${e.message}`)
    return
  }
  if (!data || typeof data !== 'object' || !Array.isArray(data.files)) {
    warn(`read-files: 매니페스트의 files 배열이 없거나 형식이 잘못됨: ${manifestPath}`)
    return
  }
  // 호출자(deploy 스크립트)가 매니페스트 경로를 rm/rsync/rmdir 의 인자로 사용하므로,
  // 매니페스트가 사용자 편집·외부 도구로 손상돼 path traversal 시도가 들어와도
  // TARGET_DIR 밖으로 escape 하지 않도록 emit 단계에서 가드한다 (defense-in-depth).
  for (const entry of data.files) {
    if (typeof entry !== 'string') continue
    if (entry.startsWith('/') || /(?:^|\/)\.\.(?:\/|$)/.test(entry) || /[\0\n\r]/.test(entry)) {
      warn(`read-files: 의심스러운 경로 무시: ${entry}`)
      continue
    }
    process.stdout.write(entry + '\n')
  }
}

function cmdWrite(positional, opts) {
  if (positional.length < 2) {
    die('write: <target-manifest> 와 <files-list-path> 인자 필요')
  }
  const target = positional[0]
  const filesListPath = positional[1]

  if (!existsSync(filesListPath)) {
    die(`write: files-list 파일이 존재하지 않습니다: ${filesListPath}`)
  }

  const raw = readFileSync(filesListPath, 'utf8')
  // 줄 단위 분할 + 양 끝 공백 제거 + 빈 줄 제거 + 중복 제거 + 정렬
  const seen = new Set()
  for (const line of raw.split('\n')) {
    const trimmed = line.trim()
    if (trimmed.length === 0) continue
    seen.add(trimmed)
  }
  const files = [...seen].sort((a, b) => a.localeCompare(b))

  // --commit / --branch: 빈 문자열은 null 로 기록
  const commitOpt = opts.commit
  const branchOpt = opts.branch
  const commit = (commitOpt === undefined || commitOpt === '') ? null : commitOpt
  const branch = (branchOpt === undefined || branchOpt === '') ? null : branchOpt

  const manifest = {
    manifest_version: 1,
    deployed_at: new Date().toISOString(),
    source: {
      commit,
      branch,
    },
    files,
  }

  // 부모 디렉토리 자동 생성
  const dir = dirname(target)
  mkdirSync(dir, { recursive: true })

  // 원자적 쓰기: 임시 파일에 쓴 뒤 rename
  const tmp = target + '.tmp'
  writeFileSync(tmp, JSON.stringify(manifest, null, 2) + '\n', 'utf8')
  renameSync(tmp, target)
}

function cmdStripGitignoreBlock(positional) {
  if (positional.length < 1) {
    die('strip-gitignore-block: .gitignore 경로 인자 필요')
  }
  const gitignorePath = positional[0]
  if (!existsSync(gitignorePath)) {
    warn(`strip-gitignore-block: .gitignore 파일이 없습니다: ${gitignorePath}`)
    return
  }
  let raw
  try {
    raw = readFileSync(gitignorePath, 'utf8')
  } catch (e) {
    die(`strip-gitignore-block: 파일 읽기 실패: ${e.message}`)
  }
  const BEGIN = '# BEGIN harness local ignores'
  const END = '# END harness local ignores'
  const lines = raw.split('\n')
  const out = []
  let skip = false
  for (const line of lines) {
    if (line === BEGIN) {
      // BEGIN 직전 빈 줄 제거
      while (out.length > 0 && out[out.length - 1] === '') {
        out.pop()
      }
      skip = true
    }
    if (skip) {
      if (line === END) skip = false
      continue
    }
    out.push(line)
  }
  // 내용이 있으면 단일 개행으로 끝냄
  let content = out.join('\n').trimEnd()
  if (content.length > 0) content += '\n'

  const tmp = gitignorePath + '.tmp'
  writeFileSync(tmp, content, 'utf8')
  renameSync(tmp, gitignorePath)
}

const [,, subcommand, ...rest] = process.argv
const { opts, positional } = parseArgs(rest)

switch (subcommand) {
  case 'list-src':
    cmdListSrc(positional)
    break
  case 'read-files':
    cmdReadFiles(positional)
    break
  case 'write':
    cmdWrite(positional, opts)
    break
  case 'strip-gitignore-block':
    cmdStripGitignoreBlock(positional)
    break
  default:
    die(`알 수 없는 서브커맨드: ${subcommand ?? '(없음)'}\n사용 가능: ${SUBCOMMANDS.join(', ')}`)
}
