# Deep Agents Quickstart

## Installation

```bash
npm install deepagents @langchain/langgraph
```

## Basic Example

```typescript
import { createDeepAgent } from "deepagents";

const agent = createDeepAgent({
  model: "claude-sonnet-4-20250514",
});

const result = await agent.invoke({
  messages: [{
    role: "user",
    content: "Create a Python script that prints 'Hello World'",
  }],
});

console.log(result.messages.at(-1).content);
// Agent creates and saves the file
```

## With Custom System Prompt

```typescript
const agent = createDeepAgent({
  model: "claude-sonnet-4-20250514",
  systemPrompt: `You are a senior developer.
    Follow best practices and add comments.
    Create tests for all code.`,
});
```

## With Checkpointer

```typescript
import { MemorySaver } from "@langchain/langgraph";

const agent = createDeepAgent({
  model: "claude-sonnet-4-20250514",
  checkpointer: new MemorySaver(),
});

// Continue conversation
await agent.invoke(
  { messages: [{ role: "user", content: "Add error handling" }] },
  { configurable: { thread_id: "project-1" } }
);
```

## Add Custom Tools

```typescript
import { tool } from "@langchain/core/tools";
import { z } from "zod";

const deployTool = tool(
  async ({ target }) => `Deployed to ${target}`,
  {
    name: "deploy",
    description: "Deploy the project",
    schema: z.object({ target: z.string() }),
  }
);

const agent = createDeepAgent({
  model: "claude-sonnet-4-20250514",
  tools: [deployTool],  // Additional tools
});
```

## Streaming

```typescript
const stream = agent.stream(
  { messages: [{ role: "user", content: "Create a web app" }] },
  { streamMode: "messages" }
);

for await (const [message, metadata] of stream) {
  process.stdout.write(message.content || "");
}
```

## Human-in-the-Loop

```typescript
const agent = createDeepAgent({
  model: "claude-sonnet-4-20250514",
  checkpointer: new MemorySaver(),
  interruptOn: {
    bash: true,        // Approve shell commands
    write_file: true,  // Approve file writes
  },
});
```

## Next Steps

- Customization: `customization.md`
- Long-term memory: `../memory/long-term.md`
- Human-in-the-loop: `../patterns/human-in-the-loop.md`
