"use client";

import { FilterX } from "lucide-react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback, useMemo } from "react";
import { useApi } from "@/lib/api";
import { countActive, readFilters, withParam, type FilterKey, type FilterState } from "@/lib/query";
import type { Options } from "@/lib/types";
import { useDataset } from "./dataset";

/** Filters live in the URL (shareable, back-button friendly). Must be rendered inside <Suspense>. */
export function useFilters() {
  const sp = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  const filters = useMemo<FilterState>(() => readFilters(sp), [sp]);
  const setParam = useCallback((key: string, value: string | string[] | null) => {
    const next = withParam(new URLSearchParams(sp.toString()), key, value);
    const qs = next.toString();
    router.replace(`${pathname}${qs ? `?${qs}` : ""}`, { scroll: false });
  }, [sp, router, pathname]);
  const clear = useCallback(() => router.replace(pathname, { scroll: false }), [router, pathname]);
  const get = useCallback((key: string) => sp.get(key), [sp]);
  return { filters, setParam, clear, get, params: sp };
}

export function useOptions() {
  const { datasetId } = useDataset();
  return useApi<Options>(datasetId ? "/options" : null, { dataset_id: datasetId });
}

function Select({ id, label, value, options, onChange }: { id: FilterKey; label: string; value: string; options: { value: string; label: string }[]; onChange: (v: string) => void }) {
  return (
    <label className="field" htmlFor={`f-${id}`}>
      {label}
      <select id={`f-${id}`} className="select" value={value} onChange={(e) => onChange(e.target.value)}>
        <option value="">All</option>
        {options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>
    </label>
  );
}

export function FilterBar({ show = ["platform", "brand", "campaign", "content_type", "date"] }: { show?: string[] }) {
  const { filters, setParam, clear } = useFilters();
  const opts = useOptions();
  const o = opts.data;
  const one = (k: FilterKey) => filters[k]?.[0] ?? "";
  return (
    <div className="filterbar" role="search" aria-label="Filters">
      {show.includes("platform") && <Select id="platform" label="Platform" value={one("platform")} onChange={(v) => setParam("platform", v || null)} options={(o?.platforms ?? []).map((p) => ({ value: p, label: p }))} />}
      {show.includes("brand") && <Select id="brand" label="Brand" value={one("brand")} onChange={(v) => setParam("brand", v || null)} options={(o?.brands ?? []).map((p) => ({ value: p, label: p }))} />}
      {show.includes("campaign") && <Select id="campaign" label="Campaign" value={one("campaign")} onChange={(v) => setParam("campaign", v || null)} options={(o?.campaigns ?? []).map((p) => ({ value: p, label: p }))} />}
      {show.includes("content_type") && <Select id="content_type" label="Content type" value={one("content_type")} onChange={(v) => setParam("content_type", v || null)} options={(o?.content_types ?? []).map((p) => ({ value: String(p.value), label: p.label }))} />}
      {show.includes("date") && (
        <>
          <label className="field" htmlFor="f-date_from">From
            <input id="f-date_from" type="date" className="input" value={one("date_from")} min={o?.date_min} max={o?.date_max} onChange={(e) => setParam("date_from", e.target.value || null)} />
          </label>
          <label className="field" htmlFor="f-date_to">To
            <input id="f-date_to" type="date" className="input" value={one("date_to")} min={o?.date_min} max={o?.date_max} onChange={(e) => setParam("date_to", e.target.value || null)} />
          </label>
        </>
      )}
      <button className="btn sm" type="button" onClick={clear} disabled={countActive(filters) === 0} style={{ alignSelf: "flex-end", marginBottom: 2 }}>
        <FilterX size={14} aria-hidden="true" /> Clear{countActive(filters) ? ` (${countActive(filters)})` : ""}
      </button>
    </div>
  );
}
