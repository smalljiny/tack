# Azure OpenAI Integration

## Installation

```bash
npm install @langchain/openai
```

## Basic Usage

```typescript
import { AzureChatOpenAI } from "@langchain/openai";

const model = new AzureChatOpenAI({
  azureOpenAIApiDeploymentName: "your-deployment-name",
  azureOpenAIApiVersion: "2024-02-15-preview",
  temperature: 0,
});

const response = await model.invoke("Hello!");
```

## Configuration Options

```typescript
const model = new AzureChatOpenAI({
  azureOpenAIApiKey: process.env.AZURE_OPENAI_API_KEY,
  azureOpenAIApiInstanceName: process.env.AZURE_OPENAI_API_INSTANCE_NAME,
  azureOpenAIApiDeploymentName: process.env.AZURE_OPENAI_API_DEPLOYMENT_NAME,
  azureOpenAIApiVersion: "2024-02-15-preview",
  temperature: 0,
  maxTokens: 4096,
});
```

## Environment Variables

```bash
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_API_INSTANCE_NAME=your-instance
AZURE_OPENAI_API_DEPLOYMENT_NAME=your-deployment
AZURE_OPENAI_API_VERSION=2024-02-15-preview
```

## Tool Calling

```typescript
const modelWithTools = model.bindTools([myTool]);
const response = await modelWithTools.invoke("Use the tool");
```

## Structured Output

```typescript
const structuredModel = model.withStructuredOutput(schema);
```

## Streaming

```typescript
const stream = await model.stream("Tell me a story");

for await (const chunk of stream) {
  process.stdout.write(chunk.content);
}
```

## With Managed Identity

```typescript
import { DefaultAzureCredential } from "@azure/identity";

const credentials = new DefaultAzureCredential();

const model = new AzureChatOpenAI({
  azureOpenAIApiDeploymentName: "your-deployment",
  azureADTokenProvider: async () => {
    const token = await credentials.getToken(
      "https://cognitiveservices.azure.com/.default"
    );
    return token.token;
  },
});
```
