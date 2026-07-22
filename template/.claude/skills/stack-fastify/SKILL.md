---
version: 2
name: stack-fastify
description: Fastify backend implementation guide. Use when developing backends with Fastify, implementing routes/plugins/hooks/validation logic. Includes reference documentation for Fastify patterns with TypeScript, error handling, and testing.
origin: SCE
capabilities: [language-patterns, typescript, fastify]
---

# Fastify Backend Implementation Guide

Guidelines and reference documentation for backend implementation using Fastify.

## When to Use This Skill

- Implementing Fastify applications
- Writing API routes, plugins, and hooks
- Implementing request/response validation and serialization
- Integrating TypeScript with Fastify
- Structuring Fastify monorepo services
- Writing Fastify tests

## Core Concepts

### Request Lifecycle

```text
Incoming Request
  │
  └─▶ Routing
        │
        └─▶ onRequest Hook
              │
              └─▶ preParsing Hook
                    │
                    └─▶ Parsing
                          │
                          └─▶ preValidation Hook
                                │
                                └─▶ Validation
                                      │
                                      └─▶ preHandler Hook
                                            │
                                            └─▶ User Handler
                                                  │
                                                  └─▶ preSerialization Hook
                                                        │
                                                        └─▶ onSend Hook
                                                              │
                                                              └─▶ onResponse Hook
```

### Basic Server Setup

```typescript
import Fastify from 'fastify'

const fastify = Fastify({
  logger: true
})

fastify.get('/', async (request, reply) => {
  return { hello: 'world' }
})

fastify.listen({ port: 3000 }, (err, address) => {
  if (err) {
    fastify.log.error(err)
    process.exit(1)
  }
})
```

### Route with Validation (TypeScript)

```typescript
import Fastify from 'fastify'
import { TypeBoxTypeProvider } from '@fastify/type-provider-typebox'
import { Type } from '@sinclair/typebox'

const fastify = Fastify().withTypeProvider<TypeBoxTypeProvider>()

fastify.post('/user', {
  schema: {
    body: Type.Object({
      name: Type.String(),
      email: Type.String({ format: 'email' })
    }),
    response: {
      200: Type.Object({
        id: Type.String(),
        name: Type.String()
      })
    }
  }
}, async (request, reply) => {
  const { name, email } = request.body
  return { id: 'generated-id', name }
})
```

### Plugin Pattern

```typescript
import fp from 'fastify-plugin'
import { FastifyInstance } from 'fastify'

async function myPlugin(fastify: FastifyInstance, options: { prefix?: string }) {
  fastify.decorate('myUtility', () => 'utility function')

  fastify.addHook('onRequest', async (request, reply) => {
    request.log.info('Request received')
  })
}

export default fp(myPlugin, {
  name: 'my-plugin',
  fastify: '5.x'
})
```

### Error Handling

```typescript
fastify.setErrorHandler(function (error, request, reply) {
  this.log.error(error)

  if (error.validation) {
    reply.status(400).send({
      error: 'Validation Error',
      message: error.message
    })
    return
  }

  reply.status(error.statusCode || 500).send({
    error: error.name,
    message: error.message
  })
})
```

## Reference Documentation

### Local References

| File | Contents |
|------|----------|
| `references/quick-reference.md` | Request/Reply objects, Route options, Hooks, Schema, Server options |
| `references/common-patterns.md` | Plugin, TypeScript, Error Handling, Auth, Testing, DB patterns |

### Context7 MCP (Detailed Documentation)

Use **Context7 MCP** when detailed official documentation is needed.

```text
1. Search "fastify" with mcp__context7__resolve-library-id
2. Query needed content with mcp__context7__query-docs
```

**Search Query Keywords:**

| Topic | Example Query |
|-------|---------------|
| Routes | `fastify routes URL parameters schema` |
| Hooks | `fastify hooks onRequest preHandler lifecycle` |
| Plugins | `fastify plugin register encapsulation` |
| TypeScript | `fastify typescript type provider typebox` |
| Validation | `fastify validation JSON schema ajv` |
| Error Handling | `fastify error handler setErrorHandler` |
| Testing | `fastify testing inject` |
| Server Config | `fastify server options logger trustProxy` |

## Common Patterns

### Registering Routes with Prefix

```typescript
fastify.register(async function userRoutes(fastify) {
  fastify.get('/', async () => ({ users: [] }))
  fastify.get('/:id', async (request) => {
    const { id } = request.params as { id: string }
    return { id }
  })
}, { prefix: '/users' })
```

### Request Decorator with Proper Typing

```typescript
declare module 'fastify' {
  interface FastifyRequest {
    user: { id: string; name: string } | null
  }
}

fastify.decorateRequest('user', null)

fastify.addHook('preHandler', async (request) => {
  const token = request.headers.authorization
  if (token) {
    request.user = { id: '1', name: 'User' }
  }
})
```

### Shared Schema with $ref

```typescript
fastify.addSchema({
  $id: 'User',
  type: 'object',
  properties: {
    id: { type: 'string' },
    name: { type: 'string' },
    email: { type: 'string', format: 'email' }
  }
})

fastify.post('/users', {
  schema: {
    body: { $ref: 'User#' },
    response: {
      201: { $ref: 'User#' }
    }
  }
}, handler)
```

### Graceful Shutdown

```typescript
const signals = ['SIGINT', 'SIGTERM']

for (const signal of signals) {
  process.on(signal, async () => {
    fastify.log.info(`Received ${signal}, closing server...`)
    await fastify.close()
    process.exit(0)
  })
}
```

## Testing

```typescript
import { test } from 'node:test'
import assert from 'node:assert'
import Fastify from 'fastify'
import myPlugin from '../src/plugin'

test('GET / returns hello world', async () => {
  const fastify = Fastify()
  await fastify.register(myPlugin)

  const response = await fastify.inject({
    method: 'GET',
    url: '/'
  })

  assert.strictEqual(response.statusCode, 200)
  assert.deepStrictEqual(response.json(), { hello: 'world' })
})
```
