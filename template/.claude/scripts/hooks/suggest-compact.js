#!/usr/bin/env node
/**
 * PreToolUse 훅: 도구 호출 횟수를 추적하고 전략적 compaction 시점을 제안한다.
 * Exit 0으로 종료 — 제안만 할 뿐 작업을 막지 않는다.
 */

import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';

const THRESHOLD    = parseInt(process.env.COMPACT_THRESHOLD || '50', 10);
const REMIND_EVERY = 25;

function getSessionId() {
  // CLAUDE_SESSION_ID 환경변수 우선, 없으면 PPID로 대체
  return process.env.CLAUDE_SESSION_ID || process.env.PPID || 'default';
}

function getCounterFile() {
  return path.join(os.tmpdir(), `harness-tool-count-${getSessionId()}`);
}

function readCount(file) {
  try {
    return parseInt(fs.readFileSync(file, 'utf8').trim(), 10) || 0;
  } catch {
    return 0;
  }
}

function main() {
  const counterFile = getCounterFile();
  const count       = readCount(counterFile) + 1;

  try {
    fs.writeFileSync(counterFile, String(count), 'utf8');
  } catch {
    process.exit(0); // 카운터 저장 실패는 무시
  }

  if (count === THRESHOLD) {
    process.stderr.write(
      `[StrategicCompact] 도구 호출 ${count}회 — 다음 Task 시작 전 /compact 고려\n`
    );
  } else if (count > THRESHOLD && (count - THRESHOLD) % REMIND_EVERY === 0) {
    process.stderr.write(
      `[StrategicCompact] 도구 호출 ${count}회 — 컨텍스트가 오래됐다면 /compact 좋은 시점\n`
    );
  }

  process.exit(0);
}

main();
