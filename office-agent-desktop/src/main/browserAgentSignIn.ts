/**
 * A step that failed because the site wants the person: a sign-in form, a
 * verification code or a captcha. The error then says so with a mark the
 * server turns into a request to the person (a saved workflow's run waits
 * for them, then runs the step again), instead of a failure a heal would
 * try to click past.
 */

import type { WebContents } from "electron";
import type { TabCdp } from "./browserCdp";

export const SIGN_IN_MARK = "NEEDS_SIGN_IN:";

/** Run in the page like pageAgent (browserAgentPage.ts), so self-contained. */
export function pageSignIn(_action: string, _args: Record<string, unknown>): unknown {
  const shown = (el: Element) => {
    const rect = el.getBoundingClientRect();
    return rect.width > 0 && rect.height > 0 && getComputedStyle(el).visibility !== "hidden";
  };
  const any = (selector: string) => Array.from(document.querySelectorAll(selector)).some(shown);
  if (any('iframe[src*="recaptcha"], iframe[src*="hcaptcha"], iframe[src*="challenges.cloudflare.com"], [id*="captcha" i], [class*="captcha" i], [class*="geetest" i]')) return "captcha";
  if (any('input[autocomplete="one-time-code"]')) return "code";
  // A settings page can hold a password field too; a sign-in page also says so.
  const words = /log\s*-?\s*in|sign\s*-?\s*in|登录|登入|登陆/i;
  const labels = Array.from(document.querySelectorAll('button, input[type="submit"], h1, h2, a[role="button"]'))
    .filter(shown).map((el) => (el as HTMLElement).innerText || (el as HTMLInputElement).value || "");
  const says = words.test(location.pathname) || words.test(document.title) || labels.some((text) => words.test(text));
  if (says && any('input[type="password"]')) return "password";
  return "";
}

/** The step's error, marked when the page now asks for the person. */
export async function signInNeeded(cdp: TabCdp, wc: WebContents, message: string): Promise<string> {
  if (message.startsWith("NEEDS_")) return message;
  let host = "";
  try {
    const url = new URL(wc.getURL());
    if (url.protocol === "http:" || url.protocol === "https:") host = url.hostname.replace(/^www\./, "");
  } catch {
    return message;
  }
  if (!host) return message;
  const reason = await cdp.agent<string>(cdp.main, "sign_in", {}, pageSignIn).catch(() => "");
  return reason ? `${SIGN_IN_MARK}${reason}:${host} ${message}` : message;
}
