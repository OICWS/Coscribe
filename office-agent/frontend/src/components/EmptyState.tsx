import { useEffect, useState } from "react";
import { pickGreeting } from "../lib/greetings";
import { getConfig } from "../lib/rest";

export function EmptyState() {
  const greeting = pickGreeting(new Date(), "");
  return (
    <div className="flex h-full items-center justify-center px-4">
      <h1 className="gradient-text text-xl font-semibold">{greeting}</h1>
    </div>
  );
}

// Module-level so it outlives the heading, which remounts each time home opens.
let lastShown = "";

/** The new-conversation heading above the centered message box. */
export function HomeGreeting() {
  // Picked once per mount, after the name is known, so the line doesn't change once shown.
  const [greeting, setGreeting] = useState("");
  useEffect(() => {
    getConfig()
      .then((config) => config.COSCRIBE_USER_NAME ?? "")
      .catch(() => "")
      .then((name) => {
        lastShown = pickGreeting(new Date(), name, Math.random, lastShown);
        setGreeting(lastShown);
      });
  }, []);
  return (
    <h1
      className="mb-7 px-4 text-center text-[40px] font-normal leading-tight text-[var(--fg)]"
      style={{ fontFamily: "Georgia, 'Times New Roman', serif" }}
    >
      {greeting}
    </h1>
  );
}
