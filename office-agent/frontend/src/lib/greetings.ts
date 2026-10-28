/** Greetings for the new-conversation heading. `{name}` is replaced with the
 * person's name; a line with it is only picked when there is a name. */
type Pool = readonly string[];

const MORNING: Pool = [
  "Good morning",
  "Good morning, {name}",
  "A fresh page, and the whole morning to fill it",
  "Morning light suits good work, {name}",
  "The day is still unwritten",
  "Coffee's warm, the page is blank",
  "Early hours, clear mind",
];
const AFTERNOON: Pool = [
  "Good afternoon",
  "Good afternoon, {name}",
  "The day has found its rhythm",
  "Halfway through the day, still plenty of room",
  "The long light of afternoon favors careful work",
  "Welcome back, {name}. Where were we?",
  "Steady hands, steady afternoon",
];
const EVENING: Pool = [
  "Good evening",
  "Good evening, {name}",
  "The day is winding down, the thinking needn't",
  "Evening settles in. Let's finish well, {name}",
  "Golden hour for tying up loose ends",
  "A quiet evening for unhurried work",
  "What's worth finishing before the day closes?",
];
const NIGHT: Pool = [
  "Hello, night owl",
  "Burning the midnight oil, {name}?",
  "The world is quiet, the ideas are loud",
  "Late hours belong to the curious, {name}",
  "Moonlit work, no interruptions",
  "Quiet hours, clear thoughts",
  "Still up? So are the best ideas",
];
const ANYTIME: Pool = [
  "What shall we make today, {name}?",
  "Where should we begin?",
  "Every good document starts with a first line",
  "Bring me the messy draft. We'll find the shape in it",
  "Ideas in, finished work out",
  "A blank page is only a possibility",
];

const MONDAY: Pool = ["A new week begins. Let's make it count", "Monday, a clean slate, {name}"];
const FRIDAY: Pool = ["Friday: finish strong, {name}", "The week's last stretch. Let's land it"];
const WEEKEND: Pool = ["A weekend of your own making", "Weekend hours, unhurried work, {name}"];

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
