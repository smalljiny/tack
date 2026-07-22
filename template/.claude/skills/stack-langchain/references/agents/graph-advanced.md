# Graph Advanced Patterns

Complex graph patterns: Branching, Loops, Command, Send API.

## Parallel Execution (Fan-out/Fan-in)

```typescript
const graph = new StateGraph(State)
  .addNode("a", nodeA)
  .addNode("b", nodeB)
  .addNode("c", nodeC)
  .addNode("d", nodeD)
  .addEdge(START, "a")
  .addEdge("a", "b")  // Fan-out
  .addEdge("a", "c")  // Fan-out
  .addEdge("b", "d")  // Fan-in
  .addEdge("c", "d")  // Fan-in
  .addEdge("d", END)
  .compile();
```

Nodes B and C run in parallel after A, then merge into D.

## Conditional Branching

```typescript
function routeByType(state: State): "b" | "c" {
  return state.type === "typeB" ? "b" : "c";
}

graph.addConditionalEdges("a", routeByType, {
  b: "nodeB",
  c: "nodeC",
});
```

### Multi-destination Routing

```typescript
function multiRoute(state: State): string[] {
  if (state.needsBoth) return ["b", "c"];
  return ["b"];
}
```

## Loops

```typescript
function shouldLoop(state: State): "continue" | typeof END {
  if (state.iterations < 5) return "continue";
  return END;
}

graph
  .addNode("process", processNode)
  .addEdge(START, "process")
  .addConditionalEdges("process", shouldLoop, {
    continue: "process",
    [END]: END,
  });
```

## Command API

State update + routing in one return.

```typescript
import { Command } from "@langchain/langgraph";

async function nodeWithCommand(state: State) {
  const nextNode = state.score > 0.8 ? "success" : "retry";

  return new Command({
    update: {
      messages: [new AIMessage("Processing...")],
      score: state.score + 0.1,
    },
    goto: nextNode,
  });
}

// Must declare possible destinations
graph.addNode("process", nodeWithCommand, {
  ends: ["success", "retry"],
});
```

### Command in Tools

```typescript
const toolWithCommand = tool(
  async (input, config) => {
    return new Command({
      update: {
        userInfo: { name: input.name },
        messages: [{
          role: "tool",
          content: "User found",
          tool_call_id: config.toolCall.id,
        }],
      },
    });
  },
  { name: "lookup_user", schema: z.object({ name: z.string() }) }
);
```

## Send API (Map-Reduce)

Dynamic fan-out with custom state per destination.

```typescript
import { Send } from "@langchain/langgraph";

function fanOutToWorkers(state: State) {
  return state.tasks.map(
    (task) => new Send("worker", { task, context: state.context })
  );
}

graph.addConditionalEdges("dispatcher", fanOutToWorkers);
```

### Complete Map-Reduce Example

```typescript
const State = z.object({
  topics: z.array(z.string()),
  results: z.array(z.string()).register(registry, {
    reducer: { fn: (x, y) => x.concat(y) },
  }),
});

function generateTopics(state) {
  return { topics: ["topic1", "topic2", "topic3"] };
}

function processOneTopic(state: { topic: string }) {
  return { results: [`Processed: ${state.topic}`] };
}

function fanOut(state) {
  return state.topics.map((topic) => new Send("process", { topic }));
}

const graph = new StateGraph(State)
  .addNode("generate", generateTopics)
  .addNode("process", processOneTopic)
  .addEdge(START, "generate")
  .addConditionalEdges("generate", fanOut)
  .addEdge("process", END)
  .compile();
```

## Input/Output Schemas

```typescript
const InputSchema = z.object({ query: z.string() });
const OutputSchema = z.object({ answer: z.string() });
const InternalState = InputSchema.merge(OutputSchema).extend({
  intermediateSteps: z.array(z.string()),
});

const graph = new StateGraph({
  input: InputSchema,
  output: OutputSchema,
  state: InternalState,
});
```

## Private State Between Nodes

```typescript
const Node1Output = z.object({ privateData: z.string() });
const Node2Input = z.object({ privateData: z.string() });

const graph = new StateGraph({
  state: OverallState,
  nodes: {
    node1: { action: node1, output: Node1Output },
    node2: { action: node2, input: Node2Input },
  },
});
```

## Retry Policy

```typescript
graph.addNode("apiCall", callApi, {
  retryPolicy: {
    maxAttempts: 3,
    retryOn: (e) => e.message.includes("rate limit"),
  },
});
```

## Visualization

```typescript
const drawableGraph = await graph.getGraphAsync();
console.log(drawableGraph.drawMermaid());
```
