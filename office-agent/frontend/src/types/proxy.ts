/** Settings › General › Proxy (issue #666), from web/routes/settings/proxy.py. */

export type ProxyMode = "system" | "manual" | "none";

export interface ProxySettings {
  mode: ProxyMode;
  address: string;
  bypass: string;
  username: string;
  /** The password itself is never sent to the page. */
  password_set: boolean;
  /** The proxy this running server uses, without a user name or password. */
  active: string | null;
  keychain: boolean;
  restart_required?: boolean;
}

export interface ProxyUpdate {
  mode: ProxyMode;
  address: string;
  bypass: string;
  username: string;
  /** null keeps the saved password; "" removes it. */
  password: string | null;
}

export interface ProxyTestResult {
  ok: boolean;
  target: string;
  status: number | null;
  error: string | null;
  proxy: string | null;
}
