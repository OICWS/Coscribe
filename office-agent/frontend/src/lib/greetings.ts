import {
  AFTERNOON,
  ANYTIME,
  AUTUMN,
  EVENING,
  FRIDAY,
  MONDAY,
  MORNING,
  NIGHT,
  SPRING,
  SUMMER,
  WEEKEND,
  WINTER,
  type Pool,
} from "./greetingLines";

const BY_MONTH: readonly Pool[] = [
  WINTER, WINTER, SPRING, SPRING, SPRING, SUMMER, SUMMER, SUMMER, AUTUMN, AUTUMN, AUTUMN, WINTER,
];

/** Local time, not UTC -- a thread opened at 8am should say "morning"
 * regardless of what timezone the backend or server clock is in. */
export function poolForTime(date: Date): Pool {
  const hour = date.getHours();
  const day = date.getDay();
  const byTime = hour >= 5 && hour < 12 ? MORNING : hour >= 12 && hour < 18 ? AFTERNOON : hour >= 18 && hour < 23 ? EVENING : NIGHT;
  const byDay = day === 1 ? MONDAY : day === 5 ? FRIDAY : day === 0 || day === 6 ? WEEKEND : [];
  return [...byTime, ...ANYTIME, ...byDay, ...BY_MONTH[date.getMonth()]];
}

/** `random` is injected so a test can pin the choice; `avoid` is the line shown last,
 * so opening a new conversation twice doesn't repeat it. */
export function pickGreeting(
  date: Date,
  name: string,
  random: () => number = Math.random,
  avoid = "",
): string {
  const who = name.trim();
  const fits = poolForTime(date).filter((line) => who !== "" || !line.includes("{name}"));
  const fresh = fits.filter((line) => line.replaceAll("{name}", who) !== avoid);
  const pool = fresh.length > 0 ? fresh : fits;
  const line = pool[Math.min(Math.floor(random() * pool.length), pool.length - 1)];
  return line.replaceAll("{name}", who);
}
