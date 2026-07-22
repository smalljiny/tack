---
version: 1
name: test-guard-precedence
description: 다층 guard를 테스트할 때 의도한 guard가 실제로 트립되는지 확인하기 위해 앞 단계 guard를 우회할 입력을 완비하는 테스트 설계 원칙
origin: learned
learned_at: 2026-04-17T10:30:00.000Z
---

## When to Activate

- 한 CLI 호출이 여러 guard(예: missing-arg → protected-field → path-depth → type check)를 순서대로 통과할 때
- "X를 거부해야 한다"는 테스트를 작성하는데 X 이전 단계 guard에 먼저 걸려서 사실상 X의 거부 경로가 실행되지 않는 위험이 있을 때
- Codex plan-review Note에서 "테스트 케이스에 `--value=...`를 추가하라" 같은 지적이 나올 때

## Pattern

테스트에서 거부하려는 guard 이외의 모든 **사전 guard**를 통과할 수 있게 인자를 완비한다.

### 나쁜 예

```js
// depth-1 거부를 검증하려는 의도지만 missing-value guard에 먼저 걸림
runExpectFail('set-field', '--field=config.dev_impl')  // --value 없음
// → 실제 실패 원인: "--value 필요"
// → depth parser가 실행되는지 전혀 검증하지 못함
```

### 좋은 예

```js
// --value를 명시적으로 제공 → depth 가드가 실패 원인임을 보장
runExpectFail('set-field', '--field=config.dev_impl', '--value=true')
// → 실제 실패 원인: "config 경로는 정확히 config.<ns>.<key> 형태여야"
```

## 검증 방법

- 실패 메시지(stderr)의 문구를 assertion에 포함 → 어느 guard가 트립됐는지 확인:
  ```js
  assert.ok(err.stderr.includes('config 경로는 정확히'))
  ```
- 또는 각 guard마다 별도 테스트를 두되, 각 테스트에서 다른 guard들이 pass하는 입력을 구성

## Why It Works

테스트가 "non-zero exit"만 확인하면 **어느 이유로든 실패**하면 통과한다. 구체적 실패 원인을 보장하지 못하면 리팩토링 중 guard 순서가 바뀌거나 하나가 삭제돼도 테스트가 그대로 통과해 회귀를 놓친다.
