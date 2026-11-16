"use client";

import { AlertTriangle, CheckCircle2, Info, Loader2, RefreshCw, Table2, BarChart3, X, XCircle } from "lucide-react";
import { useEffect, useId, useRef, useState, type ReactNode } from "react";
import Link from "next/link";
import { MODE_LABEL, date, num } from "@/lib/format";
import { isUrduScript } from "@/lib/text";
import type { Meta, Mode } from "@/lib/types";

// Patterns adapted from Repo B (signalspend-ai components/ui.tsx): PageHead, Panel, Notice, Kpi, Empty, Skeleton.

export function PageHead({ eyebrow, title, children, actions }: { eyebrow: string; title: string; children?: ReactNode; actions?: ReactNode }) {
  return (
    <header className="page-head">
      <div style={{ minWidth: 0 }}>
        <div className="eyebrow">{eyebrow}</div>
        <h1>{title}</h1>
        {children && <p>{children}</p>}
      </div>
      {actions && <div className="btn-row">{actions}</div>}
    </header>
  );
}

export function Panel({ title, description, actions, children, flat, id, className }: {
  title?: ReactNode; description?: ReactNode; actions?: ReactNode; children: ReactNode; flat?: boolean; id?: string; className?: string;
}) {
  const hid = useId();
  return (
    <section className={`panel${flat ? " flat" : ""}${className ? ` ${className}` : ""}`} id={id} aria-labelledby={title ? hid : undefined}>
      {(title || actions) && (
        <div className="panel-head">
          <div style={{ minWidth: 0 }}>
            {title && <h2 className="section" id={hid}>{title}</h2>}
            {description && <p>{description}</p>}
          </div>
          {actions && <div className="btn-row">{actions}</div>}
        </div>
      )}
      {children}
    </section>
  );
}

export function Notice({ tone = "info", title, children }: { tone?: "info" | "warn" | "error" | "ok"; title?: string; children?: ReactNode }) {
  const Icon = tone === "error" ? XCircle : tone === "warn" ? AlertTriangle : tone === "ok" ? CheckCircle2 : Info;
  const color = tone === "error" ? "var(--critical)" : tone === "warn" ? "var(--amber)" : tone === "ok" ? "var(--ok)" : "var(--violet)";
  return (
    <div className={`notice ${tone}`} role={tone === "error" ? "alert" : "status"}>
      <Icon size={17} color={color} aria-hidden="true" />
      <div style={{ minWidth: 0 }}>
        {title && <strong style={{ display: "block" }}>{title}</strong>}
        {children}
      </div>
    </div>
  );
}

export function Skeleton({ height = 120 }: { height?: number }) {
  return <div className="skeleton" style={{ height }} aria-hidden="true" />;
}

export function LoadingPage({ label = "Loading analysis…" }: { label?: string }) {
  return (
    <div className="grid" aria-busy="true">
      <span className="sr-only" role="status">{label}</span>
      <Skeleton height={70} />
      <div className="grid cols-4">{[0, 1, 2, 3].map((i) => <Skeleton key={i} height={92} />)}</div>
      <div className="grid cols-2"><Skeleton height={280} /><Skeleton height={280} /></div>
    </div>
  );
}

export function Busy({ text }: { text: string }) {
  return (
    <div className="notice" role="status" aria-live="polite">
      <Loader2 size={17} className="spin" color="var(--accent)" aria-hidden="true" />
      <span>{text}</span>
    </div>
  );
}

export function Empty({ title, children, action }: { title: string; children?: ReactNode; action?: ReactNode }) {
  return (
    <div className="empty">
      <h2>{title}</h2>
      {children && <p style={{ maxWidth: 560 }}>{children}</p>}
      {action}
    </div>
  );
}

export function ErrorState({ error, status, onRetry }: { error: string; status?: number | null; onRetry?: () => void }) {
  const title = status === 404 ? "Not found" : status === 410 ? "Dataset expired" : status === 403 ? "Not allowed here" : "Could not load this view";
  return (
    <Notice tone="error" title={title}>
      <span>{error}</span>
      {onRetry && (
        <div style={{ marginTop: 8 }}>
          <button className="btn sm" type="button" onClick={onRetry}>
            <RefreshCw size={14} aria-hidden="true" /> Retry
          </button>
        </div>
      )}
    </Notice>
  );
}

export function Kpi({ label, value, sub, na, help, href }: { label: string; value: string; sub?: ReactNode; na?: boolean; help?: string; href?: string }) {
  const body = (
    <>
      <div className="kpi-label">
        {label}
        {help && <span title={help} aria-label={`Definition: ${help}`} tabIndex={href ? -1 : 0} style={{ cursor: "help" }}>ⓘ</span>}
      </div>
      <div className={`kpi-value${na ? " na" : ""}`}>{value}</div>
      {sub && <div className="kpi-sub">{sub}</div>}
    </>
  );
  return href ? <Link href={href} className="kpi">{body}<span className="sr-only"> — open evidence</span></Link> : <div className="kpi">{body}</div>;
}

/** Comment/excerpt text with per-excerpt direction: Urdu script → rtl + Naskh font; English/Roman Urdu → ltr. */
export function Bidi({ text, className }: { text: string; className?: string }) {
  const urdu = isUrduScript(text);
  return <span dir={urdu ? "rtl" : "ltr"} lang={urdu ? "ur" : undefined} className={`${urdu ? "urdu" : "bidi"}${className ? ` ${className}` : ""}`}>{text}</span>;
}

export function ModeBadge({ mode }: { mode: Mode }) {
  const title = mode === "synthetic" ? "Simulated data — not real social-media observations" : mode === "observed" ? "Observed via an official API" : "Uploaded by a user with attested permission";
  return <span className={`badge ${mode}`} title={title}>{MODE_LABEL[mode] ?? mode}</span>;
}

/** Consistent method note: source mode, N posts / comments, date window, snapshot. */
export function MethodNote({ meta, posts, comments, extra }: { meta?: Meta | null; posts?: number | null; comments?: number | null; extra?: ReactNode }) {
  if (!meta) return null;
  return (
    <div className="method-note" aria-label="Data used for this view">
      <ModeBadge mode={meta.mode} />
      {posts !== undefined && posts !== null && <span className="chip num">N posts {num(posts)}</span>}
      {comments !== undefined && comments !== null && <span className="chip num">N comments {num(comments)}</span>}
      {meta.sample_size !== null && posts === undefined && comments === undefined && <span className="chip num">n = {num(meta.sample_size)}</span>}
      <span className="chip">Snapshot {date(meta.snapshot_at)}</span>
      {meta.run_id && <span className="chip mono" title="Run identifier">{meta.run_id}</span>}
      {meta.model_version && <span className="chip mono">{meta.model_version}</span>}
      {Object.keys(meta.filters || {}).length > 0 && <span className="chip">Filtered</span>}
      {extra}
    </div>
  );
}

export function Segmented<T extends string>({ value, options, onChange, label }: { value: T; options: { value: T; label: string }[]; onChange: (v: T) => void; label: string }) {
  return (
    <div className="segmented" role="group" aria-label={label}>
      {options.map((o) => (
        <button key={o.value} type="button" aria-pressed={o.value === value} onClick={() => onChange(o.value)}>{o.label}</button>
      ))}
    </div>
  );
}

/** Chart ⇄ table parity toggle: every chart offers its data as an accessible table. */
export function ChartTable({ chart, table, summary, label }: { chart: ReactNode; table: ReactNode; summary: string; label: string }) {
  const [mode, setMode] = useState<"chart" | "table">("chart");
  return (
    <div className="stack">
      <div className="row" style={{ justifyContent: "space-between" }}>
        <p className="faint" style={{ maxWidth: 720 }}>{summary}</p>
        <div className="segmented" role="group" aria-label={`${label}: view as`}>
          <button type="button" aria-pressed={mode === "chart"} onClick={() => setMode("chart")}><BarChart3 size={14} aria-hidden="true" /> Chart</button>
          <button type="button" aria-pressed={mode === "table"} onClick={() => setMode("table")}><Table2 size={14} aria-hidden="true" /> Table</button>
        </div>
      </div>
      {mode === "chart" ? <div role="img" aria-label={`${label}. ${summary}`}>{chart}</div> : table}
    </div>
  );
}

export function Drawer({ open, title, subtitle, onClose, children }: { open: boolean; title: ReactNode; subtitle?: ReactNode; onClose: () => void; children: ReactNode }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const prev = document.activeElement as HTMLElement | null;
    ref.current?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") { onClose(); return; }
      if (e.key !== "Tab" || !ref.current) return;
      // aria-modal: keep Tab / Shift+Tab inside the drawer
      const items = [...ref.current.querySelectorAll<HTMLElement>('a[href], button:not([disabled]), select, input, textarea, [tabindex]:not([tabindex="-1"])')].filter((el) => el.offsetParent !== null);
      if (!items.length) { e.preventDefault(); ref.current.focus(); return; }
      const first = items[0];
      const last = items[items.length - 1];
      const active = document.activeElement;
      if (e.shiftKey && (active === first || active === ref.current)) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && (active === last || !ref.current.contains(active))) { e.preventDefault(); first.focus(); }
    };
    window.addEventListener("keydown", onKey);
    return () => {
      window.removeEventListener("keydown", onKey);
      prev?.focus?.();
    };
  }, [open, onClose]);
  if (!open) return null;
  return (
    <>
      <div className="drawer-scrim" onClick={onClose} aria-hidden="true" />
      <div className="drawer" role="dialog" aria-modal="true" aria-label={typeof title === "string" ? title : "Details"} tabIndex={-1} ref={ref}>
        <div className="drawer-head">
          <div style={{ minWidth: 0 }}>
            <h2 className="section">{title}</h2>
            {subtitle && <div className="faint" style={{ marginTop: 2 }}>{subtitle}</div>}
          </div>
          <button className="btn ghost sm" type="button" onClick={onClose} aria-label="Close details"><X size={18} /></button>
        </div>
        <div className="drawer-body">{children}</div>
      </div>
    </>
  );
}

export function LowSample({ n, min = 20, what = "posts" }: { n: number; min?: number; what?: string }) {
  if (n >= min) return null;
  return <Notice tone="warn" title="Low sample size">Only {n} {what} match this view (minimum {min} for a reliable comparison). Treat patterns as anecdotal.</Notice>;
}

export function Pager({ page, pages, total, onPage }: { page: number; pages: number; total: number; onPage: (p: number) => void }) {
  return (
    <nav className="row" aria-label="Pagination" style={{ justifyContent: "space-between" }}>
      <span className="faint num">{num(total)} rows · page {page} of {pages}</span>
      <div className="btn-row">
        <button className="btn sm" type="button" disabled={page <= 1} onClick={() => onPage(page - 1)}>Previous</button>
        <button className="btn sm" type="button" disabled={page >= pages} onClick={() => onPage(page + 1)}>Next</button>
      </div>
    </nav>
  );
}

export function TextCell({ text, withheld }: { text: string | null; withheld?: boolean }) {
  if (withheld || text === null) return <span className="faint">[text withheld — no permission to show]</span>;
  return <Bidi text={text} />;
}
