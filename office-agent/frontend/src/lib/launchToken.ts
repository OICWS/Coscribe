/** The token the server made for this launch and put in the page it served. A WebSocket handshake
 * and every request that changes state must carry it, so a page on another local port cannot
 * drive the server. Empty when the page comes from the Vite dev server, which adds the token to
 * what it proxies instead. */
const token = (): string =>
  document.querySelector<HTMLMetaElement>('meta[name="coscribe-token"]')?.content ?? "";

/** `url` with the token for a WebSocket, which cannot set a header. */
export function socketUrl(url: string): string {
  const value = token();
  return value ? `${url}${url.includes("?") ? "&" : "?"}token=${encodeURIComponent(value)}` : url;
}

/** Makes every same-origin fetch that is not a read carry the token. */
export function sendTokenWithWrites(): void {
  const value = token();
  if (!value) return;
  const plainFetch = window.fetch.bind(window);
  window.fetch = (input, init) => {
    const request = new Request(input, init);
    const sameOrigin = new URL(request.url, window.location.href).origin === window.location.origin;
    if (sameOrigin && !["GET", "HEAD", "OPTIONS"].includes(request.method)) {
      request.headers.set("x-coscribe-token", value);
    }
    return plainFetch(request);
  };
}
