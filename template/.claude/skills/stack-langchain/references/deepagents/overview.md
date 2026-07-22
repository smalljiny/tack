# Deep Agents Overview

Deep Agents: Filesystem-based autonomous agents.

## What are Deep Agents?

- Perform tasks through local filesystem
- Automate complex multi-step tasks
- Code generation, file editing, project management

## Core Concepts

### Filesystem Backend

```typescript
import { createDeepAgent, StateBackend } from "deepagents";

const agent = createDeepAgent({
  model: "claude-sonnet-4-20250514",
  backend: (config) => new StateBackend(config),
});
```

### Built-in Tools

Deep Agent provides file-related tools by default:

- `read_file` - Read files
- `write_file` - Write files
- `edit_file` - Edit files
- `ls` - List directories
- `bash` - Execute shell commands

## Basic Usage

```typescript
import { createDeepAgent } from "deepagents";

const agent = createDeepAgent({
  model: "claude-sonnet-4-20250514",
  systemPrompt: "You are a coding assistant.",
});

const result = await agent.invoke({
  messages: [{ role: "user", content: "Create a hello.py file" }],
});
```

## With Persistence

```typescript
import { MemorySaver } from "@langchain/langgraph";

const agent = createDeepAgent({
  model: "claude-sonnet-4-20250514",
  checkpointer: new MemorySaver(),
});

// Thread-based persistence
const result = await agent.invoke(
  { messages: [{ role: "user", content: "Task 1" }] },
  { configurable: { thread_id: "project-1" } }
);
```

## When to Use

- Code generation and refactoring
- Project setup automation
- File-based data processing
- Complex multi-step tasks

## vs React Agent

| Deep Agent | React Agent |
|------------|-------------|
| Filesystem-based | Custom tool-based |
| Optimized for code generation | General-purpose agent |
| Built-in file tools | Define tools manually |
