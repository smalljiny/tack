# Short-Term Memory (Thread-based)

Maintain conversation context within a thread. Using the same thread_id remembers previous conversations.

## Basic Setup

```typescript
import { MemorySaver } from "@langchain/langgraph";
import { createReactAgent } from "@langchain/langgraph/prebuilt";

const checkpointer = new MemorySaver();

const agent = createReactAgent({
  llm: model,
  tools: [myTool],
  checkpointer,
});
```

## Usage with thread_id

```typescript
const config = { configurable: { thread_id: "user-123" } };

// First message
await agent.invoke(
  { messages: [{ role: "user", content: "My name is Alice" }] },
  config
);

// Second message (same thread - remembers context)
const result = await agent.invoke(
  { messages: [{ role: "user", content: "What's my name?" }] },
  config
);
// Response: "Your name is Alice"

// Different thread - no memory
const result2 = await agent.invoke(
  { messages: [{ role: "user", content: "What's my name?" }] },
  { configurable: { thread_id: "different-thread" } }
);
// Response: "I don't know your name"
```

## With StateGraph

```typescript
const graph = new StateGraph(AgentState)
  .addNode("agent", agentNode)
  .addEdge(START, "agent")
  .compile({ checkpointer: new MemorySaver() });

const result = await graph.invoke(input, {
  configurable: { thread_id: "thread-1" },
});
```

## Get Thread History

```typescript
const history = await checkpointer.list({
  configurable: { thread_id: "user-123" },
});

for await (const checkpoint of history) {
  console.log(checkpoint);
}
```

## Production Checkpointers

### PostgreSQL

```typescript
import { PostgresSaver } from "@langchain/langgraph-checkpoint-postgres";

const checkpointer = PostgresSaver.fromConnString(
  "postgresql://user:pass@localhost:5432/db"
);
```

### SQLite

```typescript
import { SqliteSaver } from "@langchain/langgraph-checkpoint-sqlite";

const checkpointer = SqliteSaver.fromConnString("./memory.db");
```

## Clearing Memory

```typescript
// Delete specific thread
await checkpointer.delete({ configurable: { thread_id: "user-123" } });
```

## Memory in Streaming

```typescript
const stream = agent.stream(
  { messages: [{ role: "user", content: "Hello" }] },
  {
    configurable: { thread_id: "user-123" },
    streamMode: "messages",
  }
);

for await (const [message, metadata] of stream) {
  process.stdout.write(message.content || "");
}
```

## Thread ID Patterns

```typescript
// Per-user threads
{ thread_id: `user-${userId}` }

// Per-conversation
{ thread_id: `conv-${conversationId}` }

// Per-session
{ thread_id: `session-${sessionId}` }
```
