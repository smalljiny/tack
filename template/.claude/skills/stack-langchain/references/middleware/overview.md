# Middleware

A system for inserting logic before and after agent execution.

## Middleware Types

| Type | Timing | Use Case |
|------|--------|----------|
| `beforeModel` | Before LLM call | Input validation, prompt modification |
| `afterModel` | After LLM call | Output filtering, logging |
| `beforeToolCall` | Before tool execution | Permission check, input validation |
| `afterToolCall` | After tool execution | Result processing, auditing |

## Basic Middleware

```typescript
import { createReactAgent } from "@langchain/langgraph/prebuilt";

const loggingMiddleware = {
  beforeModel: async (messages, config) => {
    console.log("Input:", messages);
    return messages;  // Return modified or original
  },
  afterModel: async (response, config) => {
    console.log("Output:", response.content);
    return response;
  },
};

const agent = createReactAgent({
  llm: model,
  tools: [myTool],
  middleware: [loggingMiddleware],
});
```

## Built-in Middleware

### Rate Limiting

```typescript
import { rateLimitMiddleware } from "@langchain/langgraph";

const agent = createReactAgent({
  llm: model,
  tools,
  middleware: [
    rateLimitMiddleware({
      maxRequests: 10,
      windowMs: 60000,  // 1 minute
    }),
  ],
});
```

### Caching

```typescript
import { cacheMiddleware } from "@langchain/langgraph";

const agent = createReactAgent({
  llm: model,
  tools,
  middleware: [
    cacheMiddleware({
      ttl: 300000,  // 5 minutes
      maxSize: 100,
    }),
  ],
});
```

### Validation

```typescript
import { validationMiddleware } from "@langchain/langgraph";

const agent = createReactAgent({
  llm: model,
  tools,
  middleware: [
    validationMiddleware({
      maxInputLength: 10000,
      blockedPatterns: [/password/i, /secret/i],
    }),
  ],
});
```

## Custom Middleware Examples

### Content Filtering

```typescript
const contentFilterMiddleware = {
  afterModel: async (response, config) => {
    if (containsSensitiveContent(response.content)) {
      return {
        ...response,
        content: "[Content filtered]",
      };
    }
    return response;
  },
};
```

### Tool Permission

```typescript
const permissionMiddleware = {
  beforeToolCall: async (toolCall, state, config) => {
    const user = config.configurable?.user;
    const allowed = checkPermission(user, toolCall.name);

    if (!allowed) {
      return {
        block: true,
        message: "Permission denied",
      };
    }
    return { block: false };
  },
};
```

### Metrics Collection

```typescript
const metricsMiddleware = {
  beforeModel: async (messages, config) => {
    config.metrics = { startTime: Date.now() };
    return messages;
  },
  afterModel: async (response, config) => {
    const duration = Date.now() - config.metrics.startTime;
    recordMetric("model_latency", duration);
    return response;
  },
};
```

### Retry Logic

```typescript
const retryMiddleware = {
  afterModel: async (response, config, retry) => {
    if (response.content.includes("error")) {
      if (config.retryCount < 3) {
        return retry({ retryCount: (config.retryCount || 0) + 1 });
      }
    }
    return response;
  },
};
```

## Middleware Chain

```typescript
const agent = createReactAgent({
  llm: model,
  tools,
  middleware: [
    validationMiddleware,  // First
    loggingMiddleware,     // Second
    metricsMiddleware,     // Third
  ],
});
// Execution order: validation → logging → metrics
```

## Guardrails Pattern

```typescript
const guardrailsMiddleware = {
  beforeModel: async (messages, config) => {
    // Input guardrails
    const lastMessage = messages.at(-1);
    if (await isHarmful(lastMessage.content)) {
      throw new Error("Harmful content detected");
    }
    return messages;
  },
  afterModel: async (response, config) => {
    // Output guardrails
    if (await isHarmful(response.content)) {
      return {
        ...response,
        content: "I cannot provide that information.",
      };
    }
    return response;
  },
};
```
