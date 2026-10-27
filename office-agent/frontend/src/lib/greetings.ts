/** Greetings for the new-conversation heading. `{name}` is replaced with the
 * person's name; a line with it is only picked when there is a name. */
type Pool = readonly string[];

const MORNING: Pool = ["Good morning", "Good morning, {name}", "Rise and shine", "Ready when you are"];
const AFTERNOON: Pool = ["Good afternoon", "Good afternoon, {name}", "Welcome back", "How's the day going?"];
const EVENING: Pool = ["Good evening", "Good evening, {name}", "Evening, {name}", "Let's wrap things up"];
const NIGHT: Pool = ["Hello, night owl", "Burning the midnight oil?", "Still up, {name}?", "Late night, {name}?"];
const ANYTIME: Pool = ["Hello", "Hi there", "Hello, {name}", "Welcome back, {name}", "What are we working on?"];

const MONDAY: Pool = ["Happy Monday", "Happy Monday, {name}"];
const FRIDAY: Pool = ["Happy Friday", "Happy Friday, {name}"];
const WEEKEND: Pool = ["Enjoying the weekend?", "Working on a weekend?"];

/** Local hour, not UTC -- a thread opened at 8am should say "morning"
 * regardless of what timezone the backend or server clock is in. */
function poolForTime(date: Date): Pool {
  const hour = date.getHours();
  const day = date.getDay();
  const byTime = hour >= 5 && hour < 12 ? MORNING : hour >= 12 && hour < 18 ? AFTERNOON : hour >= 18 && hour < 23 ? EVENING : NIGHT;
  const byDay = day === 1 ? MONDAY : day === 5 ? FRIDAY : day === 0 || day === 6 ? WEEKEND : [];
  return [...byTime, ...ANYTIME, ...byDay];
}

/** `random` is injected so a test can pin the choice. */
export function pickGreeting(date: Date, name: string, random: () => number = Math.random): string {
  const who = name.trim();
  const pool = poolForTime(date).filter((line) => who !== "" || !line.includes("{name}"));
  const line = pool[Math.min(Math.floor(random() * pool.length), pool.length - 1)];
  return line.replaceAll("{name}", who);
}
