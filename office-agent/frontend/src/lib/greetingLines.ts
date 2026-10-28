/** Greeting lines for the new-conversation heading, grouped by when they fit.
 * `{name}` is replaced with the person's name; a line with it is only drawn
 * when a name is set. Add lines freely: greetings.test.ts checks every group
 * stays usable without a name. */
export type Pool = readonly string[];

export const MORNING: Pool = [
  "Good morning",
  "Good morning, {name}",
  "A fresh page, and the whole morning to fill it",
  "The day is still unwritten",
  "Coffee's warm, the page is blank",
  "Morning light suits good work, {name}",
  "Early hours, clear mind",
  "The best drafts begin before the inbox wakes up",
  "Sunrise is just the world's first draft",
  "Nothing is on fire yet. A good start",
  "Let's get ahead of the day, {name}",
  "Dew on the grass, cursor on the page",
  "The quiet before the meetings",
  "A new day, no edits yet",
  "Rise, shine, and outline",
  "Today's first sentence is yours, {name}",
];

export const AFTERNOON: Pool = [
  "Good afternoon",
  "Good afternoon, {name}",
  "The day has found its rhythm",
  "Halfway through the day, still plenty of room",
  "The long light of afternoon favors careful work",
  "Welcome back, {name}. Where were we?",
  "Steady hands, steady afternoon",
  "Lunch is behind us, the good part is ahead",
  "The post-lunch slump meets its match",
  "Afternoons were made for the unfinished",
  "Light slants in; so do the good ideas",
  "Midday is just a comma, not a full stop",
  "Let's make the second half count, {name}",
  "Clock's ticking, and the work is ready",
  "Still plenty of day left to work with",
  "The inbox can wait. This is the interesting part",
];

export const EVENING: Pool = [
  "Good evening",
  "Good evening, {name}",
  "The day is winding down, the thinking needn't",
  "Evening settles in. Let's finish well, {name}",
  "Golden hour for tying up loose ends",
  "A quiet evening for unhurried work",
  "What's worth finishing before the day closes?",
  "The lamp is on, the work is waiting",
  "Dusk is a fine time for a final draft",
  "One more good thing before you go home, {name}?",
  "The city softens; the work sharpens",
  "Tomorrow's you will thank tonight's you",
  "Dinner can wait ten minutes. Maybe",
  "Let the day end on a finished page",
  "The sky's doing its best work, and so can we",
  "Closing time for the day, opening time for ideas",
];

export const NIGHT: Pool = [
  "Hello, night owl",
  "Burning the midnight oil, {name}?",
  "The world is quiet, the ideas are loud",
  "Late hours belong to the curious, {name}",
  "Moonlit work, no interruptions",
  "Quiet hours, clear thoughts",
  "Still up? So are the best ideas",
  "Everyone else is asleep. Plenty of room to think",
  "The night shift of the mind",
  "Past midnight and still unfinished. Respect",
  "Stars out, deadline in",
  "Sleep is overrated, but only a little",
  "The quiet is working in your favor, {name}",
  "Nothing good was ever finished at 4 p.m. Allegedly",
  "A lamp, a page, and the whole dark to work in",
  "Late, but never too late for a good sentence",
];

export const ANYTIME: Pool = [
  "What shall we make today, {name}?",
  "Where should we begin?",
  "Every good document starts with a first line",
  "Bring me the messy draft. We'll find the shape in it",
  "Ideas in, finished work out",
  "A blank page is only a possibility",
  "Tell me the problem, keep the credit",
  "Spreadsheets, slides, sentences. Pick one",
  "What are we building, {name}?",
  "Show me the rough version",
  "Good work starts with a good question",
  "The page is ready when you are",
  "Let's turn the pile into a plan",
  "Make something worth reading",
  "Where did we leave off, {name}?",
  "A task, a hunch, a half-formed idea. Any will do",
  "Ready to read, write, and rearrange",
  "Hand me the tangle, I'll find the thread",
  "Draft first, polish later",
  "What would you like to be done by lunch?",
  "Small tasks and large ones are equally welcome",
  "Let's make the boring parts disappear, {name}",
  "Lay it all out. I'll sort it",
  "Your move, {name}",
];

export const MONDAY: Pool = [
  "A new week begins. Let's make it count",
  "Monday, a clean slate, {name}",
  "Fresh week, fresh page",
  "The week is unwritten. Let's draft it",
  "Monday: the hardest day to start and the best one to plan",
  "Seven days, zero edits so far",
];

export const FRIDAY: Pool = [
  "Friday: finish strong, {name}",
  "The week's last stretch. Let's land it",
  "Almost the weekend. Let's tie off the loose threads",
  "One more push and the week is yours, {name}",
  "Friday has its own kind of light",
  "Close the week with something finished",
];

export const WEEKEND: Pool = [
  "A weekend of your own making",
  "Weekend hours, unhurried work, {name}",
  "Working on a weekend? Respect, and good coffee",
  "No meetings today. Just the work",
  "Slow Sunday, sharp mind",
  "The calendar is quiet. The page is not",
  "Saturday pace: no hurry, all focus",
  "Weekends are for the projects that matter, {name}",
];

export const SPRING: Pool = [
  "Spring is a good time for fresh starts",
  "Everything's in bloom, including your ideas, {name}",
  "A new season, a new draft",
  "Clear skies, clearer thinking",
  "Spring cleaning for the to-do list?",
  "Green shoots and first drafts",
];

export const SUMMER: Pool = [
  "Long days, longer drafts",
  "Summer light, easy pace, serious work",
  "The window's open, the mind with it, {name}",
  "Warm afternoons make for loose thinking",
  "Heat outside, calm inside",
  "All the daylight you could want",
];

export const AUTUMN: Pool = [
  "Autumn is for gathering things in",
  "Leaves turn; so can the plan, {name}",
  "A good season for finishing what you started",
  "Crisp air, crisp thinking",
  "Time to harvest the year's work",
  "The year is turning. What's left to do?",
];

export const WINTER: Pool = [
  "Cold outside, warm lamp inside",
  "Winter evenings were made for deep work",
  "Short days, long thoughts, {name}",
  "A good season for quiet, careful work",
  "Hot tea and a hard problem",
  "Snug indoors, sharp on the page",
];
