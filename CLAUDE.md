# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AgentFiscoAI is an Italian fiscal/tax law research agent built on LangGraph and LangChain. It answers complex tax questions by decomposing them into sub-problems, conducting iterative RAG searches across regulatory documents (circolari, giurisprudenza, risoluzioni, norme, provvedimenti), and synthesizing findings into comprehensive answers.

**Domain language**: Italian (prompts, document types, user queries are all in Italian).

## Setup & Running

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
# Ensure .env is configured with Azure OpenAI, Qdrant, MongoDB, Tavily, LangSmith keys
```

### Run the main workflow
```python
from src.graph.think.todo import todo_workflow
result = todo_workflow.invoke({
    "messages": [], "input": "Your question", "response_moment": "", "list_fonte": [], "plan": []
})
```

### Run the scope (intent clarification) graph
```python
from src.graph.scope.scope_graph import scope_research
from langchain_core.messages import HumanMessage
result = scope_research.invoke({"messages": [HumanMessage(content="Your question")]}, config={"configurable": {"thread_id": "1"}})
```

### Visualize the workflow graph
```bash
python get_graph.py    # Print Mermaid diagram
python save_graph.py   # Save as PNG (requires graphviz)
```

Most modules have `if __name__ == "__main__"` blocks for standalone testing.

## Architecture

The system uses a **plan-execute-replan** loop with strategic thinking:

```
User Input
    |
[Scope Graph]  -- clarify intent, generate research brief
    |
[Plan-Execute-Replan Loop]:
    pre_thinker  -> deep strategic analysis of the question
    planner      -> generate ordered research steps
    agent        -> execute RAG search for current step
    post_thinker -> re-analyze based on findings
    replan       -> decide: more research needed or generate final response?
        |-> loop back to agent (max ~5 iterations)
        |-> generate final response via response_llm
```

### Key modules

- **`src/graph/think/todo.py`** — Main orchestrator. Defines `PlanExecute` state, the plan-execute-replan graph, and `todo_workflow` (the compiled LangGraph).
- **`src/graph/think/thinker.py`** — Strategic analysis agent. Decomposes questions, identifies gaps, evaluates research quality.
- **`src/graph/think/response.py`** — Final answer generation from accumulated research.
- **`src/graph/research/search_graph.py`** — RAG search agent using `create_agent` with `rag_query` and `rag_query_norma_specifica` tools.
- **`src/graph/research/tools.py`** — Core RAG tools: hybrid search via Qdrant, source extraction, summary writing, response reasoning updates.
- **`src/graph/research/estrazione.py`** — Extracts structured `Fonte` objects from different document types, enriched via MongoDB lookups.
- **`src/graph/research/content_intent.py`** — Detects specific norm citations (anno/numero/articolo) in queries.
- **`src/graph/research/rewrting.py`** — Query rewriting for better embedding/keyword match.
- **`src/graph/scope/scope_graph.py`** — Intent clarification graph with checkpointer for multi-turn conversation.
- **`src/services/qdrant.py`** — `QdrantHybridRetriever`: hybrid search (dense embeddings + BM25 via RRF fusion) on "norme" collection.
- **`src/services/mongodb.py`** — Document storage/retrieval for circolari, giurisprudenza, risoluzioni, norme chunks.
- **`src/services/embeddings.py`** — Azure OpenAI `text-embedding-3-small` wrapper.
- **`src/subagents/`** — Specialized sub-agents (websearch via Tavily, calculator, todo planner).

### State model

The `Fonte` class (`src/graph/research/state.py`) is the core data unit representing a retrieved source document, with fields: `mongo_id`, `id`, `original_text`, `ricostruito_testo` (reconstructed text chunks), `tipo`, `score`, `data`, `url`, `cites`.

`PlanExecute` state accumulates `past_steps` (via `operator.add` reducer) and `list_fonte` across the replan loop.

## Infrastructure Dependencies

- **Azure OpenAI** (`gpt-4.1-mini` deployment) — all LLM calls (planning, thinking, response)
- **OpenAI** (`gpt-4.1-mini`, `gpt-5-mini`) — RAG agent, summary/response writing
- **Qdrant** (`http://100.77.246.20:6333`) — vector DB, collection "norme", hybrid search
- **MongoDB** (`mongodb://100.77.246.20:27017/`, db `vertical_ai`) — document storage
- **Tavily** — web search in subagent
- **LangSmith** (EU endpoint) — tracing under project "FISCOAI"

## Code Patterns

- Every module adds project root to `sys.path` and calls `load_dotenv()` at the top.
- Pydantic V1 deprecation warnings are suppressed throughout (`warnings.filterwarnings`).
- LangGraph state uses `Annotated` types with reducers for list fields (e.g., `operator.add` for `past_steps`).
- Tools use `@tool(parse_docstring=True)` with `InjectedState` and `InjectedToolCallId` for state access, returning `Command(update={...})`.
- The RAG search pipeline: query rewriting -> intent detection -> hybrid Qdrant search -> MongoDB enrichment -> deduplication -> sorted top-10 results.
- Document types: `circolare`, `giurisprudenza`, `risoluzione`, `provvedimento`, `norma`.
