# Persistence

Saving and restoring graph state.

## Checkpointer Basics

```typescript
import { MemorySaver } from "@langchain/langgraph";

const checkpointer = new MemorySaver();
const graph = workflow.compile({ checkpointer });

// State automatically saved after each step
const result = await graph.invoke(input, {
  configurable: { thread_id: "thread-1" },
});
```

## Production Checkpointers

### PostgreSQL

```typescript
import { PostgresSaver } from "@langchain/langgraph-checkpoint-postgres";

const checkpointer = PostgresSaver.fromConnString(
  "postgresql://user:pass@localhost:5432/db"
);

const graph = workflow.compile({ checkpointer });
```

### SQLite

```typescript
import { SqliteSaver } from "@langchain/langgraph-checkpoint-sqlite";

const checkpointer = SqliteSaver.fromConnString("./checkpoints.db");
```

## Checkpoint Operations

### Get State

```typescript
const state = await graph.getState({
  configurable: { thread_id: "thread-1" },
});

console.log(state.values);  // Current state
console.log(state.next);    // Next node(s) to execute
```

### Get History

```typescript
const history = await graph.getStateHistory({
  configurable: { thread_id: "thread-1" },
});

for await (const checkpoint of history) {
  console.log(checkpoint.checkpoint_id);
  console.log(checkpoint.values);
}
```

### Update State

```typescript
await graph.updateState(
  { configurable: { thread_id: "thread-1" } },
  { messages: [new AIMessage("Updated")] }
);
```

### Resume from Checkpoint

```typescript
// Get specific checkpoint
const state = await graph.getState({
  configurable: {
    thread_id: "thread-1",
    checkpoint_id: "checkpoint-abc",
  },
});

// Resume from that point
const result = await graph.invoke(null, {
  configurable: {
    thread_id: "thread-1",
    checkpoint_id: "checkpoint-abc",
  },
});
```

## Thread Management

### List Threads

```typescript
const threads = await checkpointer.list({});

for await (const thread of threads) {
  console.log(thread.thread_id);
}
```

### Delete Thread

```typescript
await checkpointer.delete({
  configurable: { thread_id: "thread-1" },
});
```

## Store (Long-term Memory)

```typescript
import { InMemoryStore, PostgresStore } from "@langchain/langgraph";

// Development
const store = new InMemoryStore();

// Production
const store = await PostgresStore.fromConnString(connectionString);

const graph = workflow.compile({
  checkpointer,
  store,
});
```

## Namespace Patterns

```typescript
// Per-user data
await store.put(["users", userId], "preferences", data);

// Per-organization
await store.put(["orgs", orgId, "users", userId], "profile", data);

// Shared knowledge
await store.put(["global", "knowledge"], "facts", data);
```

## Error Recovery

```typescript
try {
  await graph.invoke(input, config);
} catch (error) {
  // Get last successful state
  const state = await graph.getState(config);

  if (state.next.length > 0) {
    // Resume from last checkpoint
    await graph.invoke(null, config);
  }
}
```

## Checkpoint Metadata

```typescript
const result = await graph.invoke(input, {
  configurable: {
    thread_id: "thread-1",
    checkpoint_ns: "production",
  },
  metadata: {
    user_id: "user-123",
    session_id: "session-abc",
  },
});
```
