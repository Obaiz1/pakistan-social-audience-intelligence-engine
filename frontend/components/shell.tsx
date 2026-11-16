"use client";

import {
  AlertOctagon, BookOpen, ChevronsLeft, ChevronsRight, Database, FileDown, LayoutDashboard, Lightbulb, Megaphone,
  Menu, MessageSquareText, Moon, PlaySquare, Sun, UsersRound, X,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";
import { date } from "@/lib/format";
import { DatasetProvider, useDataset } from "./dataset";
import { ModeBadge, Notice } from "./ui";

// Shell structure adapted from Repo B (signalspend-ai components/shell.tsx); navigation and branding are Project 3's.
export const NAV = [
  { label: "Start", items: [{ href: "/", label: "Overview", icon: LayoutDashboard, q: "Q1–Q5" }] },
  {
    label: "Answer the five questions",
    items: [
      { href: "/content", label: "Content performance", icon: PlaySquare, q: "Q1" },
      { href: "/audience", label: "Audience needs", icon: UsersRound, q: "Q2·Q4" },
      { href: "/comments", label: "Comment explorer", icon: MessageSquareText, q: "Q2" },
      { href: "/anomalies", label: "Unusual patterns", icon: AlertOctagon, q: "Q3" },
      { href: "/campaigns", label: "Campaigns", icon: Megaphone, q: "Q1·Q4" },
      { href: "/recommendations", label: "Recommendations", icon: Lightbulb, q: "Q5" },
    ],
  },
  {
    label: "Data & method",
    items: [
      { href: "/data", label: "Data & imports", icon: Database },
      { href: "/reports", label: "Reports & exports", icon: FileDown },
      { href: "/methodology", label: "Methodology", icon: BookOpen },
    ],
  },
];
const ALL = NAV.flatMap((g) => g.items);

function ThemeToggle() {
  const [theme, setTheme] = useState<"dark" | "light" | null>(null);
  useEffect(() => {
    const t = document.documentElement.dataset.theme as "dark" | "light" | undefined;
    // eslint-disable-next-line react-hooks/set-state-in-effect -- read the theme applied by the pre-paint script
    setTheme(t ?? (window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark"));
  }, []);
  const next = theme === "light" ? "dark" : "light";
  return (
    <button type="button" className="btn ghost sm" aria-label={`Switch to ${next} theme`} onClick={() => {
      document.documentElement.dataset.theme = next;
      try { localStorage.setItem("audienceiq.theme", next); } catch { /* not persisted */ }
      setTheme(next);
    }}>
      {theme === "light" ? <Moon size={16} aria-hidden="true" /> : <Sun size={16} aria-hidden="true" />}
    </button>
  );
}

function DatasetSwitcher() {
  const { datasets, datasetId, dataset, select } = useDataset();
  if (!datasets.length) return null;
  return (
    <div className="row" style={{ gap: 8, flexWrap: "nowrap", minWidth: 0 }}>
      {dataset && <ModeBadge mode={dataset.mode} />}
      <label className="sr-only" htmlFor="dataset-switch">Dataset</label>
      <select id="dataset-switch" className="select" style={{ maxWidth: 260 }} value={datasetId ?? ""} onChange={(e) => select(e.target.value)}>
        {datasets.map((d) => (
          <option key={d.dataset_id} value={d.dataset_id} disabled={d.expired}>
            {d.name}{d.expired ? " (expired)" : ""}
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
    <div className={`banner ${dataset.mode}`} role="note">
      <span>{dataset.disclaimer}</span>
      <span style={{ fontWeight: 600, opacity: 0.9 }}>· {dataset.post_count.toLocaleString("en-PK")} posts · {dataset.comment_count.toLocaleString("en-PK")} comments · snapshot {date(dataset.snapshot_at)}</span>
    </div>
  );
}

function Frame({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const { error, loading, refresh, health } = useDataset();
  const current = ALL.find((i) => (i.href === "/" ? pathname === "/" : pathname.startsWith(i.href)));
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
          <Link href="/" className="brand" aria-label="AudienceIQ PK home">
            <span className="brand-mark" aria-hidden="true">AQ</span>
            <span className="brand-name">AudienceIQ PK<small>Audience &amp; campaign intelligence</small></span>
          </Link>
          <button className="btn ghost sm menu-toggle" type="button" aria-label="Close navigation" onClick={() => setOpen(false)} style={{ color: "#fff" }}>
            <X size={18} />
          </button>
        </div>
        {NAV.map((group) => (
          <div className="nav-group" key={group.label}>
            <div className="nav-label">{group.label}</div>
            {group.items.map(({ href, label, icon: Icon, ...rest }) => (
              <Link key={href} href={href} className="nav-link" aria-current={current?.href === href ? "page" : undefined} title={label}>
                <Icon size={17} aria-hidden="true" />
                <span className="nav-text">{label}</span>
                {"q" in rest && rest.q && <span className="q">{rest.q}</span>}
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
          <div className="crumbs" aria-label="Breadcrumb">
            <span>AudienceIQ</span><span aria-hidden="true">/</span>
            <strong aria-current="page">{current?.label ?? "Page"}</strong>
          </div>
          <div className="topbar-right">
            <DatasetSwitcher />
            <ThemeToggle />
          </div>
        </header>
        <main className="content" id="main" tabIndex={-1}>
          {error && !loading && (
            <Notice tone="error" title="Analysis service unavailable">
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
      <Frame>{children}</Frame>
    </DatasetProvider>
  );
}
