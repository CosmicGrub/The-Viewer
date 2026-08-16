// Typed client for the backend API (see backend/main.py, backend/routers/search.py).
// Mirrors the Pydantic models there — keep these in sync if those change.

export interface SearchResult {
  document_id: string;
  filename: string;
  filepath: string;
  title: string | null;
  snippet: string;
  score: number | null;
}

export interface SearchResponse {
  query: string;
  total_hits: number;
  results: SearchResult[];
}

export interface DocumentDetail {
  document_id: string;
  filename: string;
  filepath: string;
  title: string | null;
  author: string | null;
  text: string;
  num_pages: number | null;
  file_size: number | null;
  ocr_pages_used: number[];
  extracted_at: string | null;
}

export interface StatusResponse {
  source_dir_configured: boolean;
  source_dir: string | null;
  output_dir: string;
}

// An error response from the API that carries a status code and the
// server's `detail` message, so callers can distinguish e.g. a 503
// ("Meilisearch isn't running") from other failures.
export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function getJson<T>(url: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(url, { signal });
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      if (typeof body?.detail === "string") {
        detail = body.detail;
      }
    } catch {
      // Response body wasn't JSON (or was empty) — fall back to statusText.
    }
    throw new ApiError(response.status, detail);
  }
  return response.json() as Promise<T>;
}

export function search(query: string, limit = 20, offset = 0, signal?: AbortSignal): Promise<SearchResponse> {
  const params = new URLSearchParams({ q: query, limit: String(limit), offset: String(offset) });
  return getJson<SearchResponse>(`/api/search?${params}`, signal);
}

export function getDocument(documentId: string, signal?: AbortSignal): Promise<DocumentDetail> {
  return getJson<DocumentDetail>(`/api/search/documents/${encodeURIComponent(documentId)}`, signal);
}

export function getStatus(): Promise<StatusResponse> {
  return getJson<StatusResponse>("/api/status");
}

export function getHealth(): Promise<{ status: string }> {
  return getJson<{ status: string }>("/health");
}
