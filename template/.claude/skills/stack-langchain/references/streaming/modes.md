# Streaming Modes

Streaming modes for real-time output.

## Stream Modes Overview

| Mode | Description | Use Case |
|------|-------------|----------|
| `values` | Full state after each step | Progress tracking |
| `updates` | State delta after each step | Incremental updates |
| `messages` | Token-by-token LLM output | Chat UI |
| `custom` | User-defined events | Progress bars |
| `debug` | Detailed execution info | Debugging |

## Basic Usage

```typescript
for await (const chunk of await graph.stream(input, {
  streamMode: "updates",
})) {
  console.log(chunk);
}
```

## Messages Mode (Token Streaming)

```typescript
const stream = agent.stream(
  { messages: [{ role: "user", content: "Tell me a story" }] },
  { streamMode: "messages" }
);

for await (const [message, metadata] of stream) {
  if (message.content) {
    process.stdout.write(message.content);
  }
}
```

### Filter by Node

```typescript
for await (const [msg, metadata] of stream) {
  if (metadata.langgraph_node === "writer") {
    process.stdout.write(msg.content || "");
  }
}
```

### Filter by Tag

```typescript
const model = new ChatOpenAI({ tags: ["main-response"] });

for await (const [msg, metadata] of stream) {
  if (metadata.tags?.includes("main-response")) {
    process.stdout.write(msg.content || "");
  }
}
```

## Updates Mode (Step-by-step)

```typescript
for await (const update of agent.stream(input, { streamMode: "updates" })) {
  // { nodeName: { stateKey: newValue } }
  console.log("Step:", update);
}
```

## Values Mode (Full State)

```typescript
for await (const state of agent.stream(input, { streamMode: "values" })) {
  console.log("Current state:", state);
}
```

## Custom Mode (User Events)

```typescript
// In node or tool
const myNode = async (state, config) => {
  config.writer({ type: "progress", value: 25 });
  // ... do work
  config.writer({ type: "progress", value: 75 });
  return { result: "done" };
};

// Consume
for await (const event of graph.stream(input, { streamMode: "custom" })) {
  if (event.type === "progress") {
    console.log(`Progress: ${event.value}%`);
  }
}
```

## Multiple Modes

```typescript
const stream = agent.stream(input, {
  streamMode: ["updates", "messages"],
});

for await (const [mode, chunk] of stream) {
  if (mode === "messages") {
    process.stdout.write(chunk.content || "");
  } else if (mode === "updates") {
    console.log("Update:", chunk);
  }
}
```

## Stream from Subgraphs

```typescript
for await (const chunk of graph.stream(input, {
  streamMode: "updates",
  subgraphs: true,
})) {
  // [namespace, data]
  // namespace: path to subgraph node
  console.log(chunk);
}
```

## Stream Events API (Alternative)

```typescript
const stream = agent.streamEvents(
  { messages: [{ role: "user", content: "Hello" }] },
  { version: "v2" }
);

for await (const event of stream) {
  switch (event.event) {
    case "on_chat_model_start":
      console.log("Model starting...");
      break;
    case "on_chat_model_stream":
      process.stdout.write(event.data.chunk.content || "");
      break;
    case "on_chat_model_end":
      console.log("\nModel finished");
      break;
    case "on_tool_start":
      console.log(`Calling tool: ${event.name}`);
      break;
  }
}
```

## Disable Streaming for Specific Models

```typescript
const model = new ChatOpenAI({
  model: "o1-preview",
  streaming: false,  // Disable for this model
});
```

## With Thread ID

```typescript
const stream = agent.stream(
  { messages: [{ role: "user", content: "Hello" }] },
  {
    configurable: { thread_id: "user-123" },
    streamMode: "messages",
  }
);
```
