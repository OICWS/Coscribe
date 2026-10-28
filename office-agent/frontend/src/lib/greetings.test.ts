import { describe, expect, it } from "vitest";
import { pickGreeting } from "./greetings";

// 2026-10-26 is a Monday, 2026-10-28 a Wednesday.
const at = (day: string, hour: number) => new Date(`2026-10-${day}T${String(hour).padStart(2, "0")}:00:00`);
const first = () => 0;
const last = () => 0.999999;

describe("pickGreeting", () => {
  it("starts each part of the day with its plain greeting", () => {
    expect(pickGreeting(at("28", 8), "", first)).toBe("Good morning");
    expect(pickGreeting(at("28", 14), "", first)).toBe("Good afternoon");
    expect(pickGreeting(at("28", 20), "", first)).toBe("Good evening");
    expect(pickGreeting(at("28", 2), "", first)).toBe("Hello, night owl");
  });

  it("never leaves a placeholder when there is no name", () => {
    for (let hour = 0; hour < 24; hour++) {
      for (let i = 0; i < 20; i++) {
        expect(pickGreeting(at("26", hour), " ", () => i / 20)).not.toContain("{name}");
      }
    }
  });

  it("puts the name in lines that use it", () => {
    expect(pickGreeting(at("28", 8), "Allen", () => 0.12)).toBe("Good morning, Allen");
  });

  it("can pick a weekday line", () => {
    expect(pickGreeting(at("26", 8), "", last)).toBe("Happy Monday");
  });
});
