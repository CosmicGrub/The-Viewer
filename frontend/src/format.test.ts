import { describe, expect, it } from "vitest";
import { formatBytes, formatDate } from "./format";

describe("formatBytes", () => {
  it("renders null as an em dash", () => {
    expect(formatBytes(null)).toBe("—");
  });

  it("renders sub-1KB sizes in bytes", () => {
    expect(formatBytes(512)).toBe("512 B");
  });

  it("renders KB with one decimal place", () => {
    expect(formatBytes(2048)).toBe("2.0 KB");
  });

  it("renders MB once past 1024 KB", () => {
    expect(formatBytes(5 * 1024 * 1024)).toBe("5.0 MB");
  });

  it("renders GB once past 1024 MB", () => {
    expect(formatBytes(3 * 1024 * 1024 * 1024)).toBe("3.0 GB");
  });

  it("caps at GB rather than continuing to TB", () => {
    expect(formatBytes(2048 * 1024 * 1024 * 1024)).toBe("2048.0 GB");
  });

  it("handles zero bytes", () => {
    expect(formatBytes(0)).toBe("0 B");
  });
});

describe("formatDate", () => {
  it("renders null as an em dash", () => {
    expect(formatDate(null)).toBe("—");
  });

  it("renders a valid ISO timestamp via toLocaleString", () => {
    const iso = "2026-08-16T12:00:00.000Z";
    expect(formatDate(iso)).toBe(new Date(iso).toLocaleString());
  });

  it("falls back to the raw string for an unparseable date", () => {
    expect(formatDate("not-a-date")).toBe("not-a-date");
  });
});
