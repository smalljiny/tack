# Durable Execution

Failure recovery and resumption from interruption points.

## How It Works

LangGraph automatically checkpoints state after each node execution. When failures occur, execution resumes from the last checkpoint.

```typescript
import { MemorySaver } from "@langchain/langgraph";

const checkpointer = new MemorySaver();
const graph = workflow.compile({ checkpointer });

// Execution is durable - survives crashes
const result = await graph.invoke(input, {
  configurable: { thread_id: "durable-thread" },
});
```

## Automatic Recovery

```typescript
// First execution (crashes midway)
try {
  await graph.invoke(input, {
    configurable: { thread_id: "thread-1" },
  });
} catch (error) {
  console.log("Execution failed, state saved");
}

// Resume execution (continues from last checkpoint)
const result = await graph.invoke(null, {
  configurable: { thread_id: "thread-1" },
});
```

## Check Execution State

```typescript
const state = await graph.getState({
  configurable: { thread_id: "thread-1" },
});

if (state.next.length > 0) {
  console.log("Execution incomplete, next nodes:", state.next);
  // Resume
  await graph.invoke(null, config);
} else {
  console.log("Execution complete");
}
```

## Retry Policies

```typescript
graph.addNode("apiCall", callExternalApi, {
  retryPolicy: {
    maxAttempts: 3,
    initialDelay: 1000,
    backoffFactor: 2,
    retryOn: (error) => error.status === 429 || error.status >= 500,
  },
});
```

## Long-Running Workflows

```typescript
const longWorkflow = new StateGraph(State)
  .addNode("step1", step1)  // Checkpoint after
  .addNode("step2", step2)  // Checkpoint after
  .addNode("step3", step3)  // Checkpoint after
  .compile({ checkpointer });

// Can resume even after server restart
const result = await longWorkflow.invoke(input, {
  configurable: { thread_id: "long-running-task" },
});
```

## Timeout Handling

```typescript
const result = await graph.invoke(input, {
  configurable: { thread_id: "thread-1" },
  timeout: 30000,  // 30 seconds
});

// If timeout, can resume later
const state = await graph.getState(config);
if (state.next.length > 0) {
  await graph.invoke(null, config);
}
```

## Production Pattern

```typescript
async function executeWithRetry(
  graph: CompiledGraph,
  input: Input,
  threadId: string,
  maxRetries = 3
) {
  const config = { configurable: { thread_id: threadId } };

  for (let attempt = 0; attempt < maxRetries; attempt++) {
    try {
      // Check if there's pending execution
      const state = await graph.getState(config);

      if (state.next.length > 0) {
        // Resume
        return await graph.invoke(null, config);
      } else if (attempt === 0) {
        // Fresh start
        return await graph.invoke(input, config);
      }
    } catch (error) {
      console.log(`Attempt ${attempt + 1} failed:`, error);
      if (attempt === maxRetries - 1) throw error;
      await sleep(1000 * Math.pow(2, attempt));
    }
  }
}
```

## Benefits

1. **Crash recovery**: Resume from last checkpoint
2. **Long tasks**: Handle multi-hour workflows
3. **Rate limits**: Pause and resume
4. **Debugging**: Inspect state at any point
5. **Auditing**: Full execution history
