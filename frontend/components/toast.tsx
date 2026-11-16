"use client";

import { AlertTriangle, CheckCircle2, X } from "lucide-react";
import { createContext, useCallback, useContext, useState, type ReactNode } from "react";

type Toast = { id: number; tone: "ok" | "error"; text: string };
const ToastContext = createContext<(text: string, tone?: "ok" | "error") => void>(() => {});

/** Lightweight toasts announced to screen readers (role=status / alert). */
export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<Toast[]>([]);
  const push = useCallback((text: string, tone: "ok" | "error" = "ok") => {
    const id = Date.now() + Math.random();
    setItems((xs) => [...xs.slice(-2), { id, tone, text }]);
    window.setTimeout(() => setItems((xs) => xs.filter((t) => t.id !== id)), 4500);
  }, []);
  return (
    <ToastContext.Provider value={push}>
      {children}
      <div className="toasts" aria-live="polite">
        {items.map((t) => (
          <div key={t.id} className={`toast ${t.tone}`} role={t.tone === "error" ? "alert" : "status"}>
            {t.tone === "error" ? <AlertTriangle size={16} color="var(--critical)" aria-hidden="true" /> : <CheckCircle2 size={16} color="var(--ok)" aria-hidden="true" />}
            <span style={{ flex: 1 }}>{t.text}</span>
            <button type="button" className="btn ghost sm" aria-label="Dismiss notification" onClick={() => setItems((xs) => xs.filter((x) => x.id !== t.id))}><X size={14} /></button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  return useContext(ToastContext);
}
