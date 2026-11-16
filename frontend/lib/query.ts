/** URL/query helpers (pure; unit-tested in tests/query.test.ts). */

export const FILTER_KEYS = ["platform", "brand", "campaign", "content_type", "date_from", "date_to"] as const;
export type FilterKey = (typeof FILTER_KEYS)[number];
export type FilterState = Partial<Record<FilterKey, string[]>>;

type Scalar = string | number | boolean | null | undefined;

/** Build "?a=1&b=x&b=y" from scalars and arrays; empty values are dropped; order is stable. */
export function buildQuery(params: Record<string, Scalar | Scalar[]>): string {
  const sp = new URLSearchParams();
  for (const key of Object.keys(params).sort()) {
    const value = params[key];
    const list = Array.isArray(value) ? value : [value];
    for (const v of list) {
      if (v === null || v === undefined || v === "") continue;
      sp.append(key, String(v));
    }
  }
  const s = sp.toString();
  return s ? `?${s}` : "";
}

/** Read the filter keys from URLSearchParams (multi-valued). */
export function readFilters(sp: URLSearchParams | { getAll(k: string): string[] }): FilterState {
  const out: FilterState = {};
  for (const k of FILTER_KEYS) {
    const vals = sp.getAll(k).filter(Boolean);
    if (vals.length) out[k] = vals;
  }
  return out;
}

export function countActive(f: FilterState): number {
  return FILTER_KEYS.reduce((n, k) => n + (f[k]?.length ? 1 : 0), 0);
}

/** Replace one key in a URLSearchParams copy (null/[] removes it); resets pagination. */
export function withParam(sp: URLSearchParams, key: string, value: string | string[] | null): URLSearchParams {
  const next = new URLSearchParams(sp.toString());
  next.delete(key);
  next.delete("page");
  const list = value === null ? [] : Array.isArray(value) ? value : [value];
  for (const v of list) if (v !== "") next.append(key, v);
  return next;
}
