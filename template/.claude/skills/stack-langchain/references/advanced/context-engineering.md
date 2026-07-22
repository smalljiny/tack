# Context Engineering

Efficiently manage the LLM context window.

## Core Strategies

### 1. Summarization

Save context by summarizing long conversations.

```typescript
import { trimMessages } from "@langchain/core/messages";

const trimmedMessages = await trimMessages(messages, {
  maxTokens: 4000,
  strategy: "last",  // Keep last messages
  tokenCounter: (msgs) => msgs.length * 4,  // Approximate
});
```

### 2. Sliding Window

Keep only the last N messages.

```typescript
const windowSize = 10;
const recentMessages = messages.slice(-windowSize);
```

### 3. Selective Loading

Load only relevant information into context.

```typescript
async function loadRelevantContext(query: string, allDocs: Document[]) {
  const embeddings = new OpenAIEmbeddings();
  const queryVector = await embeddings.embedQuery(query);

  // Find most relevant docs
  const relevant = allDocs
    .map((doc) => ({
      doc,
      similarity: cosineSimilarity(queryVector, doc.vector),
    }))
    .sort((a, b) => b.similarity - a.similarity)
    .slice(0, 3);

  return relevant.map((r) => r.doc);
}
```

## Message Management

### Trim by Token Count

```typescript
import { trimMessages } from "@langchain/core/messages";

const trimmed = await trimMessages(messages, {
  maxTokens: 4000,
  strategy: "last",
  includeSystem: true,  // Always keep system message
  allowPartial: false,
});
```

### Summarize Old Messages

```typescript
async function summarizeHistory(messages: BaseMessage[]) {
  const oldMessages = messages.slice(0, -5);
  const recentMessages = messages.slice(-5);

  if (oldMessages.length > 10) {
    const summary = await summarizer.invoke(
      `Summarize this conversation: ${formatMessages(oldMessages)}`
    );

    return [
      new SystemMessage(`Previous conversation summary: ${summary}`),
      ...recentMessages,
    ];
  }

  return messages;
}
```

## RAG Context

### Chunk Size Optimization

```typescript
import { RecursiveCharacterTextSplitter } from "@langchain/textsplitters";

const splitter = new RecursiveCharacterTextSplitter({
  chunkSize: 1000,      // Characters per chunk
  chunkOverlap: 200,    // Overlap for continuity
  separators: ["\n\n", "\n", " ", ""],
});

const chunks = await splitter.splitDocuments(documents);
```

### Reranking

```typescript
async function rerankResults(query: string, results: Document[]) {
  const reranker = new CohereRerank();
  const reranked = await reranker.compressDocuments(results, query);
  return reranked.slice(0, 3);  // Top 3
}
```

## Tool Output Management

### Truncate Long Results

```typescript
const searchTool = tool(
  async ({ query }) => {
    const results = await search(query);

    // Truncate if too long
    const maxLength = 2000;
    if (results.length > maxLength) {
      return results.slice(0, maxLength) + "\n[Truncated...]";
    }
    return results;
  },
  { name: "search", schema: z.object({ query: z.string() }) }
);
```

### Summarize Tool Output

```typescript
const longOutputTool = tool(
  async ({ query }, config) => {
    const rawResult = await fetchLongData(query);

    if (rawResult.length > 3000) {
      const summary = await summarizer.invoke(
        `Summarize: ${rawResult.slice(0, 5000)}`
      );
      return `[Summary] ${summary}`;
    }
    return rawResult;
  },
  { name: "long_data", schema: z.object({ query: z.string() }) }
);
```

## State Optimization

### Selective State

```typescript
const OptimizedState = z.object({
  // Keep full messages
  messages: z.array(z.custom<BaseMessage>()),

  // Only essential metadata
  currentStep: z.string(),

  // Summary instead of full data
  contextSummary: z.string(),
});
```

### State Pruning

```typescript
function pruneState(state: State): State {
  return {
    ...state,
    messages: state.messages.slice(-10),
    intermediateResults: [],  // Clear temporary data
  };
}
```

## Best Practices

1. **Token budget**: Reserve tokens for output
2. **System message**: Keep concise
3. **Tool descriptions**: Short but clear
4. **Chunking**: Balance size vs context
5. **Caching**: Cache embeddings and summaries
