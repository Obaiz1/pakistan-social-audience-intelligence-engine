"use client";

import { Bar, BarChart, CartesianGrid, Cell, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { LANGUAGE_LABEL, NEED_LABEL, heatAlpha, label, num, pct, ratio } from "@/lib/format";
import type { CompareRow, NeedsBy } from "@/lib/types";

export const SERIES = ["var(--c1)", "var(--c2)", "var(--c3)", "var(--c4)", "var(--c5)", "var(--c6)", "var(--c7)", "var(--c8)", "var(--c9)", "var(--c10)"];
export const PLATFORM_COLOR: Record<string, string> = {
  Instagram: "var(--p-instagram)", TikTok: "var(--p-tiktok)", Facebook: "var(--p-facebook)", YouTube: "var(--p-youtube)", Other: "var(--p-other)",
};
const PLATFORM_SHAPE: Record<string, string> = { Instagram: "diamond", TikTok: "triangle", Facebook: "circle", YouTube: "square", Other: "circle" };
export const LANGUAGE_COLOR: Record<string, string> = {
  english: "var(--c1)", roman_urdu: "var(--c3)", urdu: "var(--c2)", mixed: "var(--c6)", other: "var(--c9)", unknown: "var(--c9)",
};

/** Platform marker: colour + shape, so meaning never depends on colour alone (WCAG 1.4.1; Repo B pattern). */
export function Marker({ platform, size = 10 }: { platform: string; size?: number }) {
  const c = PLATFORM_COLOR[platform] ?? "var(--text-3)";
  const s = PLATFORM_SHAPE[platform] ?? "circle";
  return (
    <svg width={size} height={size} viewBox="0 0 10 10" aria-hidden="true" style={{ flex: "none" }}>
      {s === "circle" && <circle cx="5" cy="5" r="4.5" fill={c} />}
      {s === "square" && <rect x="0.5" y="0.5" width="9" height="9" fill={c} />}
      {s === "diamond" && <path d="M5 0 10 5 5 10 0 5Z" fill={c} />}
      {s === "triangle" && <path d="M5 0.5 9.8 9.5H0.2Z" fill={c} />}
    </svg>
  );
}

export function PlatformLabel({ name }: { name: string }) {
  return <span className="row" style={{ gap: 7, display: "inline-flex", flexWrap: "nowrap" }}><Marker platform={name} />{name}</span>;
}

function Tip({ active, payload, fmt }: { active?: boolean; payload?: { name?: string; value?: number; payload?: Record<string, unknown> }[]; fmt?: (v: number) => string }) {
  if (!active || !payload?.length) return null;
  const p = payload[0];
  const row = p.payload ?? {};
  return (
    <div className="tip">
      <strong>{String(row.label ?? row.name ?? p.name ?? "")}</strong>
      <div className="num">{fmt ? fmt(Number(p.value)) : String(p.value)}{row.n !== undefined ? ` · n = ${num(Number(row.n))}` : ""}</div>
    </div>
  );
}

/** Median with 95% bootstrap CI per group; reference line at 1.00 (= typical post). Insufficient groups shown hollow. */
export function CIPlot({ rows, reference = 1, fmt = (v: number) => ratio(v) }: { rows: CompareRow[]; reference?: number | null; fmt?: (v: number) => string }) {
  const data = rows.filter((r) => r.median !== null);
  if (!data.length) return <p className="faint">No groups with data.</p>;
  const values = data.flatMap((r) => [r.ci_low ?? r.median ?? 0, r.ci_high ?? r.median ?? 0, r.median ?? 0]);
  if (reference !== null) values.push(reference);
  const lo = Math.min(...values) * 0.9;
  const hi = Math.max(...values) * 1.08;
  const W = 640, rowH = 34, left = 170, right = 90, top = 18;
  const H = top + data.length * rowH + 22;
  const x = (v: number) => left + ((v - lo) / (hi - lo || 1)) * (W - left - right);
  const ticks = Array.from({ length: 5 }, (_, i) => lo + ((hi - lo) * i) / 4);
  return (
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" style={{ maxWidth: "100%", height: "auto" }} aria-hidden="true">
      {ticks.map((t) => (
        <g key={t}>
          <line x1={x(t)} x2={x(t)} y1={top - 6} y2={H - 20} stroke="var(--line)" strokeDasharray="2 4" />
          <text x={x(t)} y={H - 6} textAnchor="middle" fontSize="11" fill="var(--text-3)">{fmt(t)}</text>
        </g>
      ))}
      {reference !== null && <line x1={x(reference)} x2={x(reference)} y1={top - 8} y2={H - 20} stroke="var(--text-3)" strokeWidth="1.5" />}
      {data.map((r, i) => {
        const y = top + i * rowH + rowH / 2;
        const sig = r.significant && r.effect && r.effect !== "negligible";
        const color = !r.sufficient ? "var(--text-3)" : sig ? ((r.cliffs_delta ?? 0) > 0 ? "var(--accent)" : "var(--critical)") : "var(--c1)";
        return (
          <g key={r.group}>
            <text x={left - 10} y={y + 4} textAnchor="end" fontSize="12.5" fill="var(--text)">{r.label}</text>
            {r.ci_low !== null && r.ci_high !== null && <line x1={x(r.ci_low)} x2={x(r.ci_high)} y1={y} y2={y} stroke={color} strokeWidth="3" strokeLinecap="round" opacity="0.55" />}
            <circle cx={x(r.median ?? 0)} cy={y} r="6" fill={r.sufficient ? color : "var(--card)"} stroke={color} strokeWidth="2" />
            <text x={W - right + 8} y={y + 4} fontSize="11.5" fill="var(--text-2)">{fmt(r.median ?? 0)} · n={r.n}{sig ? " *" : ""}</text>
          </g>
        );
      })}
    </svg>
  );
}

export function CompareTable({ rows, fmt = (v: number | null) => ratio(v) }: { rows: CompareRow[]; fmt?: (v: number | null) => string }) {
  return (
    <div className="table-wrap" tabIndex={0}>
      <table className="data">
        <thead><tr><th>Group</th><th className="n">n (mature)</th><th className="n">Median</th><th className="n">95% CI</th><th className="n">Rest median</th><th className="n">Cliff&apos;s δ</th><th className="n">BH p</th><th>Verdict</th></tr></thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.group}>
              <td>{r.label}</td>
              <td className="n">{num(r.n)}</td>
              <td className="n">{fmt(r.median)}</td>
              <td className="n">{r.ci_low !== null ? `${fmt(r.ci_low)}–${fmt(r.ci_high)}` : "not computed"}</td>
              <td className="n">{fmt(r.rest_median)}</td>
              <td className="n">{r.cliffs_delta !== null ? r.cliffs_delta.toFixed(2) : "—"}</td>
              <td className="n">{r.p_adj !== null ? (r.p_adj < 0.001 ? "<0.001" : r.p_adj.toFixed(3)) : "—"}</td>
              <td>{!r.sufficient ? <span className="badge">n &lt; 20 · not tested</span> : r.significant ? <span className={`badge ${r.effect === "negligible" ? "" : (r.cliffs_delta ?? 0) > 0 ? "ok" : "critical"}`}>{(r.cliffs_delta ?? 0) > 0 ? "higher" : "lower"} · {r.effect}</span> : <span className="badge">no clear difference</span>}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function HBar({ data, valueKey, labelKey = "label", fmt = (v: number) => num(v), colorKey, height }: {
  data: Record<string, unknown>[]; valueKey: string; labelKey?: string; fmt?: (v: number) => string; colorKey?: (row: Record<string, unknown>, i: number) => string; height?: number;
}) {
  const h = height ?? Math.max(160, data.length * 30 + 30);
  return (
    <div className="chart-box" style={{ height: h }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} layout="vertical" margin={{ top: 4, right: 40, bottom: 4, left: 8 }}>
          <CartesianGrid horizontal={false} stroke="var(--line)" strokeDasharray="2 4" />
          <XAxis type="number" tickFormatter={(v) => fmt(Number(v))} stroke="var(--text-3)" fontSize={11} />
          <YAxis type="category" dataKey={labelKey} width={170} stroke="var(--text-3)" fontSize={11.5} tick={{ fill: "var(--text-2)" }} interval={0} />
          <Tooltip cursor={{ fill: "var(--accent-soft)" }} content={<Tip fmt={fmt} />} />
          <Bar dataKey={valueKey} radius={[0, 5, 5, 0]} isAnimationActive={false}>
            {data.map((row, i) => <Cell key={i} fill={colorKey ? colorKey(row, i) : SERIES[i % SERIES.length]} />)}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function Histogram({ data, fmtX, highlight, height = 200 }: { data: { from: number; to: number; n: number }[]; fmtX: (v: number) => string; highlight?: (b: { from: number; to: number }) => boolean; height?: number }) {
  const rows = data.map((b) => ({ ...b, label: `${fmtX(b.from)} to ${fmtX(b.to)}`, mid: fmtX((b.from + b.to) / 2) }));
  return (
    <div className="chart-box" style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={rows} margin={{ top: 6, right: 8, bottom: 4, left: 0 }}>
          <CartesianGrid vertical={false} stroke="var(--line)" strokeDasharray="2 4" />
          <XAxis dataKey="mid" stroke="var(--text-3)" fontSize={10.5} interval="preserveStartEnd" />
          <YAxis stroke="var(--text-3)" fontSize={11} allowDecimals={false} width={36} />
          <Tooltip cursor={{ fill: "var(--accent-soft)" }} content={<Tip fmt={(v) => `${num(v)} posts`} />} />
          <Bar dataKey="n" isAnimationActive={false}>
            {rows.map((b, i) => <Cell key={i} fill={highlight?.(b) ? "var(--critical)" : "var(--c1)"} />)}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function Trend({ data, height = 140 }: { data: { month: string; n: number }[]; height?: number }) {
  return (
    <div className="chart-box" style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 6, right: 10, bottom: 0, left: 0 }}>
          <CartesianGrid vertical={false} stroke="var(--line)" strokeDasharray="2 4" />
          <XAxis dataKey="month" stroke="var(--text-3)" fontSize={10.5} />
          <YAxis stroke="var(--text-3)" fontSize={11} allowDecimals={false} width={34} />
          <Tooltip content={<Tip fmt={(v) => `${num(v)} comments`} />} />
          <Line type="monotone" dataKey="n" stroke="var(--accent)" strokeWidth={2} dot={{ r: 2.5 }} isAnimationActive={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

/** One stacked share bar per row (e.g. language mix per cluster). */
export function StackRows({ rows, keys, colors, labels }: { rows: { id: string | number; label: string; parts: Record<string, number> }[]; keys: string[]; colors: Record<string, string>; labels: Record<string, string> }) {
  return (
    <div className="stack">
      <div className="legend" aria-hidden="true">{keys.map((k) => <span key={k}><i style={{ background: colors[k] }} />{labels[k] ?? k}</span>)}</div>
      {rows.map((r) => {
        const total = Object.values(r.parts).reduce((a, b) => a + b, 0) || 1;
        return (
          <div key={r.id} className="stack" style={{ gap: 4 }}>
            <div className="row" style={{ justifyContent: "space-between" }}><span style={{ fontSize: 13 }}>{r.label}</span><span className="faint num">{num(total)}</span></div>
            <div className="stackbar" role="img" aria-label={`${r.label}: ${keys.filter((k) => r.parts[k]).map((k) => `${labels[k] ?? k} ${pct((r.parts[k] ?? 0) / total, 0)}`).join(", ")}`}>
              {keys.map((k) => (r.parts[k] ? <span key={k} style={{ width: `${(100 * r.parts[k]) / total}%`, background: colors[k] }} title={`${labels[k] ?? k}: ${pct(r.parts[k] / total, 0)}`} /> : null))}
            </div>
          </div>
        );
      })}
    </div>
  );
}

/** Distribution boxes (P10–P90 whiskers, P25–P75 box, median tick). */
export function BoxRows({ rows, fmt = (v: number) => ratio(v), reference = 1 }: { rows: { group: string; label: string; n: number; p10: number | null; p25: number | null; p50: number | null; p75: number | null; p90: number | null }[]; fmt?: (v: number) => string; reference?: number | null }) {
  const data = rows.filter((r) => r.p50 !== null);
  if (!data.length) return <p className="faint">No data.</p>;
  const lo = Math.min(...data.map((r) => r.p10 ?? 0)) * 0.9;
  const hi = Math.max(...data.map((r) => r.p90 ?? 0)) * 1.05;
  const W = 640, rowH = 30, left = 170, right = 70, top = 10;
  const H = top + data.length * rowH + 22;
  const x = (v: number) => left + ((v - lo) / (hi - lo || 1)) * (W - left - right);
  return (
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" style={{ height: "auto" }} aria-hidden="true">
      {reference !== null && reference >= lo && reference <= hi && <line x1={x(reference)} x2={x(reference)} y1={top} y2={H - 20} stroke="var(--text-3)" />}
      {[lo, (lo + hi) / 2, hi].map((t) => <text key={t} x={x(t)} y={H - 6} textAnchor="middle" fontSize="11" fill="var(--text-3)">{fmt(t)}</text>)}
      {data.map((r, i) => {
        const y = top + i * rowH + rowH / 2;
        return (
          <g key={r.group}>
            <text x={left - 10} y={y + 4} textAnchor="end" fontSize="12.5" fill="var(--text)">{r.label}</text>
            <line x1={x(r.p10 ?? 0)} x2={x(r.p90 ?? 0)} y1={y} y2={y} stroke="var(--text-3)" />
            <rect x={x(r.p25 ?? 0)} y={y - 8} width={Math.max(2, x(r.p75 ?? 0) - x(r.p25 ?? 0))} height="16" rx="4" fill="var(--accent-soft)" stroke="var(--accent)" />
            <line x1={x(r.p50 ?? 0)} x2={x(r.p50 ?? 0)} y1={y - 9} y2={y + 9} stroke="var(--accent)" strokeWidth="2.5" />
            <text x={W - right + 8} y={y + 4} fontSize="11.5" fill="var(--text-2)">n={r.n}</text>
          </g>
        );
      })}
    </svg>
  );
}

/** Need × group heat table: share with lift vs overall; insufficient groups marked. Accessible by construction. */
export function NeedHeat({ rows, dim, needs, caption }: { rows: NeedsBy[]; dim: "campaign" | "platform"; needs: string[]; caption: string }) {
  return (
    <div className="table-wrap" tabIndex={0}>
      <table className="data">
        <caption className="sr-only">{caption}</caption>
        <thead><tr><th>{dim === "campaign" ? "Campaign" : "Platform"}</th><th className="n">Comments</th>{needs.map((n) => <th key={n} className="n">{label(NEED_LABEL, n)}</th>)}</tr></thead>
        <tbody>
          {rows.map((r) => {
            const by = Object.fromEntries(r.needs.map((x) => [x.need, x]));
            return (
              <tr key={String(r[dim])}>
                <td>{String(r[dim])}</td>
                <td className="n">{num(r.comments)}</td>
                {needs.map((n) => {
                  const cell = by[n];
                  if (!r.sufficient) return <td key={n} className="heat-cell faint">n&lt;30</td>;
                  if (!cell) return <td key={n} className="heat-cell faint">0%</td>;
                  const alpha = heatAlpha(cell.share);
                  const strong = cell.lift >= 1.5;
                  return (
                    <td key={n} className="heat-cell" style={{ background: `rgba(var(--heat), ${alpha})`, fontWeight: strong ? 800 : 500 }} title={`${pct(cell.share)} of comments; ${cell.lift.toFixed(2)}× the overall share`}>
                      {pct(cell.share, 0)}{strong ? ` ▲${cell.lift.toFixed(1)}×` : ""}
                    </td>
                  );
                })}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

export const languageKeys = ["english", "roman_urdu", "urdu", "mixed", "other", "unknown"];
export { LANGUAGE_LABEL };
