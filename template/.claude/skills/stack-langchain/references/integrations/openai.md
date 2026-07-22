# OpenAI Integration (GPT)

## Installation

```bash
npm install @langchain/openai
```

## Basic Usage

```typescript
import { ChatOpenAI } from "@langchain/openai";

const model = new ChatOpenAI({
  model: "gpt-4o",
  temperature: 0,
});

const response = await model.invoke("Hello!");
console.log(response.content);
```

## Available Models

| Model | Use Case |
|-------|----------|
| `gpt-4o` | Most capable, multimodal |
| `gpt-4o-mini` | Fast, cost-effective |
| `gpt-4-turbo` | Previous generation |
| `o1-preview` | Reasoning (no streaming) |
| `o1-mini` | Reasoning, smaller |

## Streaming

```typescript
const stream = await model.stream("Tell me a story");

for await (const chunk of stream) {
  process.stdout.write(chunk.content);
}
```

## Tool Calling

```typescript
const modelWithTools = model.bindTools([myTool]);
const response = await modelWithTools.invoke("Use the tool");

if (response.tool_calls?.length) {
  console.log(response.tool_calls);
}
```

## Structured Output

```typescript
const schema = z.object({
  answer: z.string(),
  sources: z.array(z.string()),
});

const structuredModel = model.withStructuredOutput(schema);
const result = await structuredModel.invoke("What is LangChain?");
```

## JSON Mode

```typescript
const jsonModel = new ChatOpenAI({
  model: "gpt-4o",
  responseFormat: { type: "json_object" },
});

const response = await jsonModel.invoke(
  "Return a JSON object with name and age fields"
);
```

## Vision (Multimodal)

```typescript
import { HumanMessage } from "@langchain/core/messages";

const response = await model.invoke([
  new HumanMessage({
    content: [
      { type: "text", text: "What's in this image?" },
      { type: "image_url", image_url: { url: "https://..." } },
    ],
  }),
]);
```

## With React Agent

```typescript
import { createReactAgent } from "@langchain/langgraph/prebuilt";

const agent = createReactAgent({
  llm: new ChatOpenAI({ model: "gpt-4o" }),
  tools: [myTool],
});
```

## Configuration Options

```typescript
const model = new ChatOpenAI({
  model: "gpt-4o",
  temperature: 0.7,
  maxTokens: 4096,
  topP: 0.9,
  frequencyPenalty: 0,
  presencePenalty: 0,
  timeout: 60000,
  maxRetries: 2,
});
```

## o1 Models (Reasoning)

```typescript
const reasoningModel = new ChatOpenAI({
  model: "o1-preview",
  streaming: false,  // Required: o1 doesn't support streaming
});
```

## Environment Variable

```bash
OPENAI_API_KEY=sk-...
```

## With Organization

```typescript
const model = new ChatOpenAI({
  model: "gpt-4o",
  openAIApiKey: process.env.OPENAI_API_KEY,
  organization: "org-...",
});
```
