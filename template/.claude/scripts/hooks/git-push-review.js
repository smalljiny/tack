#!/usr/bin/env node
/**
 * PreToolUse 훅: git push 명령어 전 변경 사항 검토를 안내한다.
 * push를 막지 않고 정보만 제공.
 */

const command = process.argv[2] || ''

function isGitPush(cmd) {
  return cmd.trim().startsWith('git push')
}

function main() {
  if (!isGitPush(command)) {
    process.exit(0)
  }

  // push 전 체크리스트 출력
  console.log('[git push 전 확인 사항]')
  console.log('  □ /dev:review 를 완료했는가?')
  console.log('  □ /dev:verify 의 모든 게이트를 통과했는가?')
  console.log('  □ console.log가 남아있지 않은가?')
  console.log('  □ 시크릿이 커밋에 포함되지 않았는가?')
  console.log('')

  // exit 0: push를 막지 않음 (정보 제공만)
  process.exit(0)
}

main()
