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

/** The new-conversation heading above the centered message box. */
export function HomeGreeting() {
  const [name, setName] = useState<string | null>(null);
  // Picked once per mount so a re-render doesn't swap the line under the reader.
  const [random] = useState(() => Math.random());
  useEffect(() => {
    getConfig()
      .then((config) => setName(config.COSCRIBE_USER_NAME ?? ""))
      .catch(() => setName(""));
  }, []);
  return (
    <h1
      className="mb-7 px-4 text-center text-[40px] font-normal leading-tight text-[var(--fg)]"
      style={{ fontFamily: "Georgia, 'Times New Roman', serif" }}
    >
      {/* Held back until the name is known, so the line doesn't change after it shows. */}
      {name !== null && `${pickGreeting(new Date(), name, () => random)}!`}
    </h1>
  );
}
