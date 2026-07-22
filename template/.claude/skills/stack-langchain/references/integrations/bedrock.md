# AWS Bedrock Integration

## Installation

```bash
npm install @langchain/aws
```

## Basic Usage

```typescript
import { ChatBedrock } from "@langchain/aws";

const model = new ChatBedrock({
  model: "anthropic.claude-3-sonnet-20240229-v1:0",
  region: "us-east-1",
});

const response = await model.invoke("Hello!");
```

## Available Models

```
anthropic.claude-3-opus-20240229-v1:0
anthropic.claude-3-sonnet-20240229-v1:0
anthropic.claude-3-haiku-20240307-v1:0
amazon.titan-text-express-v1
meta.llama3-70b-instruct-v1:0
```

## Configuration

```typescript
const model = new ChatBedrock({
  model: "anthropic.claude-3-sonnet-20240229-v1:0",
  region: "us-east-1",
  credentials: {
    accessKeyId: process.env.AWS_ACCESS_KEY_ID,
    secretAccessKey: process.env.AWS_SECRET_ACCESS_KEY,
  },
  temperature: 0,
  maxTokens: 4096,
});
```

## With AWS Profile

```typescript
import { fromIni } from "@aws-sdk/credential-providers";

const model = new ChatBedrock({
  model: "anthropic.claude-3-sonnet-20240229-v1:0",
  region: "us-east-1",
  credentials: fromIni({ profile: "my-profile" }),
});
```

## Tool Calling

```typescript
const modelWithTools = model.bindTools([myTool]);
```

## Streaming

```typescript
const stream = await model.stream("Tell me a story");

for await (const chunk of stream) {
  process.stdout.write(chunk.content);
}
```

## Environment Variables

```bash
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=us-east-1
```

## With React Agent

```typescript
import { createReactAgent } from "@langchain/langgraph/prebuilt";

const agent = createReactAgent({
  llm: new ChatBedrock({
    model: "anthropic.claude-3-sonnet-20240229-v1:0",
    region: "us-east-1",
  }),
  tools: [myTool],
});
```
