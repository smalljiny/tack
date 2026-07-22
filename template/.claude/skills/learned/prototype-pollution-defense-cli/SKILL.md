---
version: 1
name: prototype-pollution-defense-cli
description: 동적 키로 JSON 객체에 읽기/쓰기하는 CLI에서 __proto__·constructor·prototype 오염과 Object.prototype 상속 속성 노출을 막는 2층 가드 패턴
origin: learned
learned_at: 2026-04-17T10:30:00.000Z
---

## When to Activate

- `--field=X.Y.Z` 같은 사용자 입력 경로로 객체 키를 조립해 read/write하는 CLI 설계 시
- code-reviewer가 "scope·regression 모두 clean"으로 판단한 후에도 security-reviewer/adversarial-reviewer가 동일 코드를 다시 검토할 때
- 신규 CLI에 "config", "settings" 같은 자유로운 중첩 객체 섹션을 추가할 때

## Pattern

두 층을 모두 둔다 — 한 층만 두면 다른 벡터로 새어 나간다.

### 층 1: 쓰기 경로에서 예약 키 거부

경로 파싱 단계에서 `__proto__`, `constructor`, `prototype`을 모든 세그먼트에서 블록한다.

```js
const FORBIDDEN = new Set(['__proto__', 'constructor', 'prototype'])
if (FORBIDDEN.has(segments[1]) || FORBIDDEN.has(segments[2])) {
  return { ok: false, reason: '예약된 키 사용 불가' }
}
```

### 층 2: 읽기 경로에서 hasOwn 가드

`ctx.config?.[ns]?.[key]` 만 쓰면 `Object.prototype`의 상속 속성(`toString`, `valueOf` 등)이 own property처럼 반환된다.

```js
const hasNs = ctx.config && Object.hasOwn(ctx.config, ns)
const nsObj = hasNs ? ctx.config[ns] : undefined
const hasKey = nsObj !== null && typeof nsObj === 'object' && Object.hasOwn(nsObj, key)
const val = hasKey ? nsObj[key] : undefined
```

## Why It Works

- 쓰기 가드만으로는 `read --field=config.toString.name`이 여전히 `"toString"`을 반환해 소비자의 분기를 오도함
- 읽기 가드만으로는 `__proto__`를 경유한 일시적 프로토타입 오염을 허용 (저장은 안 돼도 프로세스 내 상태 오염)
- 두 층이 있을 때 **심볼릭 키 경로를 쓰는 모든 CLI**가 설계상 안전해짐
