# Quickstart

## 1. Simple Chat

```typescript
import { ChatAnthropic } from "@langchain/anthropic";

const model = new ChatAnthropic({ model: "claude-sonnet-4-20250514" });
const response = await model.invoke("What is LangChain?");
console.log(response.content);
```

## 2. React Agent with Tools

```typescript
import { ChatAnthropic } from "@langchain/anthropic";
import { createReactAgent } from "@langchain/langgraph/prebuilt";
import { tool } from "@langchain/core/tools";
import { z } from "zod";

// Define a tool
const weatherTool = tool(
  async ({ city }) => `Weather in ${city}: Sunny, 22°C`,
  {
    name: "get_weather",
    description: "Get weather for a city",
    schema: z.object({
      city: z.string().describe("City name"),
    }),
  }
);

// Create agent
const model = new ChatAnthropic({ model: "claude-sonnet-4-20250514" });
const agent = createReactAgent({ llm: model, tools: [weatherTool] });

// Invoke
const result = await agent.invoke({
  messages: [{ role: "user", content: "What's the weather in Tokyo?" }],
});
console.log(result.messages.at(-1).content);
```

## 3. StateGraph (LangGraph)

```typescript
import { StateGraph, START, END, Annotation } from "@langchain/langgraph";
import { BaseMessage } from "@langchain/core/messages";

// Define state
const AgentState = Annotation.Root({
  messages: Annotation<BaseMessage[]>({
    reducer: (x, y) => x.concat(y),
  }),
});

// Define nodes
async function chatNode(state: typeof AgentState.State) {
  const model = new ChatAnthropic({ model: "claude-sonnet-4-20250514" });
  const response = await model.invoke(state.messages);
  return { messages: [response] };
}

// Build graph
const graph = new StateGraph(AgentState)
  .addNode("chat", chatNode)
  .addEdge(START, "chat")
  .addEdge("chat", END)
  .compile();

// Run
const result = await graph.invoke({
  messages: [{ role: "user", content: "Hello!" }],
});
```

## 4. With Memory (Conversation Persistence)

```typescript
import { MemorySaver } from "@langchain/langgraph";

const memory = new MemorySaver();
const agent = createReactAgent({
  llm: model,
  tools: [weatherTool],
  checkpointer: memory,
});

// First message
await agent.invoke(
  { messages: [{ role: "user", content: "My name is Alice" }] },
  { configurable: { thread_id: "user-123" } }
);

// Second message (remembers context)
const result = await agent.invoke(
  { messages: [{ role: "user", content: "What's my name?" }] },
  { configurable: { thread_id: "user-123" } }
);
// "Your name is Alice"
```

## 5. Streaming

```typescript
const stream = agent.stream(
  { messages: [{ role: "user", content: "Tell me a joke" }] },
  { streamMode: "messages" }
);

for await (const [message, metadata] of stream) {
  if (message.content) {
    process.stdout.write(message.content);
  }
}
```

## Next Steps

- Agent patterns: `agents/react-agent.md`, `agents/graph-basics.md`
- Memory: `memory/short-term.md`, `memory/long-term.md`
- Streaming: `streaming/modes.md`
