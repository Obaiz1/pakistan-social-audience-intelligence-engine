"use client";

import {
  BookOpen, ChevronsLeft, ChevronsRight, Database, FileDown, FlaskConical, LayoutDashboard, Megaphone, Menu,
  MessageSquareText, Moon, Sun, X,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";
import { date } from "@/lib/format";
import { DatasetProvider, useDataset } from "./dataset";
import { ToastProvider } from "./toast";
import { ModeBadge, Notice } from "./ui";

type NavItem = { href: string; label: string; icon?: typeof LayoutDashboard; qnum?: number; q?: string; section: string };

// Navigation follows the assignment story: attention → needs → unusual → segments → action.
export const NAV: { label: string; items: NavItem[] }[] = [
  { label: "Start", items: [{ href: "/", label: "Overview", icon: LayoutDashboard, q: "Q1–Q5", section: "Start" }] },
  {
    label: "The five questions",
    items: [
      { href: "/content", label: "Attention", qnum: 1, section: "Q1 · Which content attracts attention?" },
      { href: "/audience", label: "Audience needs", qnum: 2, section: "Q2 · What does the audience want?" },
      { href: "/anomalies", label: "Anomaly lab", qnum: 3, section: "Q3 · Which patterns are unusual?" },
      { href: "/segments", label: "Segments", qnum: 4, section: "Q4 · Which needs should we address?" },
      { href: "/recommendations", label: "Action center", qnum: 5, section: "Q5 · What should we do next?" },
    ],
  },
  {
    label: "Explore",
    items: [
      { href: "/comments", label: "Comment explorer", icon: MessageSquareText, q: "Q2", section: "Explore" },
      { href: "/campaigns", label: "Campaigns", icon: Megaphone, q: "Q1·Q4", section: "Explore" },
    ],
  },
  {
    label: "Evidence & data",
    items: [
      { href: "/data", label: "Data hub", icon: Database, section: "Evidence & data" },
      { href: "/model", label: "Model lab", icon: FlaskConical, section: "Evidence & data" },
      { href: "/reports", label: "Reports", icon: FileDown, section: "Evidence & data" },
      { href: "/methodology", label: "Methodology", icon: BookOpen, section: "Evidence & data" },
    ],
  },
];
const ALL = NAV.flatMap((g) => g.items);

const SUBPAGE_LABEL: Record<string, string> = { brief: "Executive brief" };

function ThemeToggle() {
  const [theme, setTheme] = useState<"dark" | "light" | null>(null);
  useEffect(() => {
    const t = document.documentElement.dataset.theme as "dark" | "light" | undefined;
    // eslint-disable-next-line react-hooks/set-state-in-effect -- read the theme applied by the pre-paint script
    setTheme(t ?? (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light"));
  }, []);
  const next = theme === "dark" ? "light" : "dark";
  return (
    <button type="button" className="btn ghost sm" aria-label={`Switch to ${next} theme`} title={`Switch to ${next} theme`} onClick={() => {
      document.documentElement.dataset.theme = next;
      try { localStorage.setItem("audienceiq.theme", next); } catch { /* not persisted */ }
      setTheme(next);
    }}>
      {theme === "dark" ? <Sun size={16} aria-hidden="true" /> : <Moon size={16} aria-hidden="true" />}
    </button>
  );
}

function DatasetSwitcher() {
  const { datasets, datasetId, dataset, select } = useDataset();
  if (!datasets.length) return null;
  return (
    <div className="row" style={{ gap: 8, flexWrap: "nowrap", minWidth: 0 }}>
      {dataset && <ModeBadge mode={dataset.mode} />}
      {dataset && <span className="freshness">snapshot {date(dataset.snapshot_at)}{dataset.expires_at ? ` · expires ${date(dataset.expires_at)}` : ""}</span>}
      <label className="sr-only" htmlFor="dataset-switch">Dataset</label>
      <select id="dataset-switch" className="select" style={{ maxWidth: 270 }} value={datasetId ?? ""} onChange={(e) => select(e.target.value)}>
        {datasets.map((d) => (
          <option key={d.dataset_id} value={d.dataset_id} disabled={d.expired}>
            {d.mode === "observed" ? "Observed · " : d.mode === "synthetic" ? "Synthetic · " : "Imported · "}{d.name}{d.expired ? " (expired)" : ""}
          </option>
        ))}
      </select>
    </div>
  );
}

function Banner() {
  const { dataset } = useDataset();
  if (!dataset) return null;
  return (
    <div className={`banner ${dataset.mode}`} role="note" aria-label="Data source mode">
      <span>{dataset.disclaimer}</span>
      <span style={{ fontWeight: 500 }}>· {dataset.post_count.toLocaleString("en-PK")} posts · {dataset.comment_count.toLocaleString("en-PK")} comments · snapshot {date(dataset.snapshot_at)}</span>
    </div>
  );
}

function Frame({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const { error, loading, refresh, health } = useDataset();
  const current = ALL.find((i) => (i.href === "/" ? pathname === "/" : pathname === i.href || pathname.startsWith(`${i.href}/`)));
  const subSlug = current && pathname !== current.href ? pathname.slice(current.href.length + 1) : null;
  const subpage = subSlug ? (SUBPAGE_LABEL[subSlug] ?? subSlug.replace(/[-_]/g, " ").replace(/^./, (c) => c.toUpperCase())) : null;
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- close the mobile drawer after navigation
    setOpen(false);
  }, [pathname]);
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);
  return (
    <div className="shell" data-collapsed={collapsed}>
      <div className="scrim" data-open={open} onClick={() => setOpen(false)} aria-hidden="true" />
      <nav className="rail" data-open={open} aria-label="Primary">
        <div className="row" style={{ justifyContent: "space-between", flexWrap: "nowrap" }}>
          <Link href="/" className="brand" title="AudienceIQ PK — overview">
            <span className="brand-mark" aria-hidden="true">AQ</span>
            <span className="brand-name">AudienceIQ PK<small>Understand your audience. Act with evidence.</small></span>
          </Link>
          <button className="btn ghost sm menu-toggle" type="button" aria-label="Close navigation" onClick={() => setOpen(false)}>
            <X size={18} />
          </button>
        </div>
        {NAV.map((group) => (
          <div className="nav-group" key={group.label}>
            <div className="nav-label">{group.label}</div>
            {group.items.map(({ href, label, icon: Icon, qnum, q }) => (
              <Link key={href} href={href} className="nav-link" aria-current={current?.href === href ? "page" : undefined} title={qnum ? `Q${qnum} · ${label}` : label}>
                {qnum ? <span className="qnum" aria-hidden="true">{qnum}</span> : Icon && <Icon size={17} aria-hidden="true" />}
                <span className="nav-text">{qnum ? <><span className="sr-only">Question {qnum}: </span>{label}</> : label}</span>
                {q && <span className="q">{q}</span>}
              </Link>
            ))}
          </div>
        ))}
        <div className="rail-foot">
          <span>{health?.hosted ? "Public read-only demo" : "Local mode"}{health?.version ? ` · v${health.version}` : ""}</span>
          <span>University Project 3 · clustering-based</span>
        </div>
      </nav>
      <div className="main">
        <Banner />
        <header className="topbar">
          <button className="btn ghost sm menu-toggle" type="button" aria-label="Open navigation" aria-expanded={open} onClick={() => setOpen(true)}>
            <Menu size={18} />
          </button>
          <button className="btn ghost sm collapse-toggle" type="button" aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"} onClick={() => setCollapsed((c) => !c)}>
            {collapsed ? <ChevronsRight size={17} /> : <ChevronsLeft size={17} />}
          </button>
          <nav className="crumbs" aria-label="Breadcrumb">
            <Link href="/">AudienceIQ</Link>
            {current && current.href !== "/" && <><span aria-hidden="true">/</span><span>{current.section.split(" · ")[0]}</span></>}
            <span aria-hidden="true">/</span>
            {subpage ? <><Link href={current!.href}>{current!.label}</Link><span aria-hidden="true">/</span><strong aria-current="page">{subpage}</strong></>
              : <strong aria-current="page">{current?.label ?? "Page"}</strong>}
          </nav>
          <div className="topbar-right">
            <DatasetSwitcher />
            <ThemeToggle />
          </div>
        </header>
        <main className="content" id="main" tabIndex={-1}>
          {error && !loading && (
            <Notice tone="error" title="Analysis service unavailable — no live data is being shown">
              {error}{" "}
              <button className="btn sm" type="button" onClick={() => void refresh()} style={{ marginTop: 8 }}>Retry connection</button>
            </Notice>
          )}
          {children}
        </main>
      </div>
    </div>
  );
}

export function Shell({ children }: { children: ReactNode }) {
  return (
    <DatasetProvider>
      <ToastProvider>
        <Frame>{children}</Frame>
      </ToastProvider>
    </DatasetProvider>
  );
}
