/** How a provider is reached, as Discover's cards and Yours' rows say it. */
export function providerKind({ builtin, base_url }: { builtin: boolean; base_url: string | null }): string {
  if (builtin) return "Built in";
  if (base_url && /^https?:\/\/(localhost|127\.0\.0\.1)[:/]/.test(base_url)) return "On this computer";
  return "OpenAI-compatible";
}
