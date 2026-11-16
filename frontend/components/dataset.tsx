"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { errorText, getJson } from "@/lib/api";
import type { DatasetList, DatasetSummary, Health } from "@/lib/types";

const STORAGE_KEY = "audienceiq.dataset";

type Ctx = {
  datasets: DatasetSummary[];
  datasetId: string | null;
  dataset: DatasetSummary | null;
  health: Health | null;
  writesEnabled: boolean;
  loading: boolean;
  error: string | null;
  select: (id: string) => void;
  refresh: () => Promise<void>;
};

const DatasetContext = createContext<Ctx | null>(null);

export function DatasetProvider({ children }: { children: ReactNode }) {
  const [list, setList] = useState<DatasetList | null>(null);
  const [health, setHealth] = useState<Health | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const [l, h] = await Promise.all([getJson<DatasetList>("/datasets"), getJson<Health>("/health")]);
      setList(l);
      setHealth(h);
      setError(null);
      let stored: string | null = null;
      try {
        stored = localStorage.getItem(STORAGE_KEY);
      } catch {
        /* storage unavailable */
      }
      const usable = l.datasets.filter((d) => !d.expired);
      setSelected((cur) => {
        const want = cur ?? stored;
        return want && usable.some((d) => d.dataset_id === want) ? want : l.default_dataset_id;
      });
    } catch (err) {
      setError(errorText(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- initial fetch of the dataset catalogue
    void refresh();
  }, [refresh]);

  const select = useCallback((id: string) => {
    setSelected(id);
    try {
      localStorage.setItem(STORAGE_KEY, id);
    } catch {
      /* not persisted */
    }
  }, []);

  const value = useMemo<Ctx>(() => {
    const datasets = list?.datasets ?? [];
    return {
      datasets,
      datasetId: selected,
      dataset: datasets.find((d) => d.dataset_id === selected) ?? null,
      health,
      writesEnabled: list?.writes_enabled ?? false,
      loading,
      error,
      select,
      refresh,
    };
  }, [list, selected, health, loading, error, select, refresh]);

  return <DatasetContext.Provider value={value}>{children}</DatasetContext.Provider>;
}

export function useDataset(): Ctx {
  const ctx = useContext(DatasetContext);
  if (!ctx) throw new Error("useDataset must be used inside DatasetProvider");
  return ctx;
}
