import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "./App";
import { ApiError } from "./api";

// App.tsx's search-as-you-type state machine (idle/loading/ready/error) was
// previously only ever verified manually (finding #13). These mock the API
// client module wholesale so the component's own state transitions —
// debounce, result rendering, error handling — are what's actually under
// test, not a real backend.
vi.mock("./api", async () => {
  const actual = await vi.importActual<typeof import("./api")>("./api");
  return {
    ...actual,
    search: vi.fn(),
    getDocument: vi.fn(),
    getHealth: vi.fn(),
  };
});

import { getDocument, getHealth, search } from "./api";

const mockedSearch = vi.mocked(search);
const mockedGetDocument = vi.mocked(getDocument);
const mockedGetHealth = vi.mocked(getHealth);

const SAMPLE_RESULT = {
  document_id: "abc123",
  filename: "hydraulic_pump_manual.pdf",
  filepath: "C:\\docs\\hydraulic_pump_manual.pdf",
  title: "Hydraulic Pump Manual",
  snippet: "...replace the pump seal...",
  score: 0.87,
};

const SAMPLE_DETAIL = {
  document_id: "abc123",
  filename: "hydraulic_pump_manual.pdf",
  filepath: "C:\\docs\\hydraulic_pump_manual.pdf",
  title: "Hydraulic Pump Manual",
  author: "Dept. of the Army",
  text: "full extracted text",
  num_pages: 12,
  file_size: 45678,
  ocr_pages_used: [],
  extracted_at: "2026-08-16T12:00:00.000Z",
};

// Real timers throughout: App.tsx's 300ms search debounce is short enough
// that real timers plus a generous findBy* timeout below is simpler and
// less brittle than coordinating fake timers with userEvent's own async
// event loop (which schedules its own timers internally).
const FIND_TIMEOUT = { timeout: 2000 };

beforeEach(() => {
  mockedGetHealth.mockResolvedValue({ status: "ok" });
  mockedGetDocument.mockResolvedValue(SAMPLE_DETAIL);
});

afterEach(() => {
  vi.clearAllMocks();
});

function setupUser() {
  return userEvent.setup();
}

describe("App", () => {
  it("shows the idle prompt before any query is typed", async () => {
    render(<App />);
    expect(screen.getByText(/start typing to search indexed documents/i)).toBeInTheDocument();
    // Let BackendStatus's GET /health resolve within an act() boundary
    // rather than leaking a state update past the end of the test.
    await screen.findByText(/backend online/i, {}, FIND_TIMEOUT);
  });

  it("debounces typing, then renders results and auto-selects the first one", async () => {
    mockedSearch.mockResolvedValue({
      query: "pump",
      total_hits: 1,
      results: [SAMPLE_RESULT],
    });
    const user = setupUser();
    render(<App />);

    await user.type(screen.getByPlaceholderText(/search technical manuals/i), "pump");

    // Two matches once loaded: the result row, and the auto-selected
    // detail pane's header (same title in both).
    expect(await screen.findAllByText("Hydraulic Pump Manual", {}, FIND_TIMEOUT)).toHaveLength(2);
    expect(mockedSearch).toHaveBeenCalledWith("pump", 20, 0, expect.any(AbortSignal));
  });

  it("shows an error message when the search API call fails", async () => {
    mockedSearch.mockRejectedValue(new ApiError(503, "Meilisearch is unreachable"));
    const user = setupUser();
    render(<App />);

    await user.type(screen.getByPlaceholderText(/search technical manuals/i), "pump");

    expect(await screen.findByText("Meilisearch is unreachable", {}, FIND_TIMEOUT)).toBeInTheDocument();
  });

  it("shows a no-matches message when the search succeeds with zero results", async () => {
    mockedSearch.mockResolvedValue({ query: "asdf", total_hits: 0, results: [] });
    const user = setupUser();
    render(<App />);

    await user.type(screen.getByPlaceholderText(/search technical manuals/i), "asdf");

    expect(await screen.findByText(/no documents match/i, {}, FIND_TIMEOUT)).toBeInTheDocument();
  });

  it("clearing the query back to empty returns to the idle state", async () => {
    mockedSearch.mockResolvedValue({ query: "p", total_hits: 0, results: [] });
    const user = setupUser();
    render(<App />);

    const input = screen.getByPlaceholderText(/search technical manuals/i);
    await user.type(input, "p");
    await screen.findByText(/no documents match/i, {}, FIND_TIMEOUT);
    await user.clear(input);

    expect(screen.getByText(/start typing to search indexed documents/i)).toBeInTheDocument();
  });

  it("reports the backend as unreachable when GET /health fails", async () => {
    mockedGetHealth.mockRejectedValue(new Error("network error"));
    render(<App />);

    expect(await screen.findByText(/backend unreachable/i, {}, FIND_TIMEOUT)).toBeInTheDocument();
  });
});
