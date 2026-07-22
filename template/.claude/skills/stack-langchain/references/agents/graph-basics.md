# Graph Basics (StateGraph)

LangGraph's core concepts: State, Nodes, Edges.

## State Definition

### Using Annotation

```typescript
import { Annotation } from "@langchain/langgraph";
import { BaseMessage } from "@langchain/core/messages";

const AgentState = Annotation.Root({
  // Messages with concat reducer
  messages: Annotation<BaseMessage[]>({
    reducer: (x, y) => x.concat(y),
  }),

  // Simple value (overwrite)
  currentStep: Annotation<string>(),

  // With default value
  count: Annotation<number>({
    reducer: (x, y) => x + y,
    default: () => 0,
  }),
});
```

### Using Zod (Recommended)

```typescript
import { StateGraph, MessagesZodMeta } from "@langchain/langgraph";
import { registry } from "@langchain/langgraph/zod";
import * as z from "zod";

const State = z.object({
  messages: z.array(z.custom<BaseMessage>()).register(registry, MessagesZodMeta),
  query: z.string(),
  result: z.string().optional(),
});
```

### MessagesAnnotation (Shorthand)

```typescript
import { MessagesAnnotation } from "@langchain/langgraph";

// Pre-built messages state
const graph = new StateGraph(MessagesAnnotation)
  .addNode("chat", chatNode)
  .addEdge(START, "chat");
```

## Nodes

Functions that receive state and return updates.

```typescript
async function processNode(
  state: typeof AgentState.State
): Promise<Partial<typeof AgentState.State>> {
  const response = await model.invoke(state.messages);
  return {
    messages: [response],
    count: 1,
  };
}
```

### Node with Config

```typescript
async function nodeWithConfig(
  state: typeof AgentState.State,
  config: RunnableConfig
) {
  const userId = config.configurable?.userId;
  // Use config...
  return { /* state update */ };
}
```

## Edges

### Normal Edges

```typescript
graph
  .addEdge(START, "nodeA")
  .addEdge("nodeA", "nodeB")
  .addEdge("nodeB", END);
```

### Conditional Edges

```typescript
function routeDecision(state: typeof AgentState.State): string {
  if (state.needsTools) return "tools";
  return "end";
}

graph.addConditionalEdges("agent", routeDecision, {
  tools: "toolNode",
  end: END,
});
```

## Complete Example

```typescript
import { StateGraph, START, END, Annotation } from "@langchain/langgraph";
import { ChatAnthropic } from "@langchain/anthropic";
import { BaseMessage, AIMessage } from "@langchain/core/messages";

// State
const AgentState = Annotation.Root({
  messages: Annotation<BaseMessage[]>({
    reducer: (x, y) => x.concat(y),
  }),
});

// Model
const model = new ChatAnthropic({ model: "claude-sonnet-4-20250514" });

// Nodes
async function agentNode(state: typeof AgentState.State) {
  const response = await model.invoke(state.messages);
  return { messages: [response] };
}

function shouldContinue(state: typeof AgentState.State) {
  const lastMessage = state.messages.at(-1) as AIMessage;
  if (lastMessage.tool_calls?.length) return "tools";
  return "end";
}

// Graph
const graph = new StateGraph(AgentState)
  .addNode("agent", agentNode)
  .addNode("tools", toolNode)
  .addEdge(START, "agent")
  .addConditionalEdges("agent", shouldContinue, {
    tools: "tools",
    end: END,
  })
  .addEdge("tools", "agent")
  .compile();

// Run
const result = await graph.invoke({
  messages: [{ role: "user", content: "Hello" }],
});
```

## Compile Options

```typescript
const app = graph.compile({
  checkpointer: new MemorySaver(),     // Enable memory
  interruptBefore: ["tools"],          // Pause before tools
  interruptAfter: ["agent"],           // Pause after agent
});
```

## Recursion Limit

```typescript
const result = await app.invoke(input, {
  recursionLimit: 50,  // Default: 25
});
```

For advanced patterns (branching, loops, Command), see `agents/graph-advanced.md`.
