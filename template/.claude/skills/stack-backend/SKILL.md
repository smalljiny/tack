---
version: 2
name: stack-backend
description: Backend architecture patterns for Node.js/Fastify: API design, repository pattern, rate limiting, background jobs, and logging.
origin: ECC+SCE
capabilities: [language-patterns, typescript, backend]
---

# Backend Development Patterns

Backend architecture patterns and best practices for this project's Fastify + MongoDB + Redis stack.

## API Design Patterns

### RESTful API Structure (Fastify)

```typescript
// ✅ Resource-based URLs with Fastify
import { FastifyInstance } from 'fastify'

export async function userRoutes(fastify: FastifyInstance) {
  // List resources
  fastify.get('/users', listUsersHandler)

  // Get single resource
  fastify.get('/users/:id', getUserHandler)

  // Create resource
  fastify.post('/users', createUserHandler)

  // Update resource
  fastify.patch('/users/:id', updateUserHandler)

  // Delete resource
  fastify.delete('/users/:id', deleteUserHandler)
}

// ✅ Query parameters for filtering, sorting, pagination
// GET /users?status=active&sort=createdAt&limit=20&skip=0
```

### Fastify Plugin Pattern

```typescript
import fp from 'fastify-plugin'
import { FastifyInstance } from 'fastify'

// ✅ Encapsulated plugin with decorators
export const authPlugin = fp(async (fastify: FastifyInstance) => {
  fastify.decorate('authenticate', async (request, reply) => {
    try {
      const token = request.headers.authorization?.replace('Bearer ', '')
      if (!token) throw new Error('Missing token')

      const user = await verifyJwt(token)
      request.user = user
    } catch (err) {
      reply.code(401).send({ error: 'Unauthorized' })
    }
  })
})

// ✅ Route-level authentication
fastify.get('/protected', {
  preHandler: [fastify.authenticate]
}, async (request, reply) => {
  return { user: request.user }
})
```

## Repository Pattern (MongoDB)

### BaseRepository

```typescript
// packages/database/src/repositories/base.repository.ts
import { Collection, ObjectId, Document } from 'mongodb'

export abstract class BaseRepository<T extends Document> {
  constructor(protected collection: Collection<T>) {}

  // ✅ Anti-corruption layer: id (string) ↔ _id (ObjectId)
  protected toEntity(doc: T & { _id: ObjectId }): T & { id: string } {
    const { _id, ...rest } = doc
    return { ...rest, id: _id.toHexString() } as T & { id: string }
  }

  protected toObjectId(id: string): ObjectId {
    return new ObjectId(id)
  }

  async findById(id: string): Promise<(T & { id: string }) | null> {
    const doc = await this.collection.findOne({ _id: this.toObjectId(id) })
    return doc ? this.toEntity(doc) : null
  }

  async findAll(filter: Partial<T> = {}): Promise<(T & { id: string })[]> {
    const docs = await this.collection.find(filter).toArray()
    return docs.map(doc => this.toEntity(doc))
  }

  async create(data: Omit<T, '_id'>): Promise<T & { id: string }> {
    const result = await this.collection.insertOne(data as T)
    return this.toEntity({ ...data, _id: result.insertedId } as T & { _id: ObjectId })
  }

  async update(id: string, data: Partial<T>): Promise<(T & { id: string }) | null> {
    const result = await this.collection.findOneAndUpdate(
      { _id: this.toObjectId(id) },
      { $set: data },
      { returnDocument: 'after' }
    )
    return result ? this.toEntity(result) : null
  }

  async delete(id: string): Promise<boolean> {
    const result = await this.collection.deleteOne({ _id: this.toObjectId(id) })
    return result.deletedCount > 0
  }
}
```

### CacheableBaseRepository (Redis Read-Through)

```typescript
// packages/database/src/repositories/cacheable-base.repository.ts
import { RedisClient } from '../cache/redis.client'

export abstract class CacheableBaseRepository<T extends Document> extends BaseRepository<T> {
  constructor(
    collection: Collection<T>,
    protected redis: RedisClient,
    protected cachePrefix: string,
    protected ttl: number = 300 // 5 minutes
  ) {
    super(collection)
  }

  // ✅ Cache key pattern: {prefix}:{id}
  protected getCacheKey(id: string): string {
    return `${this.cachePrefix}:${id}`
  }

  async findById(id: string): Promise<(T & { id: string }) | null> {
    const cacheKey = this.getCacheKey(id)

    // Check cache first
    const cached = await this.redis.get(cacheKey)
    if (cached) {
      return JSON.parse(cached)
    }

    // Cache miss - fetch from database
    const entity = await super.findById(id)

    if (entity) {
      await this.redis.setex(cacheKey, this.ttl, JSON.stringify(entity))
    }

    return entity
  }

  // ✅ Invalidate cache on mutations
  async update(id: string, data: Partial<T>): Promise<(T & { id: string }) | null> {
    await this.redis.del(this.getCacheKey(id))
    return super.update(id, data)
  }

  async delete(id: string): Promise<boolean> {
    await this.redis.del(this.getCacheKey(id))
    return super.delete(id)
  }

  async invalidateCache(id: string): Promise<void> {
    await this.redis.del(this.getCacheKey(id))
  }
}
```

## Service Layer Pattern

```typescript
// apps/api/src/services/user.service.ts
import { UserRepository } from '@packages/database'
import { CreateUserDto, UpdateUserDto } from '@packages/types-shared'

export class UserService {
  constructor(private userRepo: UserRepository) {}

  async createUser(dto: CreateUserDto) {
    // Business logic validation
    const existing = await this.userRepo.findByEmail(dto.email)
    if (existing) {
      throw new ConflictError('Email already exists')
    }

    // Hash password before storing
    const hashedPassword = await hashPassword(dto.password)

    return this.userRepo.create({
      ...dto,
      password: hashedPassword,
      createdAt: new Date()
    })
  }

  async updateUser(id: string, dto: UpdateUserDto) {
    const user = await this.userRepo.findById(id)
    if (!user) {
      throw new NotFoundError('User not found')
    }

    return this.userRepo.update(id, dto)
  }
}
```

## Database Patterns (MongoDB)

### Query Optimization

```typescript
// ✅ GOOD: Project only needed fields
const users = await collection
  .find({ status: 'active' })
  .project({ name: 1, email: 1, status: 1 })
  .sort({ createdAt: -1 })
  .limit(10)
  .toArray()

// ❌ BAD: Fetch all fields
const users = await collection.find({ status: 'active' }).toArray()
```

### N+1 Query Prevention

```typescript
// ❌ BAD: N+1 query problem
const posts = await postRepo.findAll()
for (const post of posts) {
  post.author = await userRepo.findById(post.authorId)  // N queries
}

// ✅ GOOD: Batch fetch with $in
const posts = await postRepo.findAll()
const authorIds = [...new Set(posts.map(p => p.authorId))]
const authors = await userRepo.findByIds(authorIds)  // 1 query
const authorMap = new Map(authors.map(a => [a.id, a]))

posts.forEach(post => {
  post.author = authorMap.get(post.authorId)
})
```

### MongoDB Transaction

```typescript
async function transferCredits(fromUserId: string, toUserId: string, amount: number) {
  const session = client.startSession()

  try {
    await session.withTransaction(async () => {
      // Deduct from sender
      await usersCollection.updateOne(
        { _id: new ObjectId(fromUserId), credits: { $gte: amount } },
        { $inc: { credits: -amount } },
        { session }
      )

      // Add to receiver
      await usersCollection.updateOne(
        { _id: new ObjectId(toUserId) },
        { $inc: { credits: amount } },
        { session }
      )
    })
  } finally {
    await session.endSession()
  }
}
```

### Aggregation Pipeline

```typescript
// ✅ Complex queries with aggregation
const stats = await collection.aggregate([
  { $match: { status: 'active' } },
  { $group: {
    _id: '$category',
    count: { $sum: 1 },
    avgPrice: { $avg: '$price' }
  }},
  { $sort: { count: -1 } },
  { $limit: 10 }
]).toArray()
```

## Redis Caching Patterns

### Cache Key Conventions

```typescript
// ✅ Consistent key naming
const CACHE_KEYS = {
  user: (id: string) => `user:${id}`,
  userByEmail: (email: string) => `user:email:${email}`,
  userList: (page: number) => `users:list:${page}`,
  session: (token: string) => `session:${token}`,
} as const
```

### Cache Invalidation Strategies

```typescript
// ✅ Pattern-based invalidation
async function invalidateUserCache(userId: string) {
  const keys = await redis.keys(`user:${userId}:*`)
  if (keys.length > 0) {
    await redis.del(...keys)
  }
  await redis.del(`user:${userId}`)
}

// ✅ Event-driven invalidation
eventEmitter.on('user:updated', async (userId: string) => {
  await invalidateUserCache(userId)
})
```

## Error Handling Patterns

### Custom Error Classes

```typescript
// packages/utils/src/errors.ts
export class AppError extends Error {
  constructor(
    public statusCode: number,
    public message: string,
    public code?: string
  ) {
    super(message)
    this.name = this.constructor.name
  }
}

export class NotFoundError extends AppError {
  constructor(message = 'Resource not found') {
    super(404, message, 'NOT_FOUND')
  }
}

export class ConflictError extends AppError {
  constructor(message = 'Resource already exists') {
    super(409, message, 'CONFLICT')
  }
}

export class ValidationError extends AppError {
  constructor(message = 'Validation failed', public details?: unknown) {
    super(400, message, 'VALIDATION_ERROR')
  }
}
```

### Fastify Error Handler

```typescript
// apps/api/src/plugins/error-handler.ts
import { FastifyError, FastifyReply, FastifyRequest } from 'fastify'
import { ZodError } from 'zod'
import { AppError } from '@packages/utils'

export function errorHandler(
  error: FastifyError,
  request: FastifyRequest,
  reply: FastifyReply
) {
  // Zod validation error
  if (error instanceof ZodError) {
    return reply.code(400).send({
      success: false,
      error: 'Validation failed',
      details: error.errors
    })
  }

  // Custom app error
  if (error instanceof AppError) {
    return reply.code(error.statusCode).send({
      success: false,
      error: error.message,
      code: error.code
    })
  }

  // MongoDB duplicate key error
  if (error.name === 'MongoServerError' && (error as any).code === 11000) {
    return reply.code(409).send({
      success: false,
      error: 'Duplicate entry',
      code: 'DUPLICATE_KEY'
    })
  }

  // Unexpected error
  request.log.error(error)
  return reply.code(500).send({
    success: false,
    error: 'Internal server error'
  })
}
```

## Authentication & Authorization

### JWT with Fastify

```typescript
// apps/auth/src/plugins/jwt.ts
import fp from 'fastify-plugin'
import fastifyJwt from '@fastify/jwt'

export const jwtPlugin = fp(async (fastify) => {
  fastify.register(fastifyJwt, {
    secret: process.env.JWT_SECRET!,
    sign: { expiresIn: '7d' }
  })

  fastify.decorate('authenticate', async (request, reply) => {
    try {
      await request.jwtVerify()
    } catch (err) {
      reply.code(401).send({ error: 'Unauthorized' })
    }
  })
})

// Usage in routes
fastify.get('/me', {
  preHandler: [fastify.authenticate]
}, async (request) => {
  return { user: request.user }
})
```

### Role-Based Access Control

```typescript
type Role = 'admin' | 'moderator' | 'user'
type Permission = 'read' | 'write' | 'delete' | 'admin'

const rolePermissions: Record<Role, Permission[]> = {
  admin: ['read', 'write', 'delete', 'admin'],
  moderator: ['read', 'write', 'delete'],
  user: ['read', 'write']
}

export function requirePermission(permission: Permission) {
  return async (request: FastifyRequest, reply: FastifyReply) => {
    const user = request.user as { role: Role }

    if (!rolePermissions[user.role].includes(permission)) {
      reply.code(403).send({ error: 'Insufficient permissions' })
    }
  }
}

// Usage
fastify.delete('/users/:id', {
  preHandler: [fastify.authenticate, requirePermission('delete')]
}, deleteUserHandler)
```

## Zod Schema Validation (SSOT)

### Schema Definition

```typescript
// packages/types-shared/src/schemas/user.schema.ts
import { z } from 'zod'

export const userSchema = z.object({
  id: z.string(),
  email: z.string().email(),
  name: z.string().min(2).max(100),
  role: z.enum(['admin', 'moderator', 'user']),
  createdAt: z.date(),
  updatedAt: z.date().optional()
})

export const createUserSchema = userSchema.omit({
  id: true,
  createdAt: true,
  updatedAt: true
}).extend({
  password: z.string().min(8)
})

export const updateUserSchema = createUserSchema.partial().omit({
  password: true
})

// Type inference
export type User = z.infer<typeof userSchema>
export type CreateUserDto = z.infer<typeof createUserSchema>
export type UpdateUserDto = z.infer<typeof updateUserSchema>
```

### Fastify Schema Integration

```typescript
import { createUserSchema } from '@packages/types-shared'

fastify.post('/users', {
  schema: {
    body: createUserSchema
  },
  preHandler: async (request) => {
    // Zod validation
    request.body = createUserSchema.parse(request.body)
  }
}, createUserHandler)
```

## Monorepo Patterns

### Package Dependencies

```
packages/types-shared  (no dependencies)
    ↓
packages/utils         (depends on types-shared)
    ↓
packages/database      (depends on utils, types-shared)
    ↓
apps/api, apps/auth    (depends on packages)
```

### Shared Configuration

```typescript
// packages/utils/src/config.ts
export function getConfig() {
  return {
    mongodb: {
      uri: process.env.MONGODB_URI!,
      dbName: process.env.MONGODB_DB_NAME!
    },
    redis: {
      url: process.env.REDIS_URL!
    },
    jwt: {
      secret: process.env.JWT_SECRET!
    }
  }
}
```

**Remember**: These patterns enable scalable, maintainable backend applications. Choose patterns that fit your complexity level and always follow the project's established conventions.

<!-- origin: ECC backend-patterns -->
## Rate Limiting

### Rate Limiting (Production Pattern)

> **⚠️ Security note**: Never use `request.headers.get('x-forwarded-for')` directly as a rate-limit key — this header is client-controlled and can be spoofed to bypass limits. Always derive the client IP from the framework's trusted-proxy API after explicit proxy configuration.

**Recommended approach**: Use a shared backend store (Redis) with atomic increment/expiry so limits survive restarts and work across multiple instances.

```typescript
import Fastify from 'fastify'
import fastifyRateLimit from '@fastify/rate-limit'
import Redis from 'ioredis'

const redis = new Redis(process.env.REDIS_URL!)

const app = Fastify()

// Configure rate limiting with Redis store (multi-instance safe)
await app.register(fastifyRateLimit, {
  max: 100,
  timeWindow: '1 minute',
  redis,
  keyGenerator: (request) => {
    // Use framework's trusted IP resolution after proxy configuration
    return request.ip  // Fastify resolves via trustProxy setting
  },
  errorResponseBuilder: (_req, context) => ({
    statusCode: 429,
    error: 'Too Many Requests',
    message: `Rate limit exceeded. Retry after ${context.after}`,
  }),
})

// Trust proxy — set to number of proxy hops, not true (avoids header spoofing)
const app = Fastify({ trustProxy: 1 })
```

> **Local-dev only** — If you need a simple in-memory limiter for local development:
> ```typescript
> // LOCAL DEV ONLY — not for production (single-instance, non-persistent, spoofable IP)
> const requests = new Map<string, number[]>()
> function checkLimit(key: string, max: number, windowMs: number): boolean {
>   const now = Date.now()
>   const times = (requests.get(key) || []).filter(t => now - t < windowMs)
>   if (times.length >= max) return false
>   times.push(now)
>   requests.set(key, times)
>   return true
> }
> ```


<!-- origin: ECC backend-patterns -->
## Background Jobs & Queues

### Background Jobs & Queues (Production Pattern)

> **⚠️ Data loss risk**: An in-memory queue loses all pending jobs on process restart, crash, or deploy. Never use it for work that must not be lost (payments, emails, indexing).

**Recommended approach**: Persist the job before returning 202. Use BullMQ (Redis-backed), pg-boss (Postgres), or a cloud queue (SQS/Pub-Sub) for durability, retry, and dead-letter handling.

```typescript
import { Queue, Worker } from 'bullmq'
import Redis from 'ioredis'

const connection = new Redis(process.env.REDIS_URL!, { maxRetriesPerRequest: null })

// Producer: persist job before returning success
const indexQueue = new Queue<{ marketId: string }>('market-indexing', { connection })

export async function POST(request: Request) {
  const { marketId } = await request.json()

  // Job is persisted in Redis before we respond — survives restarts
  await indexQueue.add('index', { marketId }, {
    attempts: 3,
    backoff: { type: 'exponential', delay: 2000 },
  })

  return Response.json({ success: true, message: 'Job queued' }, { status: 202 })
}

// Consumer (separate worker process or file)
const worker = new Worker<{ marketId: string }>(
  'market-indexing',
  async (job) => {
    // Idempotent job — safe to retry
    await indexMarket(job.data.marketId)
  },
  { connection, concurrency: 5 }
)

worker.on('failed', (job, err) => {
  // Structured error logging — job goes to dead-letter after max attempts
  console.error({ jobId: job?.id, marketId: job?.data.marketId, error: err.message })
})
```

> **Local-dev only** — If you need a simple in-process queue for local development:
> ```typescript
> // LOCAL DEV ONLY — no persistence, no retry, no multi-instance support
> const queue: Array<() => Promise<void>> = []
> let running = false
> async function enqueue(fn: () => Promise<void>) {
>   queue.push(fn)
>   if (!running) { running = true; while (queue.length) { try { await queue.shift()!() } catch (e) { console.error(e) } } running = false }
> }
> ```


<!-- origin: ECC backend-patterns -->
## Logging & Monitoring

### Structured Logging

```typescript
interface LogContext {
  userId?: string
  requestId?: string
  method?: string
  path?: string
  [key: string]: unknown
}

class Logger {
  log(level: 'info' | 'warn' | 'error', message: string, context?: LogContext) {
    const entry = {
      timestamp: new Date().toISOString(),
      level,
      message,
      ...context
    }

    console.log(JSON.stringify(entry))
  }

  info(message: string, context?: LogContext) {
    this.log('info', message, context)
  }

  warn(message: string, context?: LogContext) {
    this.log('warn', message, context)
  }

  error(message: string, error: Error, context?: LogContext) {
    this.log('error', message, {
      ...context,
      error: error.message,
      stack: error.stack
    })
  }
}

const logger = new Logger()

// Usage
export async function GET(request: Request) {
  const requestId = crypto.randomUUID()

  logger.info('Fetching markets', {
    requestId,
    method: 'GET',
    path: '/api/markets'
  })

  try {
    const markets = await fetchMarkets()
    return NextResponse.json({ success: true, data: markets })
  } catch (error) {
    logger.error('Failed to fetch markets', error as Error, { requestId })
    return NextResponse.json({ error: 'Internal error' }, { status: 500 })
  }
}
```

**Remember**: Backend patterns enable scalable, maintainable server-side applications. Choose patterns that fit your complexity level.
