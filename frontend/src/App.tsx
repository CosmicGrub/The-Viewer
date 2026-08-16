import { useEffect, useMemo, useRef, useState } from "react";
import {
  AlertCircle,
  ChevronRight,
  Clock,
  FileSearch,
  FileText,
  Files,
  Hash,
  Loader2,
  ScanText,
  Search,
} from "lucide-react";
import { ApiError, getDocument, getHealth, search, type DocumentDetail, type SearchResult } from "./api";

type SearchState =
  | { kind: "idle" }
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | { kind: "ready"; query: string; totalHits: number; results: SearchResult[] };

type DetailState =
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | { kind: "ready"; detail: DocumentDetail };

const DETAIL_TABS = [
  { id: "snippet", label: "Matched snippet", icon: ScanText },
  { id: "full", label: "Full text", icon: FileText },
] as const;
type DetailTab = (typeof DETAIL_TABS)[number]["id"];

function formatBytes(bytes: number | null) {
  if (bytes == null) return "—";
  if (bytes < 1024) return `${bytes} B`;
  const units = ["KB", "MB", "GB"];
  let value = bytes / 1024;
  let unit = 0;
  while (value >= 1024 && unit < units.length - 1) {
    value /= 1024;
    unit += 1;
  }
  return `${value.toFixed(1)} ${units[unit]}`;
}

function formatDate(iso: string | null) {
  if (!iso) return "—";
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleString();
}

// Per-document cache so re-selecting a result (or flipping tabs) doesn't
// re-fetch full text/metadata that was already loaded this session.
const detailCache = new Map<string, DocumentDetail>();

function useDocumentDetail(documentId: string): DetailState {
  const [state, setState] = useState<DetailState>(() => {
    const cached = detailCache.get(documentId);
    return cached ? { kind: "ready", detail: cached } : { kind: "loading" };
  });

  useEffect(() => {
    const cached = detailCache.get(documentId);
    if (cached) {
      setState({ kind: "ready", detail: cached });
      return;
    }
    let cancelled = false;
    setState({ kind: "loading" });
    getDocument(documentId)
      .then((detail) => {
        detailCache.set(documentId, detail);
        if (!cancelled) setState({ kind: "ready", detail });
      })
      .catch((err) => {
        if (cancelled) return;
        const message = err instanceof ApiError ? err.message : "Couldn't load this document.";
        setState({ kind: "error", message });
      });
    return () => {
      cancelled = true;
    };
  }, [documentId]);

  return state;
}

function BackendStatus() {
  const [online, setOnline] = useState<boolean | null>(null);

  useEffect(() => {
    let cancelled = false;
    getHealth()
      .then(() => !cancelled && setOnline(true))
      .catch(() => !cancelled && setOnline(false));
    return () => {
      cancelled = true;
    };
  }, []);

  const label = online === null ? "Checking…" : online ? "Backend online" : "Backend unreachable";
  const dotColor = online === null ? "bg-slate-500" : online ? "bg-emerald-400" : "bg-rose-400";

  return (
    <div
      className="ml-auto flex items-center gap-1.5 rounded-lg bg-slate-800 px-3 py-1 text-xs text-slate-300"
      title="GET /health"
    >
      <span className={`h-2 w-2 rounded-full ${dotColor}`} />
      {label}
    </div>
  );
}

function ResultRow({ result, selected, onSelect }: { result: SearchResult; selected: boolean; onSelect: () => void }) {
  return (
    <button
      onClick={onSelect}
      className={`flex w-full items-center gap-2 border-b border-slate-800/60 px-3 py-2.5 text-left ${
        selected ? "bg-slate-800" : "hover:bg-slate-900"
      }`}
    >
      <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded border border-slate-700 bg-slate-900 text-slate-500">
        <FileText size={15} />
      </span>
      <span className="min-w-0">
        <span className="block truncate text-sm">{result.filename}</span>
        <span className="block truncate font-mono text-[10px] text-slate-500">
          {result.document_id.slice(0, 12)}
        </span>
      </span>
      {result.score !== null && (
        <span className="ml-auto shrink-0 font-mono text-[10px] text-slate-500">
          {Math.round(result.score * 100)}%
        </span>
      )}
      <ChevronRight size={14} className="shrink-0 text-slate-600" />
    </button>
  );
}

function DetailPane({ result }: { result: SearchResult }) {
  const [tab, setTab] = useState<DetailTab>("snippet");
  useEffect(() => setTab("snippet"), [result.document_id]);
  const detailState = useDocumentDetail(result.document_id);

  const bodyText =
    tab === "snippet"
      ? result.snippet
      : detailState.kind === "ready"
        ? detailState.detail.text
        : null;

  return (
    <div className="flex min-w-0 flex-1 flex-col">
      <div className="flex flex-wrap items-center gap-2 px-4 pt-3">
        <span className="font-semibold">{result.filename}</span>
        {result.score !== null && (
          <span className="ml-auto flex items-center gap-1 rounded-full bg-slate-800 px-2 py-0.5 text-[11px] text-slate-300">
            {Math.round(result.score * 100)}% match
          </span>
        )}
      </div>

      <div className="flex flex-wrap gap-1 px-4 pt-2">
        {DETAIL_TABS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setTab(id)}
            className={`flex items-center gap-1.5 rounded-lg border px-2.5 py-1.5 text-xs ${
              tab === id
                ? "border-sky-500 bg-sky-500 font-semibold text-slate-900"
                : "border-slate-700 text-slate-300 hover:bg-slate-800"
            }`}
          >
            <Icon size={13} />
            {label}
          </button>
        ))}
      </div>

      <div className="grid min-h-0 flex-1 grid-cols-1 gap-3 p-4 lg:grid-cols-[1fr_260px]">
        <div className="min-h-[220px] overflow-y-auto rounded-lg bg-slate-100 p-4 text-sm leading-relaxed whitespace-pre-wrap text-slate-800">
          {tab === "full" && detailState.kind === "loading" && (
            <span className="flex items-center gap-2 text-slate-500 italic">
              <Loader2 size={14} className="animate-spin" /> Loading full text…
            </span>
          )}
          {tab === "full" && detailState.kind === "error" && (
            <span className="text-rose-600">{detailState.message}</span>
          )}
          {bodyText !== null && (bodyText || <span className="text-slate-400 italic">No text extracted.</span>)}
        </div>

        <div className="space-y-3 overflow-y-auto text-xs">
          <div>
            <div className="mb-1 text-[10px] tracking-wide text-slate-500 uppercase">Source file</div>
            <div className="text-slate-300 break-all">{result.filepath}</div>
          </div>

          <div>
            <div className="mb-1 flex items-center gap-1 text-[10px] tracking-wide text-slate-500 uppercase">
              <Hash size={11} /> Document id
            </div>
            <div className="font-mono text-slate-400">{result.document_id}</div>
          </div>

          <div>
            <div className="mb-1 flex items-center gap-1 text-[10px] tracking-wide text-slate-500 uppercase">
              <Files size={11} /> Document info
            </div>
            {detailState.kind === "ready" ? (
              <div className="space-y-1 text-slate-300">
                <div>{detailState.detail.num_pages ?? "—"} page(s)</div>
                <div>{formatBytes(detailState.detail.file_size)}</div>
                <div className="flex items-center gap-1 text-slate-400">
                  <Clock size={11} /> {formatDate(detailState.detail.extracted_at)}
                </div>
                {detailState.detail.ocr_pages_used.length > 0 && (
                  <div className="mt-1 flex flex-wrap items-center gap-1 text-slate-400">
                    OCR used:
                    {detailState.detail.ocr_pages_used.map((p) => (
                      <span key={p} className="rounded border border-slate-700 bg-slate-800 px-1.5 py-0.5">
                        p{p}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ) : detailState.kind === "error" ? (
              <div className="text-rose-400">{detailState.message}</div>
            ) : (
              <div className="text-slate-600 italic">Loading…</div>
            )}
          </div>

          <div className="border-t border-slate-800 pt-2 text-[10px] text-slate-600">
            Extracted text — always verify against the source document before relying on it.
          </div>
        </div>
      </div>
    </div>
  );
}

export default function App() {
  const [query, setQuery] = useState("");
  const [state, setState] = useState<SearchState>({ kind: "idle" });
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const debounceRef = useRef<number | undefined>(undefined);

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        inputRef.current?.focus();
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  const runSearch = (q: string) => {
    window.clearTimeout(debounceRef.current);
    if (!q.trim()) {
      setState({ kind: "idle" });
      return;
    }
    debounceRef.current = window.setTimeout(async () => {
      setState({ kind: "loading" });
      try {
        const response = await search(q);
        setState({
          kind: "ready",
          query: response.query,
          totalHits: response.total_hits,
          results: response.results,
        });
        setSelectedId(response.results[0]?.document_id ?? null);
      } catch (err) {
        const message =
          err instanceof ApiError ? err.message : "Couldn't reach the search API — is the backend running?";
        setState({ kind: "error", message });
      }
    }, 300);
  };

  const results = state.kind === "ready" ? state.results : [];
  const selected = useMemo(() => results.find((r) => r.document_id === selectedId) ?? null, [results, selectedId]);

  return (
    <div className="flex min-h-screen flex-col bg-slate-950 font-sans text-slate-200">
      {/* header */}
      <div className="flex items-center gap-3 border-b border-slate-800 bg-slate-900 px-4 py-3">
        <div className="flex items-center gap-2 font-bold tracking-wide text-sky-400">
          <FileSearch size={20} /> TM SEARCH ENGINE
        </div>
        <span className="hidden text-[11px] text-slate-500 sm:inline">full-text search · Meilisearch-backed</span>
        <BackendStatus />
      </div>

      {/* search */}
      <div className="border-b border-slate-800 px-4 py-3">
        <div className="flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-900 px-3 py-2">
          <Search size={16} className="text-slate-500" />
          <input
            ref={inputRef}
            type="search"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              runSearch(e.target.value);
            }}
            placeholder="Search technical manuals…"
            className="w-full bg-transparent text-sm outline-none placeholder:text-slate-600"
            autoFocus
          />
          {state.kind === "loading" && <Loader2 size={14} className="animate-spin text-slate-500" />}
          <kbd className="hidden rounded border border-slate-700 px-1.5 py-0.5 text-[10px] text-slate-500 sm:block">
            Ctrl K
          </kbd>
        </div>
      </div>

      <div className="flex min-h-0 flex-1">
        {/* results list */}
        <div className="w-64 shrink-0 overflow-y-auto border-r border-slate-800">
          {state.kind === "idle" && (
            <div className="p-4 text-sm text-slate-500">Start typing to search indexed documents.</div>
          )}
          {state.kind === "error" && (
            <div className="flex items-start gap-2 p-4 text-sm text-rose-400">
              <AlertCircle size={16} className="mt-0.5 shrink-0" />
              <span>{state.message}</span>
            </div>
          )}
          {state.kind === "ready" && results.length === 0 && (
            <div className="p-4 text-sm text-slate-500">No documents match “{state.query}”.</div>
          )}
          {results.map((r) => (
            <ResultRow
              key={r.document_id}
              result={r}
              selected={r.document_id === selectedId}
              onSelect={() => setSelectedId(r.document_id)}
            />
          ))}
        </div>

        {/* detail */}
        {selected ? (
          <DetailPane result={selected} />
        ) : (
          <div className="flex flex-1 items-center justify-center text-sm text-slate-600">
            {state.kind === "ready" && results.length > 0
              ? "Select a result to preview it."
              : "Results will appear here."}
          </div>
        )}
      </div>
    </div>
  );
}
