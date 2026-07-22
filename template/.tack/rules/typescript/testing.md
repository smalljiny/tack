---
version: 1
---
# TypeScript Testing Patterns

## Test Framework: Vitest

```typescript
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest'
```

## Type-Safe Mocks

```typescript
// Interface mock
const mockUserRepo: IUserRepository = {
  findById: vi.fn(),
  create: vi.fn(),
  updateById: vi.fn(),
  deleteById: vi.fn(),
}

// Specify return value type
vi.mocked(mockUserRepo.findById).mockResolvedValue({
  id: 'user-1',
  email: 'test@example.com',
  role: 'user',
  createdAt: new Date(),
})
```

## External Module Mock

```typescript
vi.mock('../infrastructure/sendgrid', () => ({
  sendEmail: vi.fn().mockResolvedValue({ success: true }),
}))
```

## Type Tests (type error validation)

```typescript
import { expectTypeOf } from 'vitest'

it('should return correct type', () => {
  expectTypeOf(parseUser).returns.toMatchTypeOf<User>()
})
```

## Test Isolation

```typescript
describe('UserService', () => {
  let service: UserService
  let mockRepo: typeof mockUserRepo

  beforeEach(() => {
    mockRepo = { findById: vi.fn(), create: vi.fn() }
    service = new UserService(mockRepo, mockLogger)
  })

  afterEach(() => {
    vi.clearAllMocks()
  })
})
```

## Async Tests

```typescript
it('should throw NotFoundError when user not found', async () => {
  vi.mocked(mockRepo.findById).mockResolvedValue(null)

  await expect(service.getUser('non-existent')).rejects.toThrow(NotFoundError)
})
```

## Coverage Configuration (vitest.config.ts)

```typescript
export default defineConfig({
  test: {
    coverage: {
      provider: 'v8',
      reporter: ['text', 'lcov'],
      thresholds: {
        lines: 80,
        functions: 80,
        branches: 80,
        statements: 80,
      },
    },
  },
})
```
