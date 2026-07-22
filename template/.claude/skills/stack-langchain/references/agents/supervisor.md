# Multi-Agent & Supervisor Pattern

Patterns for orchestrating multiple agents.

## Supervisor Pattern

```typescript
import { createSupervisor } from "@langchain/langgraph-supervisor";

const researchAgent = createReactAgent({
  llm: model,
  tools: [searchTool, fetchTool],
  prompt: "You are a research specialist.",
});

const writerAgent = createReactAgent({
  llm: model,
  tools: [writeTool],
  prompt: "You are a content writer.",
});

const supervisor = createSupervisor({
  agents: [researchAgent, writerAgent],
  llm: model,
  prompt: `You are a project manager.
    Delegate tasks to:
    - researcher: for information gathering
    - writer: for content creation`,
});

const result = await supervisor.invoke({
  messages: [{ role: "user", content: "Write an article about AI" }],
});
```

## Manual Multi-Agent Graph

```typescript
const AgentState = Annotation.Root({
  messages: Annotation<BaseMessage[]>({
    reducer: (x, y) => x.concat(y),
  }),
  nextAgent: Annotation<string>(),
});

async function supervisorNode(state: typeof AgentState.State) {
  const response = await supervisorModel.invoke(state.messages);
  // Parse which agent to call next
  return { nextAgent: "researcher" };
}

async function researcherNode(state: typeof AgentState.State) {
  const response = await researcherAgent.invoke(state.messages);
  return { messages: response.messages };
}

async function writerNode(state: typeof AgentState.State) {
  const response = await writerAgent.invoke(state.messages);
  return { messages: response.messages };
}

function routeToAgent(state: typeof AgentState.State) {
  return state.nextAgent;
}

const graph = new StateGraph(AgentState)
  .addNode("supervisor", supervisorNode)
  .addNode("researcher", researcherNode)
  .addNode("writer", writerNode)
  .addEdge(START, "supervisor")
  .addConditionalEdges("supervisor", routeToAgent, {
    researcher: "researcher",
    writer: "writer",
    end: END,
  })
  .addEdge("researcher", "supervisor")
  .addEdge("writer", "supervisor")
  .compile();
```

## Agent Handoff with Command

```typescript
import { Command } from "@langchain/langgraph";

async function agentA(state: State) {
  if (needsSpecialist(state)) {
    return new Command({
      update: { messages: [new AIMessage("Handing off...")] },
      goto: "agentB",
    });
  }
  return { messages: [response] };
}
```

## Subgraph as Agent

```typescript
// Define specialized agent as subgraph
const specialistGraph = new StateGraph(AgentState)
  .addNode("process", processNode)
  .addEdge(START, "process")
  .addEdge("process", END)
  .compile();

// Use in parent graph
const mainGraph = new StateGraph(AgentState)
  .addNode("router", routerNode)
  .addNode("specialist", specialistGraph)  // Subgraph as node
  .addEdge(START, "router")
  .addConditionalEdges("router", route)
  .compile();
```

## Swarm Pattern (Dynamic Routing)

```typescript
const agents = {
  sales: createReactAgent({ llm, tools: salesTools }),
  support: createReactAgent({ llm, tools: supportTools }),
  billing: createReactAgent({ llm, tools: billingTools }),
};

async function routerNode(state: State) {
  const classification = await classifyQuery(state.messages);
  return { nextAgent: classification.department };
}

function dynamicRoute(state: State) {
  return state.nextAgent;
}
```

## Best Practices

1. **Clear agent roles**: Each agent should have a specific, well-defined purpose
2. **Minimal handoffs**: Too many handoffs increase latency and complexity
3. **Shared context**: Use state to pass relevant context between agents
4. **Error boundaries**: Handle failures gracefully in each agent
