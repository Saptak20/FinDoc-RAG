# FinDoc-RAG (Financial Document RAG)

This project implements a Retrieval-Augmented Generation (RAG) system for financial documents, orchestrated using **LangGraph** and utilizing local **Ollama** LLMs and embedding models instead of external paid APIs.

---

## Architecture Overview

```mermaid
flowchart TD
    subgraph Ingestion
        A[PDF/TXT Document] --> B[scripts/index_documents.py]
        B --> C[app/engine/ingestion/ingest.py]
        C -->|Embedding nomic-embed-text| D[Ollama Embedding Engine]
        C -->|Save Embeddings| E[(PostgreSQL + pgvector)]
    end

    subgraph Chat Query (RAG Pipeline)
        F[Client Message] --> G[FastAPI /api/v1/chat/]
        G --> H[app/engine/pipelines.py - LangGraph]
        H -->|1. Retrieve Context| I[app/engine/retrieval/retriever.py]
        I -->|Cosine Similarity Search| E
        H -->|2. Generate Answer| J[app/engine/generation/llm.py]
        J -->|LLM llama3.2| K[Ollama Chat Engine]
        K -->|Formulated Response| G
    end
```

---

## Setup Instructions

### 1. Prerequisites
- **Python**: Version 3.10 or higher.
- **Ollama**: Running locally.
- **PostgreSQL**: With `pgvector` extension installed/enabled.

### 2. Local Ollama Models
Make sure Ollama is running, and pull the required models:
```bash
# Chat generation model (Llama 3.2 3B)
ollama pull llama3.2

# Semantic search embedding model
ollama pull nomic-embed-text
```

### 3. Installation
1. Create and activate a Python virtual environment:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### 4. Configuration
Create a `.env` file in the root directory (one has been pre-configured for you):
```env
DATABASE_URL="postgresql://postgres:postgres@localhost:5432/findoc"
OLLAMA_BASE_URL="http://localhost:11434"
OLLAMA_LLM_MODEL="llama3.2"
OLLAMA_EMBED_MODEL="nomic-embed-text"
```

### 5. Document Ingestion
Place your financial documents (PDF or TXT) into the `data/` folder, then run:
```bash
python -m scripts.index_documents
```
*Note: This will connect to Postgres, automatically create the schemas/pgvector tables, compute embeddings via Ollama, and index the document chunks.*

### 6. Run FastAPI Server
Start the development server:
```bash
uvicorn app.main:app --reload
```
You can access the interactive API docs at `http://localhost:8000/docs` to test endpoints like `/api/v1/documents/upload` or `/api/v1/chat/`.
