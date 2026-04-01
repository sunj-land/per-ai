# Intelligent Agent System

This directory contains the implementation of the Layered Intelligent Agent System.

## Architecture

The system consists of:
1.  **Master Agent**: The entry point that orchestrates the workflow.
    -   **Intent Classifier**: Uses LLM to determine if the user wants to search articles or chat.
    -   **Router**: Routes requests to Sub-Agents or General Chat.
2.  **Sub-Agents**:
    -   **Article Query Agent**: Specialized in semantic search over local documentation/articles using ChromaDB.
3.  **Communication Protocol**: Standardized `AgentRequest` and `AgentResponse` using Pydantic.
4.  **Monitoring**: Real-time metrics logging and visualization.

## Prerequisites

-   Python 3.10+
-   Ollama (running locally on port 11434)
-   ChromaDB (integrated)

## Installation

Ensure all dependencies are installed:
```bash
pip install -r ../requirements.txt
```

## Running the System

### 1. Start the Backend API
The Agent API is integrated into the main backend application.

```bash
cd ../backend
uvicorn app.main:app --reload
```

Swagger UI will be available at: http://localhost:8000/docs

### 2. Start the Admin Dashboard
Monitor agent performance and inspect the vector store.

```bash
cd ../backend
streamlit run admin_dashboard.py
```

## API Documentation

### Query Agent

**Endpoint**: `POST /api/v1/agents/query`

**Request Body**:
```json
{
  "query": "How to configure RSS feeds?",
  "session_id": "optional-uuid",
  "history": []
}
```

**Response**:
```json
{
  "answer": "To configure RSS feeds...",
  "source_agent": "article_search",
  "latency_ms": 120.5,
  "metadata": { ... }
}
```

## Testing

Run the unit and integration tests:

```bash
python3 -m unittest discover agents/tests
```

## Deployment

1.  **Environment**: Ensure `OPENAI_API_KEY` is set if using OpenAI, or Ollama is running for local models.
2.  **Vector Store**: The system uses a local ChromaDB instance in `backend/data/chroma`. Ensure this directory is persistent.
3.  **Logs**: Metrics are logged to `backend/logs/agent_metrics.jsonl`. Configure log rotation if necessary.

## Exception Handling

-   **Retries**: External LLM calls are retried automatically (default 3 times).
-   **Timeouts**: Agent tasks have strict timeouts (5s for classification, 10s for search).
-   **Degradation**: If intent classification fails, the system defaults to General Chat to ensure a response.
