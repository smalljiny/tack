# Deep Agent Customization

## Custom Backend

### StateBackend (Default)

In-state filesystem. Destroyed when thread ends.

```typescript
import { createDeepAgent, StateBackend } from "deepagents";

const agent = createDeepAgent({
  backend: (config) => new StateBackend(config),
});
```

### CompositeBackend (Hybrid Storage)

Some paths are persistent, others are temporary.

```typescript
import { CompositeBackend, StateBackend, StoreBackend } from "deepagents";
import { InMemoryStore } from "@langchain/langgraph";

const agent = createDeepAgent({
  store: new InMemoryStore(),
  backend: (config) => new CompositeBackend(
    new StateBackend(config),  // Default: ephemeral
    { "/memories/": new StoreBackend(config) }  // Persistent
  ),
});

// Files in /memories/* path persist across threads
// Files in other paths are destroyed when thread ends
```

## Subagents

Configure specialized subagents.

```typescript
const agent = createDeepAgent({
  model: "claude-sonnet-4-20250514",
  subagents: [
    {
      name: "code-reviewer",
      description: "Reviews code for best practices",
      systemPrompt: "You are a code review expert.",
      tools: [lintTool, analyzeTool],
    },
    {
      name: "tester",
      description: "Writes and runs tests",
      systemPrompt: "You are a testing specialist.",
      tools: [testRunnerTool],
    },
  ],
});
```

## Middleware

```typescript
const loggingMiddleware = {
  beforeToolCall: async (toolCall, state, config) => {
    console.log(`Tool: ${toolCall.name}`);
    return { block: false };
  },
};

const agent = createDeepAgent({
  model: "claude-sonnet-4-20250514",
  middleware: [loggingMiddleware],
});
```

## Interrupt Configuration

```typescript
const agent = createDeepAgent({
  model: "claude-sonnet-4-20250514",
  checkpointer: new MemorySaver(),
  interruptOn: {
    bash: true,  // All decisions
    write_file: { allowedDecisions: ["approve", "reject"] },
    read_file: false,  // No approval needed
  },
});
```

## Custom Tools

```typescript
import { tool } from "@langchain/core/tools";

const gitTool = tool(
  async ({ command }) => {
    const result = await exec(`git ${command}`);
    return result.stdout;
  },
  {
    name: "git",
    description: "Run git commands",
    schema: z.object({
      command: z.string().describe("Git command without 'git' prefix"),
    }),
  }
);

const agent = createDeepAgent({
  model: "claude-sonnet-4-20250514",
  tools: [gitTool],
});
```

## System Prompt Patterns

### Project-Aware

```typescript
const agent = createDeepAgent({
  systemPrompt: `You are a coding assistant for a TypeScript project.

Project structure:
- src/ - Source code
- tests/ - Test files
- package.json - Dependencies

Conventions:
- Use TypeScript strict mode
- Write tests for all functions
- Follow ESLint rules`,
});
```

### Self-Improving

```typescript
const agent = createDeepAgent({
  systemPrompt: `You have a file at /memories/instructions.txt.
Read it at the start of each conversation.
Update it when users give feedback like "always do X".`,
  backend: (config) => new CompositeBackend(
    new StateBackend(config),
    { "/memories/": new StoreBackend(config) }
  ),
});
```

## Model Configuration

```typescript
const agent = createDeepAgent({
  model: "claude-sonnet-4-20250514",
  modelConfig: {
    temperature: 0,
    maxTokens: 8192,
  },
});
```
