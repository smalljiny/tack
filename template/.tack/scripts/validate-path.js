#!/usr/bin/env node

// validate-path.js — dev-context.json의 경로 필드를 읽어 검증·정규화 후 canonical 절대경로를 stdout에 출력.
// 사용법: node .harness/scripts/validate-path.js --topic=<topic> --field=<field>
// 성공: exit 0 + canonical 절대경로 출력
// 실패: exit 1 + 오류 메시지를 stderr에 출력

import { execSync, execFileSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

function parseArgs(argv) {
  const args = {};
  for (const arg of argv) {
    const m = arg.match(/^--([^=]+)=(.*)$/);
    if (m) args[m[1]] = m[2];
  }
  return args;
}

function main() {
  const { topic, field } = parseArgs(process.argv.slice(2));

  if (!topic || !field) {
    process.stderr.write('Usage: node validate-path.js --topic=<topic> --field=<field>\n');
    process.exit(1);
  }

  // shell injection 방지: topic/field는 영문자·숫자·일부 기호만 허용
  if (!/^[a-zA-Z0-9_-]+$/.test(topic)) {
    process.stderr.write(`Invalid topic: ${topic}\n`);
    process.exit(1);
  }
  if (!/^[a-zA-Z0-9_.]+$/.test(field)) {
    process.stderr.write(`Invalid field: ${field}\n`);
    process.exit(1);
  }

  const repoRoot = execSync('git rev-parse --show-toplevel', { encoding: 'utf8' }).trim();
  const devContextScript = path.join(__dirname, 'dev-context.js');

  let rawPath;
  try {
    rawPath = execFileSync(
      'node',
      [devContextScript, 'read', `--topic=${topic}`, `--field=${field}`],
      { encoding: 'utf8', cwd: repoRoot }
    ).trim();
  } catch (err) {
    process.stderr.write(`Failed to read path (topic=${topic} field=${field}): ${err.message}\n`);
    process.exit(1);
  }

  if (!rawPath) {
    process.stderr.write(`Empty path: topic=${topic} field=${field}\n`);
    process.exit(1);
  }

  // 절대경로·leading dash·경로 탐색·제어 문자·쉘 메타문자 거부
  if (/^\//.test(rawPath) || /^-/.test(rawPath) || /\.\./.test(rawPath) || /[\x00-\x1f]/.test(rawPath)) {
    process.stderr.write(`UNSAFE path rejected: ${rawPath}\n`);
    process.exit(1);
  }
  if (/[^a-zA-Z0-9_.\/\-]/.test(rawPath)) {
    process.stderr.write(`UNSAFE path chars rejected: ${rawPath}\n`);
    process.exit(1);
  }

  const fullPath = path.join(repoRoot, rawPath);

  let canonPath;
  try {
    canonPath = fs.realpathSync(fullPath);
  } catch {
    // 파일이 아직 생성 전일 수 있음 (pre-creation 검증); path.resolve로 폴백
    canonPath = path.resolve(fullPath);
  }

  if (!canonPath.startsWith(repoRoot + path.sep) && canonPath !== repoRoot) {
    process.stderr.write(`Path escapes repo root: ${rawPath}\n`);
    process.exit(1);
  }

  process.stdout.write(canonPath + '\n');
}

main();
