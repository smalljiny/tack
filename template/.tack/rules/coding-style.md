---
version: 1
---
# Coding Style

## Immutability (CRITICAL)

Always create new objects; never mutate existing ones:

```typescript
// WRONG: Mutation
function updateUser(user, name) {
  user.name = name  // MUTATION!
  return user
}

// CORRECT: Immutability
function updateUser(user, name) {
  return { ...user, name }
}
```

## File Structure

- Recommended 200–400 lines per file, maximum 800 lines
- Extract utilities from large components
- Structure by feature/domain, not by type
- High cohesion, low coupling

## Error Handling

Always handle errors explicitly:

```typescript
try {
  const result = await riskyOperation()
  return result
} catch (error) {
  logger.error({ err: error }, 'Operation failed')
  throw new AppError('User-friendly message', 'ERROR_CODE')
}
```

## Input Validation

All external inputs must be validated (Zod recommended):

```typescript
import { z } from 'zod'

const schema = z.object({
  email: z.string().email(),
  age: z.number().int().min(0).max(150),
})

const validated = schema.parse(input)
```

## Environment Variables

Parse at startup with Zod and fail fast:

```typescript
const EnvSchema = z.object({
  NODE_ENV: z.enum(['development', 'production', 'test']).default('development'),
  PORT: z.coerce.number().default(3000),
  DATABASE_URL: z.string().url(),
})

export function getConfig(): Env {
  if (configInstance) return configInstance
  const result = EnvSchema.safeParse(process.env)
  if (!result.success) {
    console.error('Invalid environment variables:', result.error.flatten().fieldErrors)
    process.exit(1)
  }
  configInstance = result.data
  return configInstance
}
```

## Code Quality Checklist

Verify before completing work:
- [ ] Code is readable and names are clear
- [ ] Functions are small (under 50 lines)
- [ ] Files are focused (under 800 lines)
- [ ] No deep nesting (4 levels or less)
- [ ] Error handling is appropriate
- [ ] No `console.log` statements
- [ ] No hardcoded values
- [ ] Immutable patterns are used
