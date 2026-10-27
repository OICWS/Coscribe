import { useCallback, useEffect, useState } from "react";
import type { LibreOfficeStatus } from "../types/settings";
import { downloadLibreOffice, getLibreOffice, removeLibreOffice } from "./rest";

const NOT_FOUND: LibreOfficeStatus = {
  found: false,
  source: null,
  path: null,
  version: null,
  offer: null,
  working: false,
  step: "",
  done: 0,
  total: 0,
  error: "",
};

/** The LibreOffice on this computer, re-read each second while a download is under way (the
 * download request itself returns at once). */
export function useLibreOffice(active: boolean) {
  const [status, setStatus] = useState<LibreOfficeStatus | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(() => {
    getLibreOffice()
      .then(setStatus)
      .catch(() => setStatus(NOT_FOUND));
  }, []);

  useEffect(() => {
    if (active) refresh();
  }, [active, refresh]);

  const working = Boolean(status?.working);
  useEffect(() => {
    if (!active || !working) return;
    const timer = window.setInterval(refresh, 1000);
    return () => window.clearInterval(timer);
  }, [active, working, refresh]);

  const run = async (action: typeof downloadLibreOffice) => {
    setError(null);
    const result = await action();
    if ("error" in result) setError(result.error);
    else setStatus(result);
  };

  return { status, error, download: () => run(downloadLibreOffice), remove: () => run(removeLibreOffice) };
}

export function libreOfficeSummary(status: LibreOfficeStatus | null): string {
  if (status === null) return "Checking…";
  if (status.working) return "Downloading…";
  if (!status.found) return "Not found";
  return status.version ? `LibreOffice ${status.version} found` : "Found";
}
