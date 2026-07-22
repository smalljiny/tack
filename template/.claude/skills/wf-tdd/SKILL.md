---
version: 4
name: wf-tdd
description: Follow the RED-GREEN-REFACTOR cycle of writing tests first when implementing new features, fixing bugs, or refactoring.
origin: harness
category: dev-process
---

## When to Activate

- When implementing a new function or class
- When fixing a bug
- When refactoring existing code
- When executing a `tdd` type task via the `/flow-impl` command

## Iron Law

**A test that has not been confirmed to fail is the same as no test at all.**

Just because you wrote a test does not mean it actually verifies behavior unless you confirm it fails before implementation.

## RED-GREEN-REFACTOR Cycle

```
       ┌──────────────┐
       │              │
  ┌────▼────┐    ┌────┴────┐
  │   RED   │    │ REFACTOR│
  │ Failing │    │ Cleanup │
  │  test   │    └────▲────┘
  └────┬────┘         │
       │         ┌────┴────┐
       ▼         │  GREEN  │
  [Run test]     │Implement│
  [Confirm fail] │ to pass │
       │         └────┬────┘
       └──────────────┘
                  [Run test]
                  [Confirm pass]
```

## Step-by-Step Execution

### RED: Write a Failing Test

```typescript
// 1. Write the test file
describe('UserService.getUser', () => {
  it('returns the user when they exist', async () => {
    // Arrange
    mockRepo.findById.mockResolvedValue({ id: '1', name: 'Alice' })

    // Act
    const result = await service.getUser('1')

    // Assert
    expect(result).toEqual({ id: '1', name: 'Alice' })
  })

  it('throws NotFoundError when user does not exist', async () => {
    mockRepo.findById.mockResolvedValue(null)

    await expect(service.getUser('999')).rejects.toThrow(NotFoundError)
  })
})
```

```bash
# 2. Run → must fail
pnpm test src/user.test.ts
# Expected: ✗ (fail)
```

### GREEN: Minimal Implementation to Pass

```typescript
// Write only the minimal code needed to pass the tests
class UserService {
  constructor(private readonly userRepo: IUserRepository) {}

  async getUser(id: string): Promise<User> {
    const user = await this.userRepo.findById(id)
    if (!user) throw new NotFoundError(`User ${id} not found`)
    return user
  }
}
```

```bash
# Run → must pass
pnpm test src/user.test.ts
# Expected: ✓ (pass)
```

### REFACTOR: Clean Up Code

- Keep tests green
- Improve names, remove duplication, reduce complexity
- Re-run tests after refactoring

```bash
pnpm test src/user.test.ts
```

## Edge Case Checklist

For each function, test:
- [ ] Happy path
- [ ] null / undefined input
- [ ] Empty string / empty array
- [ ] Boundary values (0, -1, maximum)
- [ ] Invalid type input
- [ ] Error paths (throw cases)
- [ ] Async failure cases

## Check Coverage

```bash
pnpm test:coverage
```

Achieve a minimum of 80%. Target 100% for core business logic.

## Common Rationalizations and Rebuttals

| Rationalization | Rebuttal |
|-----------------|----------|
| "This code is too simple to need a test" | When simple code changes, mistakes cannot be caught without tests |
| "I'll add tests later" | Later, implementation details make testing harder |
| "I don't have time" | Without tests, debugging takes even more time |
| "I already tested it manually" | Manual testing does not catch regressions |

## Pre-Completion Checklist

- [ ] All functions have tests
- [ ] Confirmed each test fails before implementation
- [ ] Edge cases are covered
- [ ] Error paths are tested
- [ ] Coverage is 80%+
- [ ] All tests pass
