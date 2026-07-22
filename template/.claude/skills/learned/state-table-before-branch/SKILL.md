---
version: 1
name: state-table-before-branch
description: 상태 기반 분기 명령어에서 "stop gate 먼저" 패턴이 re-entry 상태를 차단하는 버그를 방지한다.
origin: learned
learned_at: "2026-04-17"
---

## When to Activate

명령어가 여러 진입 상태(first-run, re-entry, error)를 처리할 때.
특히 "특정 상태가 아니면 stop"과 "re-entry 상태이면 다른 흐름"이 공존할 때.

## Pattern

gate를 "invalid → stop"으로 먼저 쓰지 말고,
모든 유효 상태를 테이블로 매핑한 뒤 일치하지 않는 경우에만 stop.

```
❌ 잘못된 순서:
if phase:status != docs:generated → STOP
if phase:status == pr:created → re-entry mode   ← 절대 도달 불가

✅ 올바른 순서:
| phase:status   | mode     |
|----------------|----------|
| docs:generated | first-run|
| pr:created     | re-entry |
| anything else  | STOP     |
```

## Example

`/dev:pr`, `/dev:docs` 명령어의 gate 로직:
```markdown
Determine the entry mode based on `phase:status`:
| `phase:status`  | Mode       |
|-----------------|------------|
| `docs:generated`| First-run  |
| `pr:created`    | Re-entry   |
| anything else   | Stop       |
```

## Why It Works

guard clause 스타일("early stop")은 단일 exit 조건에 유용하지만,
복수의 유효 상태가 있는 경우 exhaustive pattern match(테이블)가 더 안전하다.
