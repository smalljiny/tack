# Structured Output

Receive LLM output in structured schema format.

## Basic Usage

```typescript
import { z } from "zod";
import { ChatAnthropic } from "@langchain/anthropic";

const model = new ChatAnthropic({ model: "claude-sonnet-4-20250514" });

const responseSchema = z.object({
  answer: z.string().describe("The answer to the question"),
  confidence: z.number().min(0).max(1).describe("Confidence score"),
  sources: z.array(z.string()).describe("Source references"),
});

const structuredModel = model.withStructuredOutput(responseSchema);

const result = await structuredModel.invoke("What is LangChain?");
// { answer: "...", confidence: 0.95, sources: ["..."] }
```

## Complex Schema

```typescript
const analysisSchema = z.object({
  sentiment: z.enum(["positive", "negative", "neutral"]),
  topics: z.array(z.object({
    name: z.string(),
    relevance: z.number(),
  })),
  summary: z.string(),
  metadata: z.object({
    wordCount: z.number(),
    language: z.string(),
  }),
});

const analyzer = model.withStructuredOutput(analysisSchema);
const analysis = await analyzer.invoke("Analyze this text: ...");
```

## With Method Option

```typescript
// JSON mode (faster, less reliable)
const jsonModel = model.withStructuredOutput(schema, {
  method: "jsonMode",
});

// Function calling (more reliable)
const fcModel = model.withStructuredOutput(schema, {
  method: "functionCalling",
});
```

## Include Raw Response

```typescript
const modelWithRaw = model.withStructuredOutput(schema, {
  includeRaw: true,
});

const result = await modelWithRaw.invoke("...");
// result.raw - original response
// result.parsed - structured output
```

## Enum Outputs

```typescript
const classificationSchema = z.enum([
  "bug_report",
  "feature_request",
  "question",
  "other",
]);

const classifier = model.withStructuredOutput(classificationSchema);
const category = await classifier.invoke("I found an error in the code");
// "bug_report"
```

## Optional Fields

```typescript
const flexibleSchema = z.object({
  required: z.string(),
  optional: z.string().optional(),
  withDefault: z.string().default("default value"),
});
```

## Array Output

```typescript
const listSchema = z.array(z.object({
  title: z.string(),
  description: z.string(),
}));

const listModel = model.withStructuredOutput(listSchema);
const items = await listModel.invoke("List 3 programming languages");
```

## In Agent Context

```typescript
const extractorTool = tool(
  async ({ text }) => {
    const extractor = model.withStructuredOutput(entitySchema);
    const entities = await extractor.invoke(`Extract entities from: ${text}`);
    return JSON.stringify(entities);
  },
  {
    name: "extract_entities",
    description: "Extract structured entities from text",
    schema: z.object({ text: z.string() }),
  }
);
```

## Error Handling

```typescript
try {
  const result = await structuredModel.invoke(prompt);
} catch (error) {
  if (error.message.includes("parsing")) {
    // Handle parsing error
    console.log("Failed to parse structured output");
  }
}
```

## Best Practices

1. **Descriptive field names**: Self-documenting schemas
2. **Use `.describe()`**: Help the model understand each field
3. **Reasonable constraints**: `.min()`, `.max()`, `.length()`
4. **Default values**: For optional fields
5. **Test edge cases**: Empty inputs, long texts
