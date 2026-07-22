# Long-Term Memory (Cross-thread)

Store data persistently across threads. User preferences, learned information, etc.

## Store Setup

```typescript
import { InMemoryStore } from "@langchain/langgraph";
import { MemorySaver } from "@langchain/langgraph";

const store = new InMemoryStore();
const checkpointer = new MemorySaver();

const agent = createReactAgent({
  llm: model,
  tools: [myTool],
  checkpointer,
  store,
});
```

## Core Operations

### Put (Write)

```typescript
await store.put(
  ["memories", "user-123"],  // namespace (array)
  "preferences",              // key
  { theme: "dark", lang: "en" }  // value
);
```

### Get (Read)

```typescript
const result = await store.get(
  ["memories", "user-123"],
  "preferences"
);
// { theme: "dark", lang: "en" }
```

### Search

```typescript
const results = await store.search(
  ["memories"],
  {
    filter: { lang: "en" },
    limit: 10,
  }
);
```

## Tool Integration

```typescript
import { tool } from "@langchain/core/tools";

const savePreference = tool(
  async ({ key, value }, config) => {
    const userId = config.configurable?.userId;
    const store = config.store;

    await store.put(["user", userId], key, { value });
    return `Saved ${key}`;
  },
  {
    name: "save_preference",
    description: "Save a user preference",
    schema: z.object({
      key: z.string(),
      value: z.string(),
    }),
  }
);

const getPreference = tool(
  async ({ key }, config) => {
    const userId = config.configurable?.userId;
    const store = config.store;

    const result = await store.get(["user", userId], key);
    return result?.value || "Not found";
  },
  {
    name: "get_preference",
    description: "Get a user preference",
    schema: z.object({
      key: z.string(),
    }),
  }
);
```

## Usage with Agent

```typescript
const result = await agent.invoke(
  { messages: [{ role: "user", content: "Remember I prefer dark mode" }] },
  {
    configurable: {
      thread_id: "thread-1",
      userId: "user-123",
    },
  }
);
```

## Namespace Patterns

```typescript
// Per-user
["users", userId, "preferences"]
["users", userId, "history"]

// Per-organization
["orgs", orgId, "settings"]
["orgs", orgId, "users", userId]

// Global
["global", "knowledge"]
```

## Vector Search (Semantic Memory)

```typescript
import { OpenAIEmbeddings } from "@langchain/openai";

const store = new InMemoryStore({
  index: {
    embeddings: new OpenAIEmbeddings(),
    dims: 1536,
  },
});

// Store with embedding
await store.put(["memories", "user-123"], "fact-1", {
  content: "User enjoys hiking",
});

// Semantic search
const results = await store.search(["memories", "user-123"], {
  query: "outdoor activities",
  limit: 5,
});
```

## Production Store

```typescript
import { PostgresStore } from "@langchain/langgraph-checkpoint-postgres";

const store = await PostgresStore.fromConnString(
  "postgresql://user:pass@localhost:5432/db"
);
```

## Deep Agent Backend (Alternative)

```typescript
import { createDeepAgent, CompositeBackend, StateBackend, StoreBackend } from "deepagents";

const agent = createDeepAgent({
  store: new InMemoryStore(),
  backend: (config) => new CompositeBackend(
    new StateBackend(config),  // Ephemeral
    { "/memories/": new StoreBackend(config) }  // Persistent
  ),
});

// Files in /memories/ persist across threads
// Files elsewhere are ephemeral to the thread
```
