"use client";

import { useCallback, useEffect, useState } from "react";
import { buildQuery } from "./query";

/** Thin typed client over /api/v1 (same-origin; proxied to FastAPI in dev). */
export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export const API = "/api/v1";

async function parse(res: Response): Promise<unknown> {
  const text = await res.text();
  let body: unknown = null;
  try {
    body = text ? JSON.parse(text) : null;
  } catch {
    body = text;
  }
  if (!res.ok) {
    const detail =
      body && typeof body === "object" && "detail" in body
        ? typeof (body as { detail: unknown }).detail === "string"
          ? (body as { detail: string }).detail
          : JSON.stringify((body as { detail: unknown }).detail)
        : `Request failed (${res.status})`;
    throw new ApiError(res.status, detail);
  }
  return body;
}

export async function getJson<T>(path: string, params: Record<string, unknown> = {}, signal?: AbortSignal): Promise<T> {
  const res = await fetch(`${API}${path}${buildQuery(params as Record<string, string>)}`, {
    signal,
    headers: { Accept: "application/json" },
    cache: "no-store",
  });
  return (await parse(res)) as T;
}

export async function postJson<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify(body),
  });
  return (await parse(res)) as T;
}

export async function deleteJson<T>(path: string): Promise<T> {
  const res = await fetch(`${API}${path}`, { method: "DELETE" });
  return (await parse(res)) as T;
}

export function errorText(err: unknown): string {
  if (err instanceof ApiError) return err.message;
  if (err instanceof Error) {
    if (err.name === "AbortError") return "Request cancelled.";
    if (/fetch|network/i.test(err.message)) return "The analysis service is unreachable. Check your connection and retry.";
    return err.message;
  }
  return "Unexpected error.";
}

export function exportUrl(params: Record<string, unknown>): string {
  return `${API}/reports/export${buildQuery(params as Record<string, string>)}`;
}

export type ApiState<T> = { data: T | null; error: string | null; status: number | null; loading: boolean; reload: () => void };

/** Fetch on mount / when the key changes; aborts stale requests; exposes reload. Pass path=null to skip. */
export function useApi<T>(path: string | null, params: Record<string, unknown> = {}): ApiState<T> {
  const key = path === null ? null : `${path}${buildQuery(params as Record<string, string>)}`;
  const [state, setState] = useState<{ data: T | null; error: string | null; status: number | null; key: string | null }>({
    data: null,
    error: null,
    status: null,
    key: null,
  });
  const [tick, setTick] = useState(0);
  useEffect(() => {
    if (key === null) return;
    const ctl = new AbortController();
    fetch(`${API}${key}`, { signal: ctl.signal, headers: { Accept: "application/json" }, cache: "no-store" })
      .then(parse)
      .then((data) => setState({ data: data as T, error: null, status: 200, key }))
      .catch((err) => {
        if (ctl.signal.aborted) return;
        setState({ data: null, error: errorText(err), status: err instanceof ApiError ? err.status : null, key });
      });
    return () => ctl.abort();
  }, [key, tick]);
  const reload = useCallback(() => setTick((t) => t + 1), []);
  const loading = path !== null && state.key !== key;
  return { data: loading ? null : state.data, error: loading ? null : state.error, status: state.status, loading, reload };
}
