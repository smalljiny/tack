# Workflows vs Agents

Two LangGraph patterns: deterministic Workflows and autonomous Agents.

## Workflow Pattern

Fixed execution paths. Predictable and easy to debug.

```typescript
const workflowGraph = new StateGraph(State)
  .addNode("validate", validateInput)
  .addNode("process", processData)
  .addNode("save", saveResult)
  .addEdge(START, "validate")
  .addEdge("validate", "process")
  .addEdge("process", "save")
  .addEdge("save", END)
  .compile();
```

### Characteristics
- Fixed execution order
- Can work without LLM
- Fast and cost-effective
- Easy to debug

## Agent Pattern

LLM decides the next action. Flexible but harder to predict.

```typescript
const agentGraph = new StateGraph(AgentState)
  .addNode("agent", agentNode)
  .addNode("tools", toolNode)
  .addEdge(START, "agent")
  .addConditionalEdges("agent", shouldContinue, {
    tools: "tools",
    end: END,
  })
  .addEdge("tools", "agent")  // Loop back
  .compile();
```

### Characteristics
- LLM decides branching
- Can loop (agent ↔ tools)
- Flexible but incurs cost
- Hard to predict results

## Hybrid Pattern (Recommended)

Use Agent only for specific parts within a Workflow.

```typescript
const hybridGraph = new StateGraph(State)
  // Workflow: deterministic steps
  .addNode("validate", validateInput)

  // Agent: flexible reasoning
  .addNode("reason", agentNode)
  .addNode("tools", toolNode)

  // Workflow: deterministic output
  .addNode("format", formatOutput)

  .addEdge(START, "validate")
  .addEdge("validate", "reason")
  .addConditionalEdges("reason", shouldUseTool, {
    tools: "tools",
    format: "format",
  })
  .addEdge("tools", "reason")
  .addEdge("format", END)
  .compile();
```

## Choosing the Right Pattern

| Situation | Pattern |
|-----------|---------|
| Fixed business logic | Workflow |
| Data pipelines | Workflow |
| Complex decision-making | Agent |
| Questions requiring tool use | Agent |
| Mostly fixed with some flexibility | Hybrid |

## Control Flow Examples

### Sequential (Workflow)

```
START → A → B → C → END
```

### Branching (Workflow)

```
START → A → [condition] → B or C → END
```

### Loop (Agent)

```
START → Agent ↔ Tools → END
```

### Fan-out/Fan-in (Workflow)

```
START → A → B, C (parallel) → D → END
```

## Practical Example: Customer Support

```typescript
const supportGraph = new StateGraph(State)
  // Workflow: classify ticket
  .addNode("classify", classifyTicket)

  // Branch based on classification
  .addConditionalEdges("classify", (s) => s.category, {
    billing: "billingAgent",
    technical: "techAgent",
    general: "generalResponse",
  })

  // Agents for complex categories
  .addNode("billingAgent", billingAgentSubgraph)
  .addNode("techAgent", techAgentSubgraph)

  // Workflow: simple response
  .addNode("generalResponse", generateResponse)

  .addEdge(START, "classify")
  .addEdge("billingAgent", END)
  .addEdge("techAgent", END)
  .addEdge("generalResponse", END)
  .compile();
```

## Best Practices

1. **Start with Workflow**: Add Agent complexity only when needed
2. **Limit Agent scope**: Contain LLM decisions to specific nodes
3. **Set recursion limits**: Prevent infinite loops
4. **Add checkpoints**: Enable recovery and debugging
