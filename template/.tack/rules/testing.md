---
version: 2
---
# Testing Rules

## Minimum Coverage: 80%

## Required Test Types

1. **Unit tests** — individual functions, utilities, components
2. **Integration tests** — API endpoints, database operations
3. **E2E tests** — core user flows

## Test-Driven Development (MANDATORY)

```
1. Write the test first (RED)
2. Run the test → it must fail
3. Write minimal implementation (GREEN)
4. Run the test → it must pass
5. Refactor (REFACTOR)
6. Check coverage (80%+)
```

Without confirming that a test fails first, you cannot know whether the test actually verifies behavior.

## Agent Support

- **tdd-specialist** — proactively use for new features and bug fixes

## Test File Patterns (TypeScript)

```
src/
├── foo.ts
└── foo.test.ts        # unit tests (co-located)

tests/
├── integration/       # integration tests
└── e2e/              # E2E tests
```

## Test Failure Troubleshooting

1. Use the **tdd-specialist** agent
2. Verify test isolation
3. Validate that mocks are correct
4. Fix the implementation, not the test (unless the test itself is wrong)

## Vitest Basic Pattern

```typescript
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest'

describe('MyService', () => {
  let service: MyService

  beforeEach(() => {
    service = new MyService()
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  it('should do something specific', async () => {
    // Arrange
    const input = { ... }

    // Act
    const result = await service.doSomething(input)

    // Assert
    expect(result).toEqual({ ... })
  })
})
```

## Mock Principles

- Only mock external services, I/O, and time dependencies
- Do not mock business logic
- Do not share mock state between tests (call `vi.clearAllMocks()` in `afterEach`)

## 다층 Guard 테스트 원칙

다층 guard(입력 검증·인증·인가 등이 계층을 이루는 구조)를 테스트할 때는 검증 대상 guard 이전의 **모든** guard를 통과할 입력을 완비해야 한다.

```
Guard 1 → Guard 2 → Guard 3 (검증 대상)
```

Guard 3을 테스트하는 케이스는 Guard 1·2를 정상 통과하는 입력으로 작성한다. 선행 guard를 우회하거나 mock으로 제거하면, Guard 3 자체가 실패해야 할 입력에서 실패가 선행 guard에서 발생해 테스트가 의도를 검증하지 못한다.

**체크리스트:**
- [ ] 테스트가 실패하는 이유가 검증 대상 guard인가?
- [ ] 선행 guard를 모두 통과하는 입력이 준비됐는가?
- [ ] mock 제거 없이 통합 경로로 실행되는가?
