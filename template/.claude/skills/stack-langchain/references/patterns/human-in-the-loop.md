# Human-in-the-Loop

Human approval, modification, or rejection for sensitive operations.

## Basic Setup

```typescript
import { createReactAgent } from "@langchain/langgraph/prebuilt";
import { MemorySaver } from "@langchain/langgraph";

const checkpointer = new MemorySaver();

const agent = createReactAgent({
  llm: model,
  tools: [dangerousTool],
  checkpointer,
  interruptBefore: ["tools"],  // Pause before tool execution
});
```

## Decision Types

| Decision | Description |
|----------|-------------|
| `approve` | Execute as proposed |
| `edit` | Modify arguments, then execute |
| `reject` | Skip execution, provide feedback |

## Handling Interrupts

```typescript
const config = { configurable: { thread_id: "thread-1" } };

// Invoke - may pause
let result = await agent.invoke(
  { messages: [{ role: "user", content: "Delete temp files" }] },
  config
);

// Check for interrupt
if (result.__interrupt__) {
  console.log("Needs approval:", result.__interrupt__);

  // Resume with decision
  result = await agent.invoke(
    new Command({ resume: { decision: "approve" } }),
    config
  );
}
```

## Edit Before Approval

```typescript
if (result.__interrupt__) {
  result = await agent.invoke(
    new Command({
      resume: {
        decision: "edit",
        args: { path: "/safe/path/file.txt" },
      },
    }),
    config
  );
}
```

## Reject with Feedback

```typescript
if (result.__interrupt__) {
  result = await agent.invoke(
    new Command({
      resume: {
        decision: "reject",
        feedback: "Cannot delete files in that directory",
      },
    }),
    config
  );
}
```

## Using interrupt() Function

```typescript
import { interrupt } from "@langchain/langgraph";

async function sensitiveNode(state) {
  const approval = interrupt({
    action: state.pendingAction,
    reason: "This action requires approval",
  });

  if (approval.approved) {
    return performAction(state);
  }
  return { status: "rejected" };
}

// Resume
await graph.invoke(null, {
  configurable: { thread_id: "thread-1" },
  resume: { approved: true },
});
```

## Multiple Tool Calls

```typescript
if (result.__interrupt__) {
  const actions = result.__interrupt__[0].value.actionRequests;

  // Provide decisions in order
  const decisions = [
    { type: "approve" },  // First tool
    { type: "reject" },   // Second tool
  ];

  result = await agent.invoke(
    new Command({ resume: { decisions } }),
    config
  );
}
```

## Streaming with Interrupts

```typescript
const stream = agent.stream(input, {
  configurable: { thread_id: "thread-1" },
  streamMode: ["updates", "messages"],
});

for await (const [mode, chunk] of stream) {
  if (mode === "updates" && chunk.__interrupt__) {
    console.log("Interrupt:", chunk.__interrupt__);
    // Handle in UI
  }
}
```

## Per-Tool Configuration

```typescript
const agent = createReactAgent({
  llm: model,
  tools: [readTool, writeTool, deleteTool],
  checkpointer,
  interruptOn: {
    read_file: false,  // No approval needed
    write_file: { allowedDecisions: ["approve", "reject"] },
    delete_file: true,  // All decisions allowed
  },
});
```

## Production Setup

```typescript
import { PostgresSaver } from "@langchain/langgraph-checkpoint-postgres";

const checkpointer = await PostgresSaver.fromConnString(connectionString);
```
