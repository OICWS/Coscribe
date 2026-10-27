import { useEffect, useState } from "react";
import type { LibreOfficeStatus } from "../types/settings";
import { getLibreOffice } from "./rest";

export function useLibreOffice(active: boolean) {
  const [status, setStatus] = useState<LibreOfficeStatus | null>(null);
  useEffect(() => {
    if (!active) return;
    let cancelled = false;
    getLibreOffice()
      .then((result) => !cancelled && setStatus(result))
      .catch(() => !cancelled && setStatus({ found: false, source: null, path: null, version: null }));
    return () => {
      cancelled = true;
    };
  }, [active]);
  return status;
}

export function libreOfficeSummary(status: LibreOfficeStatus | null): string {
  if (status === null) return "Checking…";
  if (!status.found) return "Not found";
  return status.version ? `LibreOffice ${status.version} found` : "Found";
}
