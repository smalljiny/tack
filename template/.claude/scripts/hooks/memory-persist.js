#!/usr/bin/env node
/**
 * Stop 훅: 세션 종료 시 현재 상태를 dev-context.json에 저장한다.
 * updatedAt 타임스탬프를 갱신해 세션 이력을 유지한다.
 */

import { readFileSync, writeFileSync, existsSync } from 'fs'
import { join } from 'path'

const cwd = process.env.PWD || process.cwd()
const contextPath = join(cwd, 'docs/_local/dev-context.json')

function main() {
  if (!existsSync(contextPath)) {
    process.exit(0)
  }

  try {
    const context = JSON.parse(readFileSync(contextPath, 'utf-8'))
    const topic = context.current_topic

    if (!topic || !context.topics?.[topic]) {
      process.exit(0)
    }

    // updatedAt 갱신
    context.topics[topic].updatedAt = new Date().toISOString()

    writeFileSync(contextPath, JSON.stringify(context, null, 2) + '\n', 'utf-8')
  } catch {
    // 실패 무시 (비주요 기능)
  }

  process.exit(0)
}

main()
