# Google Integration (Gemini)

## Installation

```bash
npm install @langchain/google-genai
```

## Basic Usage

```typescript
import { ChatGoogleGenerativeAI } from "@langchain/google-genai";

const model = new ChatGoogleGenerativeAI({
  model: "gemini-1.5-pro",
  temperature: 0,
});

const response = await model.invoke("Hello!");
console.log(response.content);
```

## Available Models

| Model | Use Case |
|-------|----------|
| `gemini-1.5-pro` | Most capable |
| `gemini-1.5-flash` | Fast, cost-effective |
| `gemini-1.0-pro` | Previous generation |

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
```

## Structured Output

```typescript
const schema = z.object({
  answer: z.string(),
  confidence: z.number(),
});

const structuredModel = model.withStructuredOutput(schema);
```

## Multimodal (Vision)

```typescript
import { HumanMessage } from "@langchain/core/messages";

const response = await model.invoke([
  new HumanMessage({
    content: [
      { type: "text", text: "Describe this image" },
      {
        type: "image_url",
        image_url: { url: "data:image/jpeg;base64,..." },
      },
    ],
  }),
]);
```

## Safety Settings

```typescript
import { HarmCategory, HarmBlockThreshold } from "@google/generative-ai";

const model = new ChatGoogleGenerativeAI({
  model: "gemini-1.5-pro",
  safetySettings: [
    {
      category: HarmCategory.HARM_CATEGORY_HARASSMENT,
      threshold: HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
    },
  ],
});
```

## Configuration Options

```typescript
const model = new ChatGoogleGenerativeAI({
  model: "gemini-1.5-pro",
  temperature: 0.7,
  maxOutputTokens: 8192,
  topP: 0.9,
  topK: 40,
});
```

## Environment Variable

```bash
GOOGLE_API_KEY=...
```

## With React Agent

```typescript
import { createReactAgent } from "@langchain/langgraph/prebuilt";

const agent = createReactAgent({
  llm: new ChatGoogleGenerativeAI({ model: "gemini-1.5-pro" }),
  tools: [myTool],
});
```
