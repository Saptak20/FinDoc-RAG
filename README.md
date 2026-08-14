Absolutely. Here is the **complete updated `README.md`** ready to copy-paste.

````markdown
# FinDoc-RAG

<div align="center">

### Local-First Hybrid Retrieval-Augmented Generation for Financial Documents

**Private. Local. Explainable. Built for dense financial data.**

A production-oriented RAG system for analyzing annual reports, SEC filings, and other financial documents using **Ollama, FAISS, BM25, LangGraph, FastAPI, and PostgreSQL**.

<br>

![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-Async-009688?logo=fastapi&logoColor=white)
![LangChain](https://img.shields.io/badge/LangChain-RAG-1C3C3C)
![LangGraph](https://img.shields.io/badge/LangGraph-Orchestration-orange)
![Ollama](https://img.shields.io/badge/Ollama-Local_AI-black)
![FAISS](https://img.shields.io/badge/FAISS-Vector_Search-blueviolet)
![BM25](https://img.shields.io/badge/BM25-Sparse_Retrieval-green)
![Cross-Encoder](https://img.shields.io/badge/Cross--Encoder-Reranking-red)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Async-4169E1?logo=postgresql&logoColor=white)
![Status](https://img.shields.io/badge/Status-Active_Development-yellow)

</div>

---

## Overview

**FinDoc-RAG** is a local-first Retrieval-Augmented Generation system designed for querying large and information-dense financial documents.

The system transforms financial PDFs into structured, searchable knowledge by combining:

- **Dense semantic retrieval** with FAISS
- **Sparse lexical retrieval** with BM25
- **Reciprocal Rank Fusion (RRF)**
- **Cross-encoder reranking**
- **Local LLM inference** through Ollama
- **LangGraph-based RAG orchestration**
- **FastAPI application layer**
- **PostgreSQL / SQLAlchemy infrastructure**

The primary design goal is to build a financial document intelligence system where sensitive documents, embeddings, retrieval indexes, retrieved context, and LLM inference can remain on local infrastructure.

> **Core architectural principle:** FAISS and BM25 operate on the same canonical document chunks using deterministic `chunk_id` values.

---

# Architecture

```mermaid
flowchart TB

    DOC["Financial PDFs<br/>Annual Reports • 10-K • 10-Q"]

    subgraph INGESTION["Offline Ingestion Pipeline"]
        LOAD["PDF Loader<br/>DirectoryLoader + PyPDFLoader"]
        CHUNK["Recursive Chunking<br/>Chunk Size + Overlap"]
        ID["Stable Chunk Identity<br/>chunk_id + chunk_index"]

        LOAD --> CHUNK
        CHUNK --> ID
    end

    subgraph STORAGE["Persistent Retrieval Storage"]
        CORPUS[("Canonical Chunk Corpus<br/>chunks.jsonl")]
        FAISS[("FAISS Vector Index<br/>index.faiss + index.pkl")]
    end

    subgraph EMBEDDING["Local Embedding Infrastructure"]
        OLLAMA_EMBED["Ollama<br/>nomic-embed-text<br/>768 Dimensions"]
    end

    DOC --> LOAD
    ID --> CORPUS
    ID --> OLLAMA_EMBED
    OLLAMA_EMBED --> FAISS

    QUERY["User Financial Query"]

    subgraph RETRIEVAL["Hybrid Retrieval Engine"]
        DENSE["Dense Retriever<br/>FAISS Semantic Search"]
        SPARSE["Sparse Retriever<br/>BM25 Lexical Search"]
        FUSION["RRF Rank Fusion<br/>Deduplication by chunk_id"]
        RERANK["Cross-Encoder Reranker"]

        DENSE --> FUSION
        SPARSE --> FUSION
        FUSION --> RERANK
    end

    QUERY --> DENSE
    QUERY --> SPARSE
    FAISS --> DENSE
    CORPUS --> SPARSE

    subgraph GENERATION["LangGraph RAG Generation"]
        CONTEXT["Context Builder"]
        LLM["Ollama<br/>llama3.2:3b"]
        VALIDATE["Grounding / Output Validation"]

        CONTEXT --> LLM
        LLM --> VALIDATE
    end

    RERANK --> CONTEXT

    subgraph API["Application Layer"]
        FASTAPI["FastAPI<br/>/api/v1/chat"]
        LANGGRAPH["LangGraph<br/>RAG Orchestrator"]
    end

    FASTAPI --> LANGGRAPH
    LANGGRAPH --> RETRIEVAL
    VALIDATE --> FASTAPI

    subgraph DATABASE["Observability / Persistence"]
        POSTGRES[("PostgreSQL<br/>Query / Response / Latency")]
    end

    VALIDATE --> POSTGRES
````

---

# End-to-End RAG Flow

```text
User Question
     │
     ▼
FastAPI /api/v1/chat
     │
     ▼
LangGraph
     │
     ▼
Hybrid Retrieval
 ┌───────────────┐
 │               │
 ▼               ▼
FAISS           BM25
Semantic        Lexical
Search          Search
 │               │
 └───────┬───────┘
         ▼
    RRF Rank Fusion
         │
         ▼
 Cross-Encoder Reranker
         │
         ▼
   Final Context
         │
         ▼
 Ollama Llama 3.2 3B
         │
         ▼
 Grounded Answer
         │
         ▼
 Sources + Page + Chunk ID
```

The retrieval stack is deliberately layered:

* **FAISS** maximizes semantic recall.
* **BM25** captures exact lexical matches.
* **RRF** combines independent rankings without comparing incompatible score scales.
* **Cross-Encoder** performs precision-oriented reranking on the smaller candidate set.
* **Ollama** generates the final grounded response from the selected context.

---

# How It Works

## 1. Document Ingestion

Financial PDFs are placed inside:

```text
data/raw/
```

The ingestion pipeline performs:

```text
PDF
 ↓
Load Pages
 ↓
Recursive Chunking
 ↓
Assign Stable Chunk IDs
 ↓
 ┌──────────────────────┐
 ▼                      ▼
Canonical Corpus     Local Embeddings
chunks.jsonl         nomic-embed-text
                         ↓
                       FAISS
```

Each chunk receives a deterministic identity:

```text
<filename>::page_<page>::chunk_<index>::<hash>
```

Example:

```text
OTC_TATLY_2024.pdf::page_219::chunk_3::a81f29c4e291
```

Stable chunk IDs are used for:

* retrieval synchronization
* deduplication
* debugging
* evaluation
* cross-store consistency

---

## 2. Canonical Chunk Corpus

The canonical text corpus is stored in:

```text
data/vector_store/chunks.jsonl
```

This file represents the exact chunk collection used by the retrieval system.

Both retrieval paths operate against the same underlying chunks:

```text
                 Canonical Chunks
                       │
             ┌─────────┴─────────┐
             ▼                   ▼
          FAISS                 BM25
       Vector View            Text View
```

This prevents the dense and sparse retrieval systems from drifting apart.

---

## 3. Dense Semantic Retrieval

The dense retrieval pipeline uses:

```text
User Query
    ↓
Ollama Embedding
    ↓
768-D Query Vector
    ↓
FAISS Similarity Search
    ↓
Top-K Semantic Candidates
```

Dense retrieval is useful when the query and relevant document text express similar concepts using different wording.

---

## 4. Sparse Lexical Retrieval

BM25 searches the canonical `chunks.jsonl` corpus.

It complements semantic retrieval by providing strong lexical matching for:

* Company names
* Financial terminology
* Ticker symbols
* Dates and fiscal years
* Named entities
* Exact phrases
* Rare financial terms
* Specific numerical terminology

For example, a query containing **EBITDA** benefits from direct lexical matching even when the surrounding wording differs.

---

## 5. Hybrid Retrieval

The hybrid retrieval layer combines FAISS and BM25:

```text
                 User Query
                      │
             ┌────────┴────────┐
             ▼                 ▼
      Dense Retrieval    Sparse Retrieval
           FAISS               BM25
             │                 │
             └────────┬────────┘
                      ▼
                RRF Rank Fusion
                      ↓
             Deduplication
                by chunk_id
                      ↓
             Cross-Encoder
                Reranking
                      ↓
               Final Context
```

This provides better retrieval coverage than relying exclusively on either semantic or keyword search.

### Why RRF?

FAISS and BM25 produce different score types and scales. Instead of adding those incompatible raw scores together, FinDoc-RAG uses **Reciprocal Rank Fusion**:

```text
RRF(d) = Σ 1 / (k + rank)
```

This combines the **rank positions** produced by each retrieval system.

---

## 6. Cross-Encoder Reranking

The cross-encoder does not search the entire corpus.

It receives only the relatively small candidate set produced by hybrid retrieval:

```text
2,710 corpus chunks
       ↓
FAISS + BM25
       ↓
RRF Fusion
       ↓
~10–20 candidates
       ↓
Cross-Encoder
       ↓
Final 3–5 chunks
```

Configured model:

```text
cross-encoder/ms-marco-MiniLM-L-6-v2
```

The cross-encoder evaluates:

```text
(query, document_chunk)
```

as a pair, providing a more precise relevance score than the initial retrieval stages.

The current implementation automatically uses CUDA when available and falls back to CPU otherwise.

---

# RAG Generation with LangGraph

The generation workflow is orchestrated using LangGraph:

```text
START
  ↓
Validate Query
  ↓
Retrieve
  ↓
Rerank
  ↓
Build Context
  ↓
Generate Answer
  ↓
Validate Grounding
  ↓
END
```

The generation model currently runs locally through Ollama:

```text
llama3.2:3b
```

The generation prompt instructs the model to:

* Use only the supplied retrieved context.
* Avoid inventing financial facts.
* Admit when the context is insufficient.
* Preserve source/page information.
* Produce concise, grounded answers.

---

# API Layer

FinDoc-RAG exposes the RAG pipeline through FastAPI.

### Main endpoints

| Method | Endpoint       | Purpose                                   |
| ------ | -------------- | ----------------------------------------- |
| `GET`  | `/`            | Application status                        |
| `GET`  | `/health`      | Lightweight health check                  |
| `POST` | `/api/v1/chat` | Financial document question answering     |
| `GET`  | `/docs`        | Interactive Swagger/OpenAPI documentation |

### Example Request

```json
{
  "query": "What was Tata Steel's EBITDA margin in FY2023-24?",
  "dense_top_k": 10,
  "sparse_top_k": 10,
  "final_top_k": 3
}
```

### Example Response

```json
{
  "query": "What was Tata Steel's EBITDA margin in FY2023-24?",
  "answer": "According to the provided financial document context, Tata Steel's standalone EBITDA margin in FY2023-24 was 22%.",
  "sources": [
    {
      "source": "OTC_TATLY_2024.pdf",
      "page": 14,
      "chunk_id": "OTC_TATLY_2024.pdf::page_14::chunk_3::c6a111a9b067"
    }
  ],
  "metrics": {
    "retrieval_candidates": 10,
    "reranked_chunks": 3,
    "latency_seconds": 8.85
  }
}
```

---

# Current Pipeline Statistics

The current development corpus is a Tata Steel annual report used for ingestion, retrieval, and end-to-end RAG testing.

| Metric                          |  Result |
| ------------------------------- | ------: |
| PDF Pages Loaded                |     581 |
| Document Chunks                 |   2,710 |
| Unique Chunk IDs                |   2,710 |
| Embedding Dimensions            |     768 |
| FAISS Vectors                   |   2,710 |
| Canonical Corpus Entries        |   2,710 |
| Cross-Store Coverage            |    100% |
| Hybrid Candidates in RAG Test   |      10 |
| Final Reranked Chunks           |       3 |
| End-to-End RAG Latency          | ~2.88 s |
| Cross-Encoder Reranking Latency | ~244 ms |

The ingestion pipeline has also been successfully restored and verified on the EndeavourOS development environment.

---

# Tech Stack

| Layer             | Technology                          |
| ----------------- | ----------------------------------- |
| Language          | Python 3.12                         |
| API               | FastAPI                             |
| AI Orchestration  | LangGraph                           |
| RAG Components    | LangChain                           |
| Local AI Runtime  | Ollama                              |
| Embeddings        | `nomic-embed-text`                  |
| Dense Retrieval   | FAISS                               |
| Sparse Retrieval  | BM25 / `rank-bm25`                  |
| Rank Fusion       | Reciprocal Rank Fusion              |
| Reranking         | Sentence-Transformers Cross-Encoder |
| Generation        | `llama3.2:3b`                       |
| Database          | PostgreSQL                          |
| ORM               | SQLAlchemy Async                    |
| PostgreSQL Driver | asyncpg                             |
| Configuration     | Pydantic Settings                   |
| Document Parsing  | PyPDFLoader                         |
| Testing           | Pytest                              |

---

# Project Structure

```text
FinDoc-RAG/
│
├── app/
│   ├── api/
│   │   ├── dependencies.py
│   │   └── routes/
│   │       └── chat.py
│   │
│   ├── core/
│   │   ├── config.py
│   │   └── logger.py
│   │
│   ├── db/
│   │   ├── models.py
│   │   └── session.py
│   │
│   ├── engine/
│   │   ├── ingestion/
│   │   │   ├── ingestor.py
│   │   │   └── chunk_store.py
│   │   │
│   │   ├── retrieval/
│   │   │   ├── retriever.py
│   │   │   ├── bm25_retriever.py
│   │   │   ├── rank_fusion.py
│   │   │   ├── hybrid_retriever.py
│   │   │   └── reranker.py
│   │   │
│   │   ├── generation/
│   │   │   └── llm.py
│   │   │
│   │   └── pipelines.py
│   │
│   ├── schemas/
│   │   └── chat.py
│   │
│   └── main.py
│
├── data/
│   ├── raw/
│   └── vector_store/
│       ├── index.faiss
│       ├── index.pkl
│       └── chunks.jsonl
│
├── scripts/
│   └── index_documents.py
│
├── tests/
│   ├── test_api.py
│   ├── test_bm25_retriever.py
│   ├── test_hybrid_retriever.py
│   ├── test_rag_pipeline.py
│   ├── test_rank_fusion.py
│   └── test_reranker.py
│
├── evaluation/
├── requirements.txt
├── .env
└── README.md
```

> Generated local retrieval artifacts and private financial documents should normally remain outside version control.

---

# Getting Started

## 1. Prerequisites

Make sure the following are installed:

* Python 3.12
* Miniconda or Anaconda
* Ollama
* PostgreSQL
* Git

---

## 2. Clone the Repository

```bash
git clone <your-repository-url>
cd FinDoc-RAG
```

---

## 3. Create the Conda Environment

```bash
conda create -n findoc-rag python=3.12
conda activate findoc-rag
```

Install dependencies:

```bash
pip install -r requirements.txt
```

---

## 4. Install Ollama Models

Make sure Ollama is running locally.

Pull the embedding model:

```bash
ollama pull nomic-embed-text
```

Pull the configured generation model:

```bash
ollama pull llama3.2:3b
```

Verify:

```bash
ollama list
```

The cross-encoder model:

```text
cross-encoder/ms-marco-MiniLM-L-6-v2
```

is downloaded and cached automatically by `sentence-transformers` on first use.

---

## 5. Environment Configuration

Create a `.env` file in the project root.

Example:

```env
APP_NAME=FinDoc-RAG
APP_ENV=development
DEBUG=true

OLLAMA_BASE_URL=http://localhost:11434
LLM_MODEL=llama3.2:3b
EMBEDDING_MODEL=nomic-embed-text
RERANKER_MODEL=cross-encoder/ms-marco-MiniLM-L-6-v2

DATABASE_URL=postgresql://<username>:<password>@localhost:5432/findoc_rag

RAW_DATA_PATH=./data/raw
VECTOR_STORE_PATH=./data/vector_store

CHUNK_SIZE=1000
CHUNK_OVERLAP=200

TOP_K=10
FINAL_CONTEXT_K=3
```

> Never commit real secrets, passwords, API keys, or private credentials to Git.

---

# Document Ingestion

Place financial PDF documents inside:

```text
data/raw/
```

Supported document categories include:

* Annual reports
* SEC 10-K filings
* SEC 10-Q filings
* Earnings reports
* Financial disclosures

Run:

```bash
python scripts/index_documents.py
```

The pipeline performs:

```text
Load PDFs
    ↓
Split into Chunks
    ↓
Assign Stable Chunk IDs
    ↓
Save Canonical Chunk Corpus
    ↓
Generate Embeddings in Controlled Batches
    ↓
Build FAISS Index
    ↓
Persist Retrieval Assets
```

Generated retrieval artifacts:

```text
data/vector_store/
├── chunks.jsonl
├── index.faiss
└── index.pkl
```

---

# Running the API

Start the FastAPI development server:

```bash
uvicorn app.main:app --reload
```

Health check:

```text
GET /health
```

Interactive API documentation:

```text
GET /docs
```

Chat endpoint:

```text
POST /api/v1/chat
```

---

# Testing

The project contains focused tests for the major RAG components.

Run the full test suite with:

```bash
pytest
```

Major tested components include:

* BM25 retrieval
* RRF rank fusion
* Hybrid retrieval
* Cross-encoder reranking
* LangGraph RAG pipeline
* FastAPI API layer

The current development milestones have been validated against the live 2,710-chunk financial corpus.

---

# Development Progress

## Milestone 1 — Core Foundation

**Status: Complete**

* [x] Project architecture
* [x] Conda environment
* [x] Pydantic configuration
* [x] Application logging
* [x] FastAPI foundation
* [x] Health endpoint

---

## Milestone 2 — Database & Ingestion Infrastructure

**Status: Complete**

* [x] Async PostgreSQL connection
* [x] SQLAlchemy session management
* [x] Query logging model
* [x] PDF loading
* [x] Recursive document chunking
* [x] Deterministic chunk IDs
* [x] Local Ollama embeddings
* [x] Batched embedding pipeline
* [x] FAISS index creation
* [x] FAISS persistence and reload
* [x] Canonical JSONL chunk corpus
* [x] Cross-store consistency validation

---

## Milestone 3 — Hybrid Retrieval Engine

**Status: Complete**

* [x] Dense FAISS retrieval
* [x] Semantic retrieval testing
* [x] BM25 sparse retrieval
* [x] RRF rank fusion
* [x] Chunk-level deduplication
* [x] Hybrid retrieval
* [x] Hybrid retrieval integration testing

---

## Milestone 4 — Cross-Encoder Reranking

**Status: Complete**

* [x] Cross-encoder model integration
* [x] CUDA/CPU device detection
* [x] Candidate-pair scoring
* [x] Precision-oriented reranking
* [x] RRF score preservation
* [x] Source tracking preservation
* [x] Reranker integration testing

---

## Milestone 5 — LangGraph RAG Generation

**Status: Complete**

* [x] Typed LangGraph state
* [x] Query validation
* [x] Hybrid retrieval node
* [x] Cross-encoder reranking node
* [x] Context construction
* [x] Local Ollama generation
* [x] Grounding/output validation
* [x] Source metadata tracking
* [x] End-to-end RAG testing

---

## Milestone 6 — FastAPI Application Layer

**Status: Complete**

* [x] Pydantic chat schemas
* [x] `/api/v1/chat`
* [x] `/health`
* [x] Root endpoint
* [x] Swagger/OpenAPI documentation
* [x] RAG pipeline integration
* [x] Request validation
* [x] HTTP error handling
* [x] Response formatting
* [x] Performance metrics
* [x] API integration tests

---

## Milestone 7 — Production Hardening

**Status: Next**

* [ ] Retrieval evaluation dataset
* [ ] Retrieval quality metrics
* [ ] RAG answer evaluation
* [ ] Observability improvements
* [ ] Robustness and failure testing
* [ ] Performance optimization
* [ ] Production configuration review
* [ ] Dockerization
* [ ] CI/CD
* [ ] Deployment readiness

---

# Privacy-First Architecture

FinDoc-RAG follows a **local-first processing model**.

The following components can remain entirely on the user's machine:

```text
Financial Documents
        +
Document Chunks
        +
Embeddings
        +
FAISS Index
        +
BM25 Corpus
        +
Retrieved Context
        +
Cross-Encoder Reranking
        +
Local LLM Inference
```

This architecture is particularly relevant for financial workflows where documents may contain confidential or sensitive business information.

A future version may explore privacy-preserving local/cloud reasoning where sensitive information is sanitized locally before any external reasoning.

---

# Engineering Principles

### Single Canonical Corpus

Dense and sparse retrieval operate on identical document chunks.

### Stable Chunk Identity

Every chunk receives a deterministic `chunk_id` for synchronization, deduplication, debugging, and evaluation.

### Local-First AI

Embeddings, reranking, and LLM inference can run locally without requiring paid external AI APIs.

### Controlled Embedding Batches

Large corpora are embedded incrementally to avoid overwhelming the local Ollama inference runtime.

### Retrieval Separation

Semantic retrieval and lexical retrieval remain independent until rank fusion.

### Rank-Based Fusion

FAISS and BM25 scores are not mixed directly. RRF combines their ranking positions instead.

### Reranking for Precision

The cross-encoder operates only on the small candidate set produced by hybrid retrieval rather than scanning the entire corpus.

### Grounded Generation

The LLM receives retrieved evidence and is explicitly instructed not to fabricate financial facts.

### Separation of Concerns

Ingestion, retrieval, reranking, generation, orchestration, API infrastructure, and database access remain independently testable.

---

# Roadmap

```text
Document Ingestion                         ✅
        ↓
Canonical Chunk Corpus                    ✅
        ↓
Dense FAISS Retrieval                     ✅
        ↓
BM25 Sparse Retrieval                     ✅
        ↓
RRF Rank Fusion                           ✅
        ↓
Hybrid Retrieval                           ✅
        ↓
Cross-Encoder Reranking                    ✅
        ↓
Context Construction                       ✅
        ↓
Local LLM Generation                       ✅
        ↓
LangGraph Orchestration                    ✅
        ↓
Production RAG API                         ✅
        ↓
Evaluation + Optimization                  🚧
        ↓
Production Hardening                       ⏳
        ↓
Deployment                                  ⏳
```

---

# Author

**Saptak Mondal**

Computer Science Engineering — AI/ML & IoT

---

<div align="center">

### FinDoc-RAG

**Turning dense financial documents into searchable, grounded intelligence.**

</div>
```
