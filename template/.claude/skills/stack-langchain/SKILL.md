---
version: 2
name: stack-langchain
description: LangChain and LangGraph TypeScript 1.0 implementation guide. This skill should be used when building AI agents, workflows, RAG systems, or multi-agent applications using LangChain/LangGraph in TypeScript. Covers agent patterns, memory management, streaming, tools, integrations, and Deep Agents.
origin: SCE
capabilities: [language-patterns, typescript, langchain]
---

# LangChain/LangGraph TypeScript

## When to Use

- Building AI agents with tool calling
- Implementing RAG systems
- Creating multi-agent workflows
- Working with chat models (Anthropic, OpenAI, etc.)
- Implementing short-term and long-term memory
- Building stateful graph-based workflows

## Quick Reference

### Key Imports

```typescript
// Models
import { ChatAnthropic } from "@langchain/anthropic";
import { ChatOpenAI } from "@langchain/openai";

// Agent
import { createReactAgent } from "@langchain/langgraph/prebuilt";

// Graph
import { StateGraph, START, END, Annotation } from "@langchain/langgraph";
import { MemorySaver, InMemoryStore } from "@langchain/langgraph";

// Tools
import { tool } from "@langchain/core/tools";
import { z } from "zod";
```

### React Agent (Simple)

```typescript
const searchTool = tool(
  async ({ query }) => `Results for: ${query}`,
  {
    name: "search",
    description: "Search for information",
    schema: z.object({ query: z.string() }),
  }
);

const model = new ChatAnthropic({ model: "claude-sonnet-4-20250514" });
const agent = createReactAgent({ llm: model, tools: [searchTool] });

const result = await agent.invoke({
  messages: [{ role: "user", content: "Search for LangChain" }],
});
```

### StateGraph (Custom Workflow)

```typescript
const AgentState = Annotation.Root({
  messages: Annotation<BaseMessage[]>({
    reducer: (x, y) => x.concat(y),
  }),
});

const graph = new StateGraph(AgentState)
  .addNode("agent", agentNode)
  .addEdge(START, "agent")
  .addConditionalEdges("agent", shouldContinue, {
    tools: "tools",
    end: END,
  })
  .compile({ checkpointer: new MemorySaver() });
```

### Memory

```typescript
// Short-term (thread-based)
const checkpointer = new MemorySaver();
const agent = createReactAgent({ llm, tools, checkpointer });

await agent.invoke(input, {
  configurable: { thread_id: "user-123" },
});

// Long-term (cross-thread)
const store = new InMemoryStore();
await store.put(["user", "123"], "preferences", { theme: "dark" });
```

### Streaming

```typescript
// Token streaming
for await (const [msg, meta] of agent.stream(input, { streamMode: "messages" })) {
  process.stdout.write(msg.content || "");
}

// Step streaming
for await (const update of agent.stream(input, { streamMode: "updates" })) {
  console.log(update);
}
```

### Structured Output

```typescript
const schema = z.object({
  answer: z.string(),
  confidence: z.number(),
});

const structuredModel = model.withStructuredOutput(schema);
const result = await structuredModel.invoke("What is 2+2?");
```

## Reference Loading Guide

For detailed documentation, see the `references/` folder. Load only the documents you need.

### Quick Navigation → `references/_index.md`

Complete topic-based routing guide.

### By Task

| Task | Reference |
|------|-----------|
| Installation | `getting-started/install.md` |
| Quick Start | `getting-started/quickstart.md` |
| React Agent | `agents/react-agent.md` |
| StateGraph Basics | `agents/graph-basics.md` |
| StateGraph Advanced (Command, Send) | `agents/graph-advanced.md` |
| Multi-Agent | `agents/supervisor.md` |
| Conversation Memory | `memory/short-term.md` |
| Persistent Storage | `memory/long-term.md` |
| Streaming | `streaming/modes.md` |
| Tool Definition | `tools/definition.md` |
| Structured Output | `tools/structured-output.md` |
| Human-in-the-Loop | `patterns/human-in-the-loop.md` |
| Subgraph | `patterns/subgraphs.md` |
| Workflow vs Agent | `patterns/workflows-agents.md` |
| Anthropic | `integrations/anthropic.md` |
| OpenAI | `integrations/openai.md` |
| Google | `integrations/google.md` |
| Middleware | `middleware/overview.md` |
| Context Management | `advanced/context-engineering.md` |
| Persistence | `advanced/persistence.md` |
| Deep Agents | `deepagents/overview.md` |

### Search Patterns

Search for specific sections in large files:

```bash
# State definition
grep -n "Annotation\|StateGraph\|z.object" <file>

# Edge/Routing
grep -n "addEdge\|addConditionalEdges\|Command\|Send" <file>

# Memory
grep -n "MemorySaver\|InMemoryStore\|checkpointer\|store" <file>

# Streaming
grep -n "streamMode\|streamEvents\|for await" <file>

# Tool
grep -n "tool(\|bindTools\|tool_calls" <file>
```

## File Structure

```
references/
├── _index.md              # Topic-based routing
├── getting-started/       # Installation, Quickstart
├── agents/                # React Agent, StateGraph
├── memory/                # Short-term, Long-term
├── streaming/             # Stream modes
├── tools/                 # Tool definition, Structured output
├── patterns/              # HITL, Subgraph, Workflow
├── integrations/          # Anthropic, OpenAI, Google, Azure, Bedrock
├── middleware/            # Middleware system
├── advanced/              # Context, Persistence, Durable
├── migration/             # v1 migration guide
└── deepagents/            # Deep Agents
```
