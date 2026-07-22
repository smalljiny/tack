#!/usr/bin/env node
/**
 * PostToolUse 훅: TypeScript 파일 편집 후 타입 체크를 실행한다.
 * .ts, .tsx 파일에만 동작.
 */

import { execSync } from 'child_process'
import { existsSync } from 'fs'
import { join } from 'path'

const filePath = process.argv[2] || ''
const cwd = process.env.PWD || process.cwd()

function isTypeScriptFile(path) {
  return path.endsWith('.ts') || path.endsWith('.tsx')
}

function hasTsConfig() {
  return existsSync(join(cwd, 'tsconfig.json'))
}

function main() {
  // TypeScript 파일이 아니면 스킵
  if (!isTypeScriptFile(filePath)) {
    process.exit(0)
  }

  // tsconfig.json이 없으면 스킵
  if (!hasTsConfig()) {
    process.exit(0)
  }

  try {
    // tsc 타입 체크 실행 (빌드 없이)
    const result = execSync('npx tsc --noEmit 2>&1', {
      cwd,
      encoding: 'utf-8',
      timeout: 30000,
    })

    // 오류 없음
    process.exit(0)
  } catch (error) {
    // 타입 오류 발생
    const output = error.stdout || error.message || ''

    // 오류가 있으면 경고 출력 (exit 0으로 Claude Code 실행을 막지 않음)
    if (output.trim()) {
      console.warn('[타입 체크] 오류 발견:')
      console.warn(output.slice(0, 500))  // 너무 긴 출력 방지
    }

    process.exit(0)  // 훅 실패로 Claude Code를 막지 않음
  }
}

main()
