/** The same spinner as the desktop shell's own splash (office-agent-desktop/src/splash/index.html),
 * which hands off to this page once the server answers, so the switch between them is invisible
 * and the app only appears once it has real data to show. */
export function StartupSplash() {
  return (
    <div className="flex h-full items-center justify-center bg-[var(--bg)]">
      <div
        className="h-7 w-7 animate-spin rounded-full border-[3px] border-[color-mix(in_srgb,var(--fg)_15%,transparent)] border-t-[var(--accent)] motion-reduce:animate-none"
        role="status"
        aria-label="Loading"
      />
    </div>
  );
}
