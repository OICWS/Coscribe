import { describe, expect, it } from "vitest";
import { listSessions, timeAgo } from "./sessionList";

const NOW = Date.parse("2026-11-16T12:00:00Z");

describe("timeAgo", () => {
  it("says how long ago in words", () => {
    expect(timeAgo("2026-11-16T11:52:00Z", NOW)).toBe("8 minutes ago");
    expect(timeAgo("2026-11-16T11:59:00Z", NOW)).toBe("1 minute ago");
    expect(timeAgo("2026-11-16T09:00:00Z", NOW)).toBe("3 hours ago");
    expect(timeAgo("2026-11-13T12:00:00Z", NOW)).toBe("3 days ago");
    expect(timeAgo("2026-11-16T11:59:40Z", NOW)).toBe("just now");
  });

  it("says nothing without a time", () => {
    expect(timeAgo(null, NOW)).toBe("");
    expect(timeAgo("not a date", NOW)).toBe("");
  });
});

describe("listSessions", () => {
  const thread = (id: string, preview: string, updated: string, archived = false, environment = "default") => ({
    thread_id: id,
    preview,
    updated_at: updated,
    archived,
    environment,
  });
  const threads = [
    thread("a", "Quarterly report", "2026-11-16T10:00:00Z"),
    thread("b", "Budget sheet", "2026-11-16T11:00:00Z", false, "work"),
    thread("c", "Old deck", "2026-11-15T11:00:00Z", true),
  ];
  const name = (id: string) => (id === "work" ? "Work laptop" : "Default");

  it("splits active from archived, newest first", () => {
    expect(listSessions(threads, "active", "", name).map((t) => t.thread_id)).toEqual(["b", "a"]);
    expect(listSessions(threads, "archived", "", name).map((t) => t.thread_id)).toEqual(["c"]);
  });

  it("searches titles and environment names", () => {
    expect(listSessions(threads, "active", "report", name).map((t) => t.thread_id)).toEqual(["a"]);
    expect(listSessions(threads, "active", "laptop", name).map((t) => t.thread_id)).toEqual(["b"]);
  });
});
