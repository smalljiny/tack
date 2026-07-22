# Fastify Common Patterns

Collection of frequently used code patterns and snippets.

## Plugin Patterns

### Basic Plugin Structure

```typescript
import fp from 'fastify-plugin'
import { FastifyInstance, FastifyPluginOptions } from 'fastify'

interface MyPluginOptions extends FastifyPluginOptions {
  prefix?: string
  enabled?: boolean
}

async function myPlugin(
  fastify: FastifyInstance,
  options: MyPluginOptions
) {
  const { prefix = '/api', enabled = true } = options

  if (!enabled) return

  // Add decorator
  fastify.decorate('myUtil', () => 'utility')

  // Add hook
  fastify.addHook('onRequest', async (request) => {
    request.log.info('Plugin hook triggered')
  })

  // Add route
  fastify.get(`${prefix}/health`, async () => ({ status: 'ok' }))
}

// Skip encapsulation (accessible from parent scope)
export default fp(myPlugin, {
  name: 'my-plugin',
  fastify: '5.x',
  dependencies: []  // Dependent plugin names
})
```

### Route Plugin (Encapsulated)

```typescript
import { FastifyInstance } from 'fastify'

// Export without fp() - keeps encapsulation
export async function userRoutes(fastify: FastifyInstance) {
  fastify.get('/', async () => {
    return { users: [] }
  })

  fastify.get('/:id', async (request) => {
    const { id } = request.params as { id: string }
    return { id }
  })

  fastify.post('/', {
    schema: {
      body: {
        type: 'object',
        required: ['name'],
        properties: {
          name: { type: 'string' }
        }
      }
    }
  }, async (request) => {
    const { name } = request.body as { name: string }
    return { id: 'new-id', name }
  })
}

// Registration
fastify.register(userRoutes, { prefix: '/users' })
```

### Service Plugin (Dependency Injection)

```typescript
import fp from 'fastify-plugin'
import { FastifyInstance } from 'fastify'

// Service interface
interface UserService {
  findById(id: string): Promise<User | null>
  create(data: CreateUserDto): Promise<User>
}

// Type augmentation
declare module 'fastify' {
  interface FastifyInstance {
    userService: UserService
  }
}

async function userServicePlugin(fastify: FastifyInstance) {
  const service: UserService = {
    async findById(id) {
      // DB query logic
      return null
    },
    async create(data) {
      // Creation logic
      return { id: 'new', ...data }
    }
  }

  fastify.decorate('userService', service)
}

export default fp(userServicePlugin, {
  name: 'user-service'
})
```

## TypeScript Patterns

### Request/Reply Generic Types

```typescript
interface CreateUserBody {
  name: string
  email: string
}

interface UserParams {
  id: string
}

interface UserQuery {
  include?: string
}

interface UserResponse {
  id: string
  name: string
  email: string
}

fastify.post<{
  Body: CreateUserBody
  Reply: UserResponse
}>('/users', async (request, reply) => {
  const { name, email } = request.body  // Type inferred
  return { id: 'new', name, email }
})

fastify.get<{
  Params: UserParams
  Querystring: UserQuery
  Reply: UserResponse
}>('/users/:id', async (request) => {
  const { id } = request.params
  const { include } = request.query
  return { id, name: 'User', email: 'user@example.com' }
})
```

### TypeBox Type Provider

```typescript
import Fastify from 'fastify'
import { TypeBoxTypeProvider } from '@fastify/type-provider-typebox'
import { Type, Static } from '@sinclair/typebox'

const CreateUserSchema = Type.Object({
  name: Type.String({ minLength: 1 }),
  email: Type.String({ format: 'email' })
})

const UserSchema = Type.Object({
  id: Type.String(),
  name: Type.String(),
  email: Type.String()
})

type CreateUser = Static<typeof CreateUserSchema>
type User = Static<typeof UserSchema>

const fastify = Fastify().withTypeProvider<TypeBoxTypeProvider>()

fastify.post('/users', {
  schema: {
    body: CreateUserSchema,
    response: { 201: UserSchema }
  }
}, async (request) => {
  // request.body is automatically typed as CreateUser
  const { name, email } = request.body
  return { id: 'new', name, email }
})
```

### Request Decorator with Types

```typescript
interface UserPayload {
  id: string
  name: string
  roles: string[]
}

declare module 'fastify' {
  interface FastifyRequest {
    user: UserPayload | null
  }
}

// Initial value is null (objects/functions use null, strings use '', numbers use 0)
fastify.decorateRequest('user', null)

fastify.addHook('preHandler', async (request) => {
  const token = request.headers.authorization?.replace('Bearer ', '')
  if (token) {
    request.user = await verifyToken(token)
  }
})

fastify.get('/profile', async (request, reply) => {
  if (!request.user) {
    return reply.code(401).send({ error: 'Unauthorized' })
  }
  return { user: request.user }
})
```

## Error Handling Patterns

### Global Error Handler

```typescript
import { FastifyError } from 'fastify'

fastify.setErrorHandler((error: FastifyError, request, reply) => {
  request.log.error(error)

  // Validation error
  if (error.validation) {
    return reply.status(400).send({
      error: 'Validation Error',
      message: 'Invalid request data',
      details: error.validation
    })
  }

  // Custom error
  if (error.statusCode) {
    return reply.status(error.statusCode).send({
      error: error.name,
      message: error.message
    })
  }

  // Server error
  reply.status(500).send({
    error: 'Internal Server Error',
    message: 'Something went wrong'
  })
})
```

### Custom Error Classes

```typescript
import createError from '@fastify/error'

// Define custom errors
const NotFoundError = createError('NOT_FOUND', '%s not found', 404)
const UnauthorizedError = createError('UNAUTHORIZED', 'Authentication required', 401)
const ForbiddenError = createError('FORBIDDEN', 'Access denied', 403)
const ConflictError = createError('CONFLICT', '%s already exists', 409)

// Usage
fastify.get('/users/:id', async (request, reply) => {
  const { id } = request.params as { id: string }
  const user = await userService.findById(id)

  if (!user) {
    throw new NotFoundError('User')
  }

  return user
})
```

### Error Handler per Plugin

```typescript
fastify.register(async function apiRoutes(app) {
  // Handle errors only within this plugin
  app.setErrorHandler((error, request, reply) => {
    if (error.statusCode === 404) {
      return reply.status(404).send({
        error: 'Resource Not Found',
        path: request.url
      })
    }
    throw error  // Propagate to parent error handler
  })

  app.get('/resource/:id', async (request) => {
    // ...
  })
}, { prefix: '/api' })
```

## Authentication Patterns

### JWT Auth Hook

```typescript
import fp from 'fastify-plugin'
import jwt from '@fastify/jwt'

declare module '@fastify/jwt' {
  interface FastifyJWT {
    payload: { userId: string; roles: string[] }
    user: { userId: string; roles: string[] }
  }
}

async function authPlugin(fastify: FastifyInstance) {
  await fastify.register(jwt, {
    secret: process.env.JWT_SECRET!
  })

  fastify.decorate('authenticate', async function(request, reply) {
    try {
      await request.jwtVerify()
    } catch (err) {
      reply.status(401).send({ error: 'Unauthorized' })
    }
  })
}

export default fp(authPlugin)

// Usage
fastify.get('/protected', {
  preHandler: [fastify.authenticate]
}, async (request) => {
  return { user: request.user }
})
```

### Role-Based Access Control

```typescript
function requireRoles(...roles: string[]) {
  return async function(request: FastifyRequest, reply: FastifyReply) {
    if (!request.user) {
      return reply.status(401).send({ error: 'Unauthorized' })
    }

    const hasRole = roles.some(role => request.user!.roles.includes(role))
    if (!hasRole) {
      return reply.status(403).send({ error: 'Forbidden' })
    }
  }
}

fastify.get('/admin', {
  preHandler: [fastify.authenticate, requireRoles('admin')]
}, async () => {
  return { admin: true }
})
```

## Testing Patterns

### Basic Test with inject()

```typescript
import { test, describe, beforeEach, afterEach } from 'node:test'
import assert from 'node:assert'
import Fastify, { FastifyInstance } from 'fastify'
import { app } from '../src/app'

describe('User API', () => {
  let fastify: FastifyInstance

  beforeEach(async () => {
    fastify = Fastify()
    await fastify.register(app)
    await fastify.ready()
  })

  afterEach(async () => {
    await fastify.close()
  })

  test('GET /users returns empty array', async () => {
    const response = await fastify.inject({
      method: 'GET',
      url: '/users'
    })

    assert.strictEqual(response.statusCode, 200)
    assert.deepStrictEqual(response.json(), { users: [] })
  })

  test('POST /users creates user', async () => {
    const response = await fastify.inject({
      method: 'POST',
      url: '/users',
      payload: { name: 'John', email: 'john@example.com' },
      headers: { 'content-type': 'application/json' }
    })

    assert.strictEqual(response.statusCode, 201)
    const body = response.json()
    assert.ok(body.id)
    assert.strictEqual(body.name, 'John')
  })

  test('GET /users/:id returns 404 for non-existent user', async () => {
    const response = await fastify.inject({
      method: 'GET',
      url: '/users/non-existent-id'
    })

    assert.strictEqual(response.statusCode, 404)
  })
})
```

### Testing with Authentication

```typescript
test('protected route requires auth', async () => {
  const response = await fastify.inject({
    method: 'GET',
    url: '/protected'
  })

  assert.strictEqual(response.statusCode, 401)
})

test('protected route works with valid token', async () => {
  const token = fastify.jwt.sign({ userId: '123', roles: ['user'] })

  const response = await fastify.inject({
    method: 'GET',
    url: '/protected',
    headers: {
      authorization: `Bearer ${token}`
    }
  })

  assert.strictEqual(response.statusCode, 200)
})
```

### Mocking Dependencies

```typescript
import { test, mock } from 'node:test'

test('user service returns mocked data', async () => {
  const fastify = Fastify()

  // Mock service
  const mockUserService = {
    findById: mock.fn(async (id: string) => ({
      id,
      name: 'Mock User',
      email: 'mock@example.com'
    }))
  }

  fastify.decorate('userService', mockUserService)
  await fastify.register(userRoutes)

  const response = await fastify.inject({
    method: 'GET',
    url: '/users/123'
  })

  assert.strictEqual(response.statusCode, 200)
  assert.strictEqual(mockUserService.findById.mock.calls.length, 1)

  await fastify.close()
})
```

## Database Patterns

### MongoDB Plugin

```typescript
import fp from 'fastify-plugin'
import { MongoClient, Db } from 'mongodb'

declare module 'fastify' {
  interface FastifyInstance {
    mongo: {
      client: MongoClient
      db: Db
    }
  }
}

async function mongoPlugin(fastify: FastifyInstance, options: { uri: string; dbName: string }) {
  const client = new MongoClient(options.uri)
  await client.connect()

  const db = client.db(options.dbName)

  fastify.decorate('mongo', { client, db })

  fastify.addHook('onClose', async () => {
    await client.close()
  })
}

export default fp(mongoPlugin, { name: 'mongodb' })
```

### Repository Pattern

```typescript
import { Collection, ObjectId } from 'mongodb'

interface User {
  _id?: ObjectId
  name: string
  email: string
  createdAt: Date
}

class UserRepository {
  constructor(private collection: Collection<User>) {}

  async findById(id: string): Promise<User | null> {
    return this.collection.findOne({ _id: new ObjectId(id) })
  }

  async findByEmail(email: string): Promise<User | null> {
    return this.collection.findOne({ email })
  }

  async create(data: Omit<User, '_id' | 'createdAt'>): Promise<User> {
    const user = { ...data, createdAt: new Date() }
    const result = await this.collection.insertOne(user)
    return { ...user, _id: result.insertedId }
  }

  async update(id: string, data: Partial<User>): Promise<boolean> {
    const result = await this.collection.updateOne(
      { _id: new ObjectId(id) },
      { $set: data }
    )
    return result.modifiedCount > 0
  }

  async delete(id: string): Promise<boolean> {
    const result = await this.collection.deleteOne({ _id: new ObjectId(id) })
    return result.deletedCount > 0
  }
}
```

## Graceful Shutdown

```typescript
const fastify = Fastify({ logger: true })

// Register app
await fastify.register(app)

// Graceful shutdown setup
const signals = ['SIGINT', 'SIGTERM'] as const

for (const signal of signals) {
  process.on(signal, async () => {
    fastify.log.info(`Received ${signal}, closing server...`)

    try {
      await fastify.close()
      fastify.log.info('Server closed successfully')
      process.exit(0)
    } catch (err) {
      fastify.log.error(err, 'Error during shutdown')
      process.exit(1)
    }
  })
}

// Start server
try {
  await fastify.listen({ port: 3000, host: '0.0.0.0' })
} catch (err) {
  fastify.log.error(err)
  process.exit(1)
}
```

## Middleware Compatibility

### Using Express Middleware

```typescript
import middie from '@fastify/middie'
import cors from 'cors'
import helmet from 'helmet'

await fastify.register(middie)

// Use Express middleware
fastify.use(cors())
fastify.use(helmet())

// Apply to specific path only
fastify.use('/api', someExpressMiddleware)
```

## Content Type Parsers

### Custom JSON Parser

```typescript
fastify.addContentTypeParser(
  'application/json',
  { parseAs: 'string' },
  (request, body, done) => {
    try {
      const json = JSON.parse(body as string)
      done(null, json)
    } catch (err) {
      done(err as Error, undefined)
    }
  }
)
```

### File Upload with multipart

```typescript
import multipart from '@fastify/multipart'

await fastify.register(multipart, {
  limits: {
    fileSize: 10 * 1024 * 1024  // 10MB
  }
})

fastify.post('/upload', async (request) => {
  const file = await request.file()

  if (!file) {
    throw new Error('No file uploaded')
  }

  const buffer = await file.toBuffer()

  return {
    filename: file.filename,
    mimetype: file.mimetype,
    size: buffer.length
  }
})
```
