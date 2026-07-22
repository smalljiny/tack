# Subgraphs

Modularize by including graphs within other graphs.

## Basic Subgraph

```typescript
// Define subgraph
const subgraph = new StateGraph(SubState)
  .addNode("process", processNode)
  .addEdge(START, "process")
  .addEdge("process", END)
  .compile();

// Use in parent graph
const parentGraph = new StateGraph(ParentState)
  .addNode("main", mainNode)
  .addNode("sub", subgraph)  // Subgraph as node
  .addEdge(START, "main")
  .addEdge("main", "sub")
  .addEdge("sub", END)
  .compile();
```

## State Mapping

Convert between subgraph state and parent state.

```typescript
const ParentState = z.object({
  query: z.string(),
  result: z.string(),
});

const SubState = z.object({
  input: z.string(),
  output: z.string(),
});

// Input/output transformers
const subgraphNode = async (state: ParentState) => {
  // Map parent → subgraph state
  const subInput = { input: state.query };

  // Run subgraph
  const subResult = await subgraph.invoke(subInput);

  // Map subgraph → parent state
  return { result: subResult.output };
};
```

## Shared State Keys

```typescript
// Both use same state schema
const SharedState = z.object({
  messages: z.array(z.custom<BaseMessage>()).register(registry, MessagesZodMeta),
  context: z.string(),
});

const subgraph = new StateGraph(SharedState)
  .addNode("process", processNode)
  .compile();

const parent = new StateGraph(SharedState)
  .addNode("sub", subgraph)  // Shares state automatically
  .compile();
```

## Navigate to Parent (Command.PARENT)

```typescript
import { Command } from "@langchain/langgraph";

async function subgraphNode(state) {
  if (shouldHandoff(state)) {
    return new Command({
      update: { result: "handoff" },
      goto: "otherNode",
      graph: Command.PARENT,  // Navigate to parent graph
    });
  }
  return { result: "done" };
}
```

## Streaming from Subgraphs

```typescript
for await (const chunk of parent.stream(input, {
  streamMode: "updates",
  subgraphs: true,
})) {
  const [namespace, data] = chunk;
  // namespace: path to subgraph, e.g., ["subNode:task-id"]
  console.log(`From ${namespace}:`, data);
}
```

## Nested Subgraphs

```typescript
const innerGraph = new StateGraph(State)
  .addNode("inner", innerNode)
  .compile();

const middleGraph = new StateGraph(State)
  .addNode("middle", middleNode)
  .addNode("inner", innerGraph)
  .compile();

const outerGraph = new StateGraph(State)
  .addNode("outer", outerNode)
  .addNode("middle", middleGraph)
  .compile();
```

## Subgraph with Different Checkpointer

```typescript
const subgraph = new StateGraph(SubState)
  .addNode("process", processNode)
  .compile({
    checkpointer: new MemorySaver(),  // Own checkpointer
  });
```

## Use Cases

1. **Modular agents**: Encapsulate specialized logic
2. **Reusable components**: Share across multiple graphs
3. **Testing**: Test subgraphs in isolation
4. **Multi-agent**: Each agent as a subgraph
