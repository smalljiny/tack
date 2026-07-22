---
version: 1
---
# TypeScript Patterns

## Type Design Principles

- No `any` usage — replace with `unknown` and apply type guards
- Minimize `as` type assertions — use only when unavoidable
- Actively use utility types (`Partial`, `Required`, `Pick`, `Omit`, `Readonly`)
- Use interfaces for domain models, type aliases for value objects

```typescript
// WRONG
function process(data: any) { ... }

// CORRECT
function process(data: unknown) {
  if (!isValidData(data)) throw new Error('Invalid data')
  // data is now narrowed
}
```

## Zod Schema Patterns

Runtime validation and type inference simultaneously:

```typescript
import { z } from 'zod'

// Schema definition
const UserSchema = z.object({
  id: z.string().uuid(),
  email: z.string().email(),
  role: z.enum(['admin', 'user']),
  createdAt: z.coerce.date(),
})

// Automatic type inference
type User = z.infer<typeof UserSchema>

// Validation
function parseUser(input: unknown): User {
  return UserSchema.parse(input)
}
```

## Async Error Handling

```typescript
// Result type pattern (Option A)
type Result<T, E = Error> =
  | { success: true; data: T }
  | { success: false; error: E }

async function fetchUser(id: string): Promise<Result<User>> {
  try {
    const user = await userRepo.findById(id)
    if (!user) return { success: false, error: new Error('Not found') }
    return { success: true, data: user }
  } catch (error) {
    return { success: false, error: error as Error }
  }
}
```

## Dependency Injection

Ensure testability through constructor injection:

```typescript
interface IUserRepository {
  findById(id: string): Promise<User | null>
  create(data: CreateUserDto): Promise<User>
}

class UserService {
  constructor(
    private readonly userRepo: IUserRepository,
    private readonly logger: ILogger,
  ) {}

  async getUser(id: string): Promise<User> {
    const user = await this.userRepo.findById(id)
    if (!user) throw new NotFoundError(`User ${id} not found`)
    return user
  }
}
```

## Type Guards

```typescript
function isUser(value: unknown): value is User {
  return (
    typeof value === 'object' &&
    value !== null &&
    'id' in value &&
    'email' in value
  )
}
```

## Module Structure

```
src/
├── domain/          # domain models, interfaces
├── application/     # use cases, services
├── infrastructure/  # external dependency implementations (DB, API)
└── presentation/    # controllers, routers
```
