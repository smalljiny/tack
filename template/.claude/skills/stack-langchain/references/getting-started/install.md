# Installation

## LangChain + LangGraph

```bash
npm install langchain @langchain/core @langchain/langgraph
```

## Provider Integrations

```bash
# Anthropic (Claude)
npm install @langchain/anthropic

# OpenAI
npm install @langchain/openai

# Google Gemini
npm install @langchain/google-genai

# Azure OpenAI
npm install @langchain/openai  # same package, different config

# AWS Bedrock
npm install @langchain/aws
```

## Additional Packages

```bash
# Zod for schema validation
npm install zod

# Checkpointing (production)
npm install @langchain/langgraph-checkpoint-postgres

# Deep Agents
npm install deepagents
```

## Minimum Requirements

- Node.js 20+
- TypeScript 5.0+

## Environment Variables

```bash
# Anthropic
ANTHROPIC_API_KEY=sk-ant-...

# OpenAI
OPENAI_API_KEY=sk-...

# Google
GOOGLE_API_KEY=...

# Azure
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_API_INSTANCE_NAME=...
AZURE_OPENAI_API_DEPLOYMENT_NAME=...
AZURE_OPENAI_API_VERSION=...
```

## Verify Installation

```typescript
import { ChatAnthropic } from "@langchain/anthropic";
import { StateGraph, START, END } from "@langchain/langgraph";

const model = new ChatAnthropic({ model: "claude-sonnet-4-20250514" });
const response = await model.invoke("Hello!");
console.log(response.content);
```
