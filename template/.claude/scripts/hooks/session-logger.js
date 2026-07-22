#!/usr/bin/env node
/**
 * PostToolUse 훅 (비동기): 도구 사용 패턴을 세션 로그에 기록한다.
 * sessions/<date>.jsonl 형식으로 저장.
 */

import { appendFileSync, mkdirSync, existsSync, readFileSync } from 'fs'
import { join } from 'path'

const cwd = process.env.PWD || process.cwd()
const toolName = process.argv[2] || 'unknown'
const filePath = process.argv[3] || ''

function getToday() {
  return new Date().toISOString().slice(0, 10)  // YYYY-MM-DD
}

function getCurrentTopic() {
  const contextPath = join(cwd, 'docs/_local/dev-context.json')
  if (!existsSync(contextPath)) return null
  try {
    const context = JSON.parse(readFileSync(contextPath, 'utf-8'))
    return context.current_topic || null
  } catch {
    return null
  }
}

function main() {
  const sessionsDir = join(cwd, '.claude/sessions')

  // sessions/ 디렉토리 생성 (없으면)
  if (!existsSync(sessionsDir)) {
    try {
      mkdirSync(sessionsDir, { recursive: true })
    } catch {
      process.exit(0)
    }
  }

  const logFile = join(sessionsDir, `${getToday()}.jsonl`)
  const topic = getCurrentTopic()

  const entry = {
    ts: new Date().toISOString(),
    tool: toolName,
    ...(filePath && { file: filePath }),
    ...(topic && { topic }),
  }

  try {
    appendFileSync(logFile, JSON.stringify(entry) + '\n', 'utf-8')
  } catch {
    // 로그 실패는 무시 (비주요 기능)
  }

  process.exit(0)
}

main()
