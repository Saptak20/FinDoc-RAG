# FinDoc-RAG API Reference

Base URL: `/api/v1` (proxied through Nginx at `/api/v1`)

All endpoints require `Content-Type: application/json` unless noted.  
All responses include `X-Request-ID` header for correlation.

---

## Health & Readiness

### `GET /health`
Liveness probe – process is alive.

**Response 200**
```json
{
  "status": "healthy",
  "application": "FinDoc-RAG",
  "environment": "production"
}
```

### `GET /ready`
Readiness probe – all subsystems operational (FAISS, BM25, PostgreSQL, Ollama).

**Response 200 (ready)**
```json
{
  "status": "ready",
  "checks": {
    "faiss_index": true,
    "chunk_corpus": true,
    "database": true,
    "ollama_service": true
  },
  "application": "FinDoc-RAG"
}
```

**Response 503 (not ready)**
```json
{
  "status": "not_ready",
  "checks": {
    "faiss_index": false,
    "chunk_corpus": true,
    "database": true,
    "ollama_service": true
  },
  "application": "FinDoc-RAG"
}
```

---

## Chat

### `POST /api/v1/chat`

Ask a financial question; returns grounded answer with citations and telemetry.

**Rate limit:** 30 requests/minute per IP (configurable).

#### Request
```json
{
  "query": "string (required, non‑empty)",
  "dense_top_k": 10,
  "sparse_top_k": 10,
  "final_top_k": 3
}
```
| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `query` | string | **Yes** | – | Financial question |
| `dense_top_k` | integer | No | 10 | FAISS candidates |
| `sparse_top_k` | integer | No | 10 | BM25 candidates |
| `final_top_k` | integer | No | 3 | Reranked chunks passed to LLM |

#### Response 200
```json
{
  "query": "What was Tata Steel's EBITDA margin in FY2023-24?",
  "answer": "Tata Steel reported an EBITDA margin of 22% in FY2023-24.",
  "sources": [
    {
      "source": "OTC_TATLY_2024.pdf",
      "page": 14,
      "chunk_id": "OTC_TATLY_2024.pdf::page_14::chunk_3::c6a111a9b067",
      "rerank_score": 8.42,
      "rrf_score": 0.0153
    }
  ],
  "metrics": {
    "retrieval_candidates": 20,
    "reranked_chunks": 3,
    "latency_seconds": 2.41
  }
}
```

#### Error Responses
| Code | Condition |
|------|-----------|
| 400 | Empty/whitespace query |
| 422 | Invalid `top_k` (≤0) |
| 429 | Rate limit exceeded (`Retry-After` header) |
| 500 | Internal server error (sanitized) |

---

## Documents

### `POST /api/v1/documents/upload`
Upload a financial PDF; triggers async ingestion.

**Rate limit:** 10 requests/minute per IP.

**Content-Type:** `multipart/form-data`

| Field | Type | Required |
|-------|------|----------|
| `file` | file (PDF) | **Yes** |

#### Response 201
```json
{
  "message": "Document 'report.pdf' uploaded successfully. Background ingestion initiated.",
  "document": {
    "id": 12,
    "filename": "a1b2c3d4_report.pdf",
    "original_filename": "report.pdf",
    "file_size_bytes": 25690663,
    "page_count": 0,
    "chunk_count": 0,
    "processing_status": "PENDING",
    "processing_error": null,
    "created_at": "2025-08-27T12:34:56.789Z",
    "updated_at": "2025-08-27T12:34:56.789Z"
  }
}
```

#### Error Responses
| Code | Condition |
|------|-----------|
| 400 | Not a PDF, >50 MB, missing file, corrupt PDF |
| 409 | Duplicate content (SHA‑256 match) – returns existing document |
| 429 | Rate limit |

---

### `GET /api/v1/documents`
List all registered documents with indexing status.

**Response 200**
```json
{
  "total": 3,
  "ready_count": 2,
  "documents": [
    {
      "id": 1,
      "filename": "OTC_TATLY_2024.pdf",
      "original_filename": "OTC_TATLY_2024.pdf",
      "file_size_bytes": 25690663,
      "page_count": 581,
      "chunk_count": 2710,
      "processing_status": "READY",
      "processing_error": null,
      "created_at": "2025-08-12T06:48:00Z",
      "updated_at": "2025-08-26T15:13:00Z"
    }
  ]
}
```

### `GET /api/v1/documents/{id}`
Get metadata for a single document.

**Response 200** – same shape as array element above.  
**404** if not found.

---

### `DELETE /api/v1/documents/{id}`
Delete a document, purge its chunks, rebuild FAISS/BM25, hot‑reload retrievers.

**Rate limit:** 10 requests/minute.

**Response 200**
```json
{ "message": "Document 'report.pdf' deleted successfully.", "id": 12 }
```

**Errors**
| Code | Condition |
|------|-----------|
| 404 | Not found |
| 409 | Document currently `PROCESSING` |
| 429 | Rate limit |

---

## Data Models (Pydantic)

### `ChatRequest`
```json
{
  "query": "string",
  "dense_top_k": "integer|null",
  "sparse_top_k": "integer|null",
  "final_top_k": "integer|null"
}
```

### `ChatResponse`
```json
{
  "query": "string",
  "answer": "string",
  "sources": [ "SourceItem" ],
  "metrics": "ChatMetrics"
}
```

### `SourceItem`
```json
{
  "source": "string",
  "page": "integer",
  "chunk_id": "string",
  "rerank_score": "number|null",
  "rrf_score": "number|null"
}
```

### `ChatMetrics`
```json
{
  "retrieval_candidates": "integer",
  "reranked_chunks": "integer",
  "latency_seconds": "number"
}
```

### `DocumentItem`
```json
{
  "id": "integer",
  "filename": "string",
  "original_filename": "string",
  "file_size_bytes": "integer",
  "page_count": "integer",
  "chunk_count": "integer",
  "processing_status": "PENDING|PROCESSING|READY|FAILED",
  "processing_error": "string|null",
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

### `DocumentListResponse`
```json
{
  "total": "integer",
  "ready_count": "integer",
  "documents": [ "DocumentItem" ]
}
```

### `DocumentUploadResponse`
```json
{
  "message": "string",
  "document": "DocumentItem"
}
```

---

## Error Format (Global)

All error responses follow:
```json
{
  "detail": "Human‑readable message",
  "request_id": "string"
}
```
Headers: `X-Request-ID`, `Retry-After` (on 429).

---

## Rate Limit Headers

| Header | Meaning |
|--------|---------|
| `Retry-After` | Seconds until next allowed request (on 429) |
| `X-Request-ID` | Correlation ID for every response |

---

## Example cURL

```bash
# Health
curl https://yourdomain.com/health

# Ready
curl https://yourdomain.com/ready

# Chat
curl -X POST https://yourdomain.com/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"query":"What was Tata Steel EBITDA margin in FY2023-24?"}'

# Upload PDF
curl -X POST https://yourdomain.com/api/v1/documents/upload \
  -F "file=@/path/report.pdf"

# List docs
curl https://yourdomain.com/api/v1/documents

# Delete
curl -X DELETE https://yourdomain.com/api/v1/documents/12
```

---

*All endpoints are versioned under `/api/v1`. Future versions will use `/api/v2`.*  
*OpenAPI docs available at `/docs` (FastAPI Swagger UI) when `DEBUG=True`.*