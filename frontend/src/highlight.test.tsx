import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { highlightTerms } from "./highlight";

function renderHighlighted(text: string, query: string) {
  render(<div data-testid="out">{highlightTerms(text, query)}</div>);
  return screen.getByTestId("out");
}

describe("highlightTerms", () => {
  it("returns the plain text unchanged when the query is empty", () => {
    const el = renderHighlighted("hydraulic pump manual", "");
    expect(el.textContent).toBe("hydraulic pump manual");
    expect(el.querySelector("mark")).toBeNull();
  });

  it("wraps a single matching term in <mark>", () => {
    const el = renderHighlighted("replace the hydraulic pump seal", "pump");
    const marks = el.querySelectorAll("mark");
    expect(marks).toHaveLength(1);
    expect(marks[0].textContent).toBe("pump");
  });

  it("matches case-insensitively", () => {
    const el = renderHighlighted("Hydraulic Pump Manual", "pump");
    expect(el.querySelector("mark")?.textContent).toBe("Pump");
  });

  it("highlights every occurrence and every distinct term in a multi-word query", () => {
    const el = renderHighlighted("pump seal, pump gasket, valve seal", "pump seal");
    const marks = Array.from(el.querySelectorAll("mark")).map((m) => m.textContent);
    expect(marks).toEqual(["pump", "seal", "pump", "seal"]);
  });

  it("doesn't crash on regex-special characters in the query", () => {
    const el = renderHighlighted("part 5310-01-234-5678(rev.2)", "5310-01-234-5678(rev.2)");
    expect(el.querySelector("mark")?.textContent).toBe("5310-01-234-5678(rev.2)");
  });

  it("leaves non-matching text untouched around a highlighted term", () => {
    const el = renderHighlighted("torque the fitting to 45 ft-lb", "torque");
    expect(el.textContent).toBe("torque the fitting to 45 ft-lb");
    expect(el.querySelectorAll("mark")).toHaveLength(1);
  });
});
