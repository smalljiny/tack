# React Agent

LangGraph's prebuilt React Agent - the simplest tool-calling agent.

## Basic Usage

```typescript
import { ChatAnthropic } from "@langchain/anthropic";
import { createReactAgent } from "@langchain/langgraph/prebuilt";
import { tool } from "@langchain/core/tools";
import { z } from "zod";

const searchTool = tool(
  async ({ query }) => `Results for: ${query}`,
  {
    name: "search",
    description: "Search the web",
    schema: z.object({
      query: z.string().describe("Search query"),
    }),
  }
);

const model = new ChatAnthropic({ model: "claude-sonnet-4-20250514" });
const agent = createReactAgent({ llm: model, tools: [searchTool] });

const result = await agent.invoke({
  messages: [{ role: "user", content: "Search for LangChain" }],
});
```

## With Memory

```typescript
import { MemorySaver } from "@langchain/langgraph";

const checkpointer = new MemorySaver();
const agent = createReactAgent({
  llm: model,
  tools: [searchTool],
  checkpointer,
});

// Use thread_id for conversation persistence
const result = await agent.invoke(
  { messages: [{ role: "user", content: "Hello" }] },
  { configurable: { thread_id: "thread-1" } }
);
```

## With System Prompt

```typescript
const agent = createReactAgent({
  llm: model,
  tools: [searchTool],
  prompt: "You are a helpful research assistant. Always cite your sources.",
});
```

## With Long-Term Memory (Store)

```typescript
import { InMemoryStore } from "@langchain/langgraph";

const store = new InMemoryStore();
const agent = createReactAgent({
  llm: model,
  tools: [searchTool],
  checkpointer: new MemorySaver(),
  store,
});
```

## Streaming

```typescript
// Stream messages (token by token)
const stream = agent.stream(
  { messages: [{ role: "user", content: "Hello" }] },
  { streamMode: "messages" }
);

for await (const [message, metadata] of stream) {
  process.stdout.write(message.content || "");
}

// Stream updates (step by step)
for await (const update of agent.stream(input, { streamMode: "updates" })) {
  console.log(update);
}
```

## Error Handling

```typescript
try {
  const result = await agent.invoke({ messages });
} catch (error) {
  if (error instanceof GraphRecursionError) {
    console.log("Max iterations reached");
  }
}
```

## When to Use React Agent

- Simple tool-calling workflows
- Quick prototyping
- Standard request-response patterns

For complex workflows with custom control flow, use `StateGraph` directly.
See `agents/graph-basics.md`.
