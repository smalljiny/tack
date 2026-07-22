# Anthropic Integration (Claude)

## Installation

```bash
npm install @langchain/anthropic
```

## Basic Usage

```typescript
import { ChatAnthropic } from "@langchain/anthropic";

const model = new ChatAnthropic({
  model: "claude-sonnet-4-20250514",
  // Optional
  temperature: 0,
  maxTokens: 4096,
});

const response = await model.invoke("Hello!");
console.log(response.content);
```

## Available Models

| Model | Use Case |
|-------|----------|
| `claude-sonnet-4-20250514` | Balanced performance (recommended) |
| `claude-opus-4-20250514` | Most capable, complex tasks |
| `claude-haiku-4-5-20251001` | Fast, simple tasks |

## With System Message

```typescript
import { SystemMessage, HumanMessage } from "@langchain/core/messages";

const response = await model.invoke([
  new SystemMessage("You are a helpful assistant."),
  new HumanMessage("Hello!"),
]);
```

## Streaming

```typescript
const stream = await model.stream("Tell me a story");

for await (const chunk of stream) {
  process.stdout.write(chunk.content);
}
```

## Tool Calling

```typescript
import { tool } from "@langchain/core/tools";
import { z } from "zod";

const weatherTool = tool(
  async ({ city }) => `Weather in ${city}: Sunny`,
  {
    name: "get_weather",
    description: "Get weather for a city",
    schema: z.object({ city: z.string() }),
  }
);

const modelWithTools = model.bindTools([weatherTool]);
const response = await modelWithTools.invoke("What's the weather in Tokyo?");

if (response.tool_calls?.length) {
  console.log("Tool call:", response.tool_calls[0]);
}
```

## Structured Output

```typescript
const schema = z.object({
  answer: z.string(),
  confidence: z.number(),
});

const structuredModel = model.withStructuredOutput(schema);
const result = await structuredModel.invoke("What is 2+2?");
// { answer: "4", confidence: 1.0 }
```

## With React Agent

```typescript
import { createReactAgent } from "@langchain/langgraph/prebuilt";

const agent = createReactAgent({
  llm: new ChatAnthropic({ model: "claude-sonnet-4-20250514" }),
  tools: [weatherTool],
});
```

## Extended Thinking (Claude)

```typescript
const model = new ChatAnthropic({
  model: "claude-sonnet-4-20250514",
  thinking: {
    type: "enabled",
    budgetTokens: 10000,
  },
});
```

## Configuration Options

```typescript
const model = new ChatAnthropic({
  model: "claude-sonnet-4-20250514",
  temperature: 0.7,        // 0-1, creativity
  maxTokens: 4096,         // Max output tokens
  topP: 0.9,               // Nucleus sampling
  topK: 40,                // Top-k sampling
  stopSequences: ["END"],  // Stop generation
});
```

## Environment Variable

```bash
ANTHROPIC_API_KEY=sk-ant-...
```

## Error Handling

```typescript
try {
  const response = await model.invoke(prompt);
} catch (error) {
  if (error.status === 429) {
    console.log("Rate limited");
  } else if (error.status === 401) {
    console.log("Invalid API key");
  }
}
```
