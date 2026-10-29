import { describe, expect, it } from "vitest";
import { pickGreeting, poolForTime } from "./greetings";

// 2026-10-26 is a Monday, 2026-10-28 a Wednesday.
const at = (day: string, hour: number, month = "10") =>
  new Date(`2026-${month}-${day}T${String(hour).padStart(2, "0")}:00:00`);
const first = () => 0;

describe("pickGreeting", () => {
  it("starts each part of the day with its plain greeting", () => {
    expect(pickGreeting(at("28", 8), "", first)).toBe("Good morning");
    expect(pickGreeting(at("28", 14), "", first)).toBe("Good afternoon");
    expect(pickGreeting(at("28", 20), "", first)).toBe("Good evening");
    expect(pickGreeting(at("28", 2), "", first)).toBe("Hello, night owl");
  });

  it("never leaves a placeholder when there is no name", () => {
    for (const month of ["01", "04", "07", "10"]) {
      for (const day of ["25", "26", "30"]) {
        for (let hour = 0; hour < 24; hour++) {
          for (let i = 0; i < 20; i++) {
            expect(pickGreeting(at(day, hour, month), " ", () => i / 20)).not.toContain("{name}");
          }
        }
      }
    }
  });

  it("puts the name in lines that use it", () => {
    expect(pickGreeting(at("28", 8), "Allen", () => 0.03)).toBe("Good morning, Allen");
  });

  it("draws from the weekday and season groups", () => {
    const monday = poolForTime(at("26", 8));
    const wednesday = poolForTime(at("28", 8));
    expect(monday).toContain("Fresh week, fresh page");
    expect(wednesday).not.toContain("Fresh week, fresh page");
    expect(poolForTime(at("28", 8, "01"))).toContain("Cold outside, warm lamp inside");
    expect(poolForTime(at("28", 8, "07"))).toContain("Long days, longer drafts");
  });

  it("does not repeat the line shown last", () => {
    expect(pickGreeting(at("28", 8), "", first, "Good morning")).not.toBe("Good morning");
  });
});
