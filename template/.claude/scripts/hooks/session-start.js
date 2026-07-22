#!/usr/bin/env node
/**
 * SessionStart 훅: dev-context.json을 로드하고 이전 작업 컨텍스트를 복원한다.
 * codex 상태 감지는 .claude/scripts/codex/detect-and-cache.js에 위임한다.
 */

import { readFileSync, existsSync } from 'fs'
import { join } from 'path'
import { spawnSync } from 'child_process'

const cwd = process.env.PWD || process.cwd()
const contextPath = join(cwd, 'docs/_local/dev-context.json')
const detectScript = join(cwd, '.claude/scripts/codex/detect-and-cache.js')

function main() {
  if (existsSync(contextPath)) {
    try {
      const context = JSON.parse(readFileSync(contextPath, 'utf-8'))
      const topic = context.current_topic

      if (topic) {
        const topicData = context.topics?.[topic]
        if (topicData) {
          // 이전 컨텍스트 출력 (Claude Code가 시스템 메시지로 인식)
          console.log(`[컨텍스트 복원] 주제: ${topic} | phase: ${topicData.phase}`)

          if (topicData.currentStory) {
            console.log(`[컨텍스트 복원] 다음 Story: ${topicData.currentStory}`)
            console.log(`  → /dev:impl 로 계속하세요.`)
          }

          if (topicData.plan) {
            console.log(`[컨텍스트 복원] 계획 파일: ${topicData.plan}`)
          }
        }
      }
    } catch {
      // 파일 파싱 오류 무시
    }
  }

  // codex 상태 감지 — TTL(1h) 내 캐시가 유효하면 스킵
  if (existsSync(detectScript)) {
    try {
      spawnSync('node', [detectScript], { stdio: 'ignore' })
    } catch {
      // 무음 실패
    }
  }

  process.exit(0)
}

main()
