# Tool Definition

Define tools for agents to use.

## Basic Tool (Zod Schema)

```typescript
import { tool } from "@langchain/core/tools";
import { z } from "zod";

const searchTool = tool(
  async ({ query }) => {
    // Implementation
    return `Results for: ${query}`;
  },
  {
    name: "search",
    description: "Search the web for information",
    schema: z.object({
      query: z.string().describe("Search query"),
    }),
  }
);
```

## Multi-parameter Tool

```typescript
const calculatorTool = tool(
  async ({ a, b, operation }) => {
    switch (operation) {
      case "add": return a + b;
      case "subtract": return a - b;
      case "multiply": return a * b;
      case "divide": return a / b;
    }
  },
  {
    name: "calculator",
    description: "Perform arithmetic operations",
    schema: z.object({
      a: z.number().describe("First number"),
      b: z.number().describe("Second number"),
      operation: z.enum(["add", "subtract", "multiply", "divide"]),
    }),
  }
);
```

## Tool with Config Access

```typescript
const userTool = tool(
  async ({ action }, config) => {
    const userId = config.configurable?.userId;
    const store = config.store;

    // Access runtime config
    return `User ${userId}: ${action}`;
  },
  {
    name: "user_action",
    description: "Perform user-specific action",
    schema: z.object({
      action: z.string(),
    }),
  }
);
```

## Dynamic Structured Tool

```typescript
import { DynamicStructuredTool } from "@langchain/core/tools";

const dynamicTool = new DynamicStructuredTool({
  name: "database_query",
  description: "Query the database",
  schema: z.object({
    table: z.string(),
    filter: z.record(z.any()).optional(),
  }),
  func: async ({ table, filter }) => {
    // Implementation
  },
});
```

## Tool with State Update (Command)

```typescript
import { Command } from "@langchain/langgraph";

const statefulTool = tool(
  async (input, config) => {
    const result = await doSomething(input);

    return new Command({
      update: {
        customState: result,
        messages: [{
          role: "tool",
          content: "Done",
          tool_call_id: config.toolCall.id,
        }],
      },
    });
  },
  {
    name: "stateful_action",
    description: "Action that updates state",
    schema: z.object({ data: z.string() }),
  }
);
```

## Tool with Streaming

```typescript
const streamingTool = tool(
  async ({ query }, config) => {
    config.writer({ type: "progress", value: 0 });

    const results = [];
    for (let i = 0; i < 10; i++) {
      results.push(await fetchPage(query, i));
      config.writer({ type: "progress", value: (i + 1) * 10 });
    }

    return results.join("\n");
  },
  {
    name: "paginated_search",
    description: "Search with progress updates",
    schema: z.object({ query: z.string() }),
  }
);
```

## Using Tools with Agent

```typescript
import { createReactAgent } from "@langchain/langgraph/prebuilt";

const agent = createReactAgent({
  llm: model,
  tools: [searchTool, calculatorTool, userTool],
});
```

## Tool Binding to Model

```typescript
const modelWithTools = model.bindTools([searchTool, calculatorTool]);

const response = await modelWithTools.invoke("Search for LangChain");
// response.tool_calls contains tool call info
```

## Best Practices

1. **Clear descriptions**: Help the model understand when to use the tool
2. **Specific schemas**: Use `.describe()` for each parameter
3. **Error handling**: Return meaningful error messages
4. **Idempotent**: Tools should be safe to retry
