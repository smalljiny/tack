# LangChain/LangGraph Reference Index

Topic-based document routing guide. Select and load documents based on your task.

## Quick Navigation

### Getting Started
| Scenario | Reference |
|----------|-----------|
| Installation and setup | `getting-started/install.md` |
| First agent | `getting-started/quickstart.md` |

### Agent Implementation
| Scenario | Reference |
|----------|-----------|
| Simple React Agent | `agents/react-agent.md` |
| StateGraph basics | `agents/graph-basics.md` |
| Complex graph patterns | `agents/graph-advanced.md` |
| Multi-Agent / Supervisor | `agents/supervisor.md` |

### Memory
| Scenario | Reference |
|----------|-----------|
| Conversation memory (thread-based) | `memory/short-term.md` |
| Persistent storage (cross-thread) | `memory/long-term.md` |

### Streaming
| Scenario | Reference |
|----------|-----------|
| All streaming modes | `streaming/modes.md` |

### Tools
| Scenario | Reference |
|----------|-----------|
| Tool definition (Zod) | `tools/definition.md` |
| Structured Output | `tools/structured-output.md` |

### Advanced Patterns
| Scenario | Reference |
|----------|-----------|
| Human-in-the-Loop | `patterns/human-in-the-loop.md` |
| Subgraph composition | `patterns/subgraphs.md` |
| Workflow vs Agent | `patterns/workflows-agents.md` |

### Integrations
| Scenario | Reference |
|----------|-----------|
| Anthropic (Claude) | `integrations/anthropic.md` |
| OpenAI (GPT) | `integrations/openai.md` |
| Google (Gemini) | `integrations/google.md` |
| Azure OpenAI | `integrations/azure.md` |
| AWS Bedrock | `integrations/bedrock.md` |

### Middleware
| Scenario | Reference |
|----------|-----------|
| Middleware overview | `middleware/overview.md` |

### Advanced Features
| Scenario | Reference |
|----------|-----------|
| Context Engineering | `advanced/context-engineering.md` |
| Persistence | `advanced/persistence.md` |
| Durable Execution | `advanced/durable-execution.md` |

### Deep Agents
| Scenario | Reference |
|----------|-----------|
| Deep Agent overview | `deepagents/overview.md` |
| Deep Agent quickstart | `deepagents/quickstart.md` |
| Customization | `deepagents/customization.md` |

### Migration
| Scenario | Reference |
|----------|-----------|
| LangChain v0.2 → v1 | `migration/langchain-v1.md` |
| LangGraph v0 → v1 | `migration/langgraph-v1.md` |

## Search Patterns

Use these to find specific sections in large files:

```bash
# State definition
grep -n "Annotation\|StateGraph\|z.object" <file>

# Edge-related
grep -n "addEdge\|addConditionalEdges\|Command\|Send" <file>

# Memory-related
grep -n "MemorySaver\|InMemoryStore\|checkpointer\|store" <file>

# Streaming
grep -n "streamMode\|streamEvents\|for await" <file>
```
