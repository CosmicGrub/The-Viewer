import { Fragment, type ReactNode } from "react";

// Splits `query` into individual search terms and wraps every
// case-insensitive match of any of them in `text` with <mark>. Applied to
// both the cropped snippet and the full-text view, so switching tabs
// doesn't lose all match context the way a backend-only crop-highlight
// would (finding #28). Pure text splitting — never dangerouslySetInnerHTML
// — since extracted document text is untrusted content.
//
// Pulled out of App.tsx alongside format.ts (finding #13/#14) so the term
// -splitting logic can be unit-tested without rendering the whole app.
export function highlightTerms(text: string, query: string): ReactNode {
  const terms = Array.from(
    new Set(
      query
        .split(/\s+/)
        .map((t) => t.trim())
        .filter((t) => t.length > 0)
        .map((t) => t.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")) // escape regex metachars
    )
  );
  if (terms.length === 0) return text;

  const pattern = new RegExp(`(${terms.join("|")})`, "gi");
  const parts = text.split(pattern);

  return parts.map((part, i) =>
    pattern.test(part) && terms.some((t) => new RegExp(`^${t}$`, "i").test(part)) ? (
      <mark key={i} className="rounded-sm bg-sky-400/40 text-slate-50">
        {part}
      </mark>
    ) : (
      <Fragment key={i}>{part}</Fragment>
    )
  );
}
