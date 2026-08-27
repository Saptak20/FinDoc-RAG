export interface ChatRequest {
  query: string;
  dense_top_k?: number;
  sparse_top_k?: number;
  final_top_k?: number;
}

export interface SourceItem {
  source: string;
  page: number;
  chunk_id: string;
  rerank_score?: number;
  rrf_score?: number;
  retrieval_sources?: string[];
}

export interface ChatMetrics {
  retrieval_candidates: number;
  reranked_chunks: number;
  latency_seconds: number;
}

export interface ChatResponse {
  query: string;
  answer: string;
  sources: SourceItem[];
  metrics: ChatMetrics;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  sources?: SourceItem[];
  metrics?: ChatMetrics;
  isError?: boolean;
}

export interface SystemStatus {
  status: 'healthy' | 'ready' | 'not_ready' | 'offline' | 'checking';
  application: string;
  checks?: {
    faiss_index?: boolean;
    chunk_corpus?: boolean;
    ollama_service?: boolean;
  };
  environment?: string;
}

export interface DocumentItem {
  id: number;
  filename: string;
  original_filename: string;
  file_size_bytes: number;
  page_count: number;
  chunk_count: number;
  processing_status: 'PENDING' | 'PROCESSING' | 'READY' | 'FAILED';
  processing_error?: string | null;
  created_at: string;
  updated_at: string;
}

export interface DocumentListResponse {
  total: number;
  ready_count: number;
  documents: DocumentItem[];
}

export interface DocumentUploadResponse {
  message: string;
  document: DocumentItem;
}