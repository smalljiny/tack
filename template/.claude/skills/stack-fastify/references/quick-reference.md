# Fastify Quick Reference

Quick reference for core APIs and options.

## Request Object

```typescript
interface FastifyRequest {
  // Data
  body: unknown           // Parsed request body
  query: unknown          // Parsed querystring
  params: unknown         // URL parameters
  headers: IncomingHttpHeaders

  // Metadata
  id: string              // Request ID
  ip: string              // Client IP
  ips: string[]           // X-Forwarded-For IP list
  host: string            // Host header
  hostname: string        // Hostname
  port: number            // Port
  protocol: 'http' | 'https'
  method: string          // HTTP method
  url: string             // Request URL
  originalUrl: string     // Original URL (before rerouting)

  // References
  raw: IncomingMessage    // Node.js raw request
  server: FastifyInstance // Fastify instance
  log: FastifyBaseLogger  // Logger

  // Route info
  routeOptions: {
    method: string
    url: string
    bodyLimit: number
    config: RouteConfig
    schema: RouteSchema
    handler: RouteHandler
  }

  // Validation methods
  getValidationFunction(schema | httpPart): ValidationFunction
  compileValidationSchema(schema, httpPart?): ValidationFunction
  validateInput(data, schema | httpPart): boolean
}
```

## Reply Object

```typescript
interface FastifyReply {
  // Status code
  code(statusCode: number): this
  status(statusCode: number): this  // Alias for code()
  statusCode: number                // getter/setter

  // Headers
  header(key: string, value: string): this
  headers(obj: Record<string, string>): this
  getHeader(key: string): string
  getHeaders(): Record<string, string>
  hasHeader(key: string): boolean
  removeHeader(key: string): this
  type(contentType: string): this   // Set Content-Type

  // Send response
  send(payload?: unknown): this
  redirect(url: string, code?: number): this

  // Serialization
  serialize(payload: unknown): string
  serializer(fn: (payload: unknown) => string): this

  // References
  raw: ServerResponse      // Node.js raw response
  server: FastifyInstance
  request: FastifyRequest
  log: FastifyBaseLogger

  // State
  sent: boolean            // Response sent flag
  elapsedTime: number      // Request processing time (ms)

  // Advanced
  hijack(): this           // Interrupt lifecycle
  callNotFound(): void     // Call 404 handler
}
```

## Route Options

```typescript
fastify.route({
  // Required
  method: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH' | 'OPTIONS' | 'HEAD',
  url: '/path/:param',
  handler: (request, reply) => {},

  // Schema (validation & serialization)
  schema: {
    body: JSONSchema,
    querystring: JSONSchema,  // or query
    params: JSONSchema,
    headers: JSONSchema,
    response: {
      200: JSONSchema,
      '4xx': JSONSchema
    }
  },

  // Route hooks (can be arrays)
  onRequest: (request, reply, done) => {},
  preParsing: (request, reply, payload, done) => {},
  preValidation: (request, reply, done) => {},
  preHandler: (request, reply, done) => {},
  preSerialization: (request, reply, payload, done) => {},
  onSend: (request, reply, payload, done) => {},
  onResponse: (request, reply, done) => {},
  onError: (request, reply, error, done) => {},
  onTimeout: (request, reply, done) => {},

  // Options
  bodyLimit: 1048576,        // Body size limit (default 1MB)
  logLevel: 'info',          // Route-specific log level
  config: {},                // Custom config
  errorHandler: (error, request, reply) => {},

  // Constraints
  constraints: {
    version: '1.0.0',        // Accept-Version header matching
    host: 'api.example.com'  // Host header matching (RegExp allowed)
  },

  // Other
  attachValidation: false,   // Attach validation error to request
  exposeHeadRoute: true,     // Create HEAD route for GET
  prefixTrailingSlash: 'both' // 'both' | 'slash' | 'no-slash'
})
```

## Hooks Lifecycle

```text
Incoming Request
  │
  └─▶ Routing
        │
        └─▶ onRequest        # Right after request received
              │
              └─▶ preParsing     # Before body parsing (stream transform)
                    │
                    └─▶ Parsing
                          │
                          └─▶ preValidation  # Before validation (body modifiable)
                                │
                                └─▶ Validation
                                      │
                                      └─▶ preHandler   # Before handler execution
                                            │
                                            └─▶ User Handler
                                                  │
                                                  └─▶ preSerialization  # Before serialization
                                                        │
                                                        └─▶ onSend      # Before response sent
                                                              │
                                                              └─▶ onResponse  # After response sent
```

### Hook Signatures

```typescript
// Basic hooks
fastify.addHook('onRequest', async (request, reply) => {})
fastify.addHook('preValidation', async (request, reply) => {})
fastify.addHook('preHandler', async (request, reply) => {})
fastify.addHook('onResponse', async (request, reply) => {})
fastify.addHook('onTimeout', async (request, reply) => {})
fastify.addHook('onRequestAbort', async (request) => {})

// Payload hooks
fastify.addHook('preParsing', async (request, reply, payload) => {
  return newPayload  // Return stream
})
fastify.addHook('preSerialization', async (request, reply, payload) => {
  return newPayload  // Return modified payload
})
fastify.addHook('onSend', async (request, reply, payload) => {
  return newPayload  // string | Buffer | stream | null
})

// Error hook
fastify.addHook('onError', async (request, reply, error) => {
  // Logging only, cannot call reply.send
})

// Application hooks
fastify.addHook('onReady', async () => {})     // Server ready to start
fastify.addHook('onListen', async () => {})   // After listen() called
fastify.addHook('onClose', async () => {})    // On close() call
fastify.addHook('onRoute', (routeOptions) => {})  // On route registration
fastify.addHook('onRegister', (instance, opts) => {})  // On plugin registration
```

## Schema Validation

### JSON Schema Basics

```typescript
const schema = {
  body: {
    type: 'object',
    required: ['name', 'email'],
    properties: {
      name: { type: 'string', minLength: 1 },
      email: { type: 'string', format: 'email' },
      age: { type: 'integer', minimum: 0 },
      tags: {
        type: 'array',
        items: { type: 'string' },
        maxItems: 5
      },
      status: {
        type: 'string',
        enum: ['active', 'inactive']
      }
    },
    additionalProperties: false
  },
  querystring: {
    type: 'object',
    properties: {
      page: { type: 'integer', default: 1 },
      limit: { type: 'integer', default: 10 }
    }
  },
  params: {
    type: 'object',
    properties: {
      id: { type: 'string', pattern: '^[0-9a-fA-F]{24}$' }
    }
  },
  response: {
    200: {
      type: 'object',
      properties: {
        id: { type: 'string' },
        name: { type: 'string' }
      }
    }
  }
}
```

### Shared Schema with $ref

```typescript
// Register schema
fastify.addSchema({
  $id: 'User',
  type: 'object',
  properties: {
    id: { type: 'string' },
    name: { type: 'string' },
    email: { type: 'string', format: 'email' }
  }
})

// Use reference
fastify.post('/users', {
  schema: {
    body: { $ref: 'User#' },
    response: {
      201: { $ref: 'User#' }
    }
  }
}, handler)

// Get schemas
const schemas = fastify.getSchemas()
const userSchema = fastify.getSchema('User')
```

## Server Options

```typescript
const fastify = Fastify({
  // Logging
  logger: true,  // or pino options object
  disableRequestLogging: false,

  // Security
  trustProxy: false,  // Trust X-Forwarded-* headers

  // Parsing
  bodyLimit: 1048576,  // 1MB
  caseSensitive: true,
  ignoreTrailingSlash: false,
  ignoreDuplicateSlashes: false,

  // Timeouts
  connectionTimeout: 0,
  keepAliveTimeout: 72000,

  // HTTP/2
  http2: false,
  https: null,

  // Advanced
  maxParamLength: 100,
  onProtoPoisoning: 'error',
  onConstructorPoisoning: 'error',

  // Custom
  genReqId: (req) => uuid(),
  requestIdHeader: 'request-id',
  requestIdLogLabel: 'reqId'
})
```

## Server Instance Methods

```typescript
// Server control
await fastify.listen({ port: 3000, host: '0.0.0.0' })
await fastify.close()
await fastify.ready()

// Route registration
fastify.get(url, opts?, handler)
fastify.post(url, opts?, handler)
fastify.put(url, opts?, handler)
fastify.delete(url, opts?, handler)
fastify.patch(url, opts?, handler)
fastify.options(url, opts?, handler)
fastify.all(url, opts?, handler)
fastify.route(routeOptions)

// Plugins
fastify.register(plugin, opts?)
fastify.after(callback?)

// Decorators
fastify.decorate(name, value, deps?)
fastify.decorateRequest(name, value, deps?)
fastify.decorateReply(name, value, deps?)
fastify.hasDecorator(name)
fastify.hasRequestDecorator(name)
fastify.hasReplyDecorator(name)

// Hooks
fastify.addHook(hookName, hookHandler)

// Schema
fastify.addSchema(schema)
fastify.getSchemas()
fastify.getSchema(id)

// Error handling
fastify.setErrorHandler((error, request, reply) => {})
fastify.setNotFoundHandler(opts?, handler)

// Content type
fastify.addContentTypeParser(contentType, opts, parser)
fastify.hasContentTypeParser(contentType)
fastify.removeContentTypeParser(contentType | contentTypes[])
fastify.removeAllContentTypeParsers()

// Testing
const response = await fastify.inject({ method, url, payload?, headers? })

// Debug output
fastify.printRoutes()
fastify.printPlugins()
```

## Error Codes

```typescript
import { errorCodes } from 'fastify'

// Common error codes
errorCodes.FST_ERR_BAD_URL           // Invalid URL
errorCodes.FST_ERR_MISSING_MIDDLEWARE  // Missing middleware
errorCodes.FST_ERR_DUPLICATED_ROUTE    // Duplicate route
errorCodes.FST_ERR_REP_ALREADY_SENT    // Response already sent
errorCodes.FST_ERR_HOOK_INVALID_TYPE   // Invalid hook type
errorCodes.FST_ERR_DEC_ALREADY_PRESENT // Duplicate decorator
errorCodes.FST_ERR_VALIDATION          // Validation failed
```
