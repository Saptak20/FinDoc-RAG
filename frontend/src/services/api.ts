import type {
  ChatRequest,
  ChatResponse,
  DocumentListResponse,
  DocumentUploadResponse,
  SystemStatus,
} from '../types/chat';

// Base URL configured via Vite environment variable. Empty string means relative URLs (same origin).
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

export class ApiError extends Error {
  statusCode?: number;
  constructor(message: string, statusCode?: number) {
    super(message);
    this.name = 'ApiError';
    this.statusCode = statusCode;
  }
}

export async function checkSystemReadiness(): Promise<SystemStatus> {
  try {
    const response = await fetch(`${API_BASE_URL}/ready`, {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
      },
    });

    if (response.ok) {
      const data = await response.json();
      return {
        status: data.status === 'ready' ? 'ready' : 'not_ready',
        application: data.application || 'FinDoc-RAG',
        checks: data.checks,
      };
    }

    // If /ready returns 503, parse checks
    if (response.status === 503) {
      const errorData = await response.json().catch(() => ({}));
      return {
        status: 'not_ready',
        application: errorData.application || 'FinDoc-RAG',
        checks: errorData.checks,
      };
    }

    return {
      status: 'offline',
      application: 'FinDoc-RAG',
    };
  } catch {
    // Fallback attempt to /health
    try {
      const healthRes = await fetch(`${API_BASE_URL}/health`, { method: 'GET' });
      if (healthRes.ok) {
        const healthData = await healthRes.json();
        return {
          status: 'healthy',
          application: healthData.application || 'FinDoc-RAG',
          environment: healthData.environment,
        };
      }
    } catch {
      // Backend is completely unreachable
    }

    return {
      status: 'offline',
      application: 'FinDoc-RAG',
    };
  }
}

export async function sendChatQuery(request: ChatRequest): Promise<ChatResponse> {
  if (!request.query || !request.query.trim()) {
    throw new ApiError('Please enter a financial question before submitting.', 400);
  }

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/api/v1/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      body: JSON.stringify({
        query: request.query.trim(),
        dense_top_k: request.dense_top_k,
        sparse_top_k: request.sparse_top_k,
        final_top_k: request.final_top_k,
      }),
    });
  } catch {
    throw new ApiError(
      'Unable to connect to FinDoc-RAG backend. Please verify that the API server is running.',
      0
    );
  }

  if (!response.ok) {
    let errorDetail = 'An error occurred while retrieving information.';
    try {
      const errJson = await response.json();
      if (errJson.detail) {
        if (typeof errJson.detail === 'string') {
          errorDetail = errJson.detail;
        } else if (Array.isArray(errJson.detail) && errJson.detail[0]?.msg) {
          errorDetail = errJson.detail[0].msg;
        }
      }
    } catch {
      // Use fallback errorDetail
    }

    throw new ApiError(errorDetail, response.status);
  }

  const data: ChatResponse = await response.json();
  return data;
}

export async function fetchDocuments(): Promise<DocumentListResponse> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/documents`, {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
      },
    });

    if (!response.ok) {
      throw new ApiError('Failed to fetch document registry.', response.status);
    }

    return await response.json();
  } catch (err: any) {
    if (err instanceof ApiError) throw err;
    throw new ApiError('Could not retrieve documents from backend.', 0);
  }
}

export async function uploadDocument(file: File): Promise<DocumentUploadResponse> {
  const formData = new FormData();
  formData.append('file', file);

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/api/v1/documents/upload`, {
      method: 'POST',
      body: formData,
    });
  } catch {
    throw new ApiError('Network error while uploading document.', 0);
  }

  if (!response.ok) {
    let errorDetail = 'Failed to upload document.';
    try {
      const errJson = await response.json();
      if (errJson.detail) {
        errorDetail = typeof errJson.detail === 'string' ? errJson.detail : errJson.detail[0]?.msg || errorDetail;
      }
    } catch {
      // Fallback message
    }
    throw new ApiError(errorDetail, response.status);
  }

  return await response.json();
}

export async function deleteDocument(documentId: number): Promise<{ message: string; id: number }> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/api/v1/documents/${documentId}`, {
      method: 'DELETE',
      headers: {
        'Accept': 'application/json',
      },
    });
  } catch {
    throw new ApiError('Network error while deleting document.', 0);
  }

  if (!response.ok) {
    throw new ApiError('Failed to delete document.', response.status);
  }

  return await response.json();
}
