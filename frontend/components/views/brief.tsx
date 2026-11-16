"use client";

import { FileType, Printer } from "lucide-react";
import { exportUrl, useApi } from "@/lib/api";
import { date, num, pct, ratio } from "@/lib/format";
import type { Comparison, Meta, Recommendation } from "@/lib/types";
import { useDataset } from "../dataset";
import { useFilters } from "../filters";
import type { NeedGroup } from "../needs";
import { ErrorState, LoadingPage, ModeBadge } from "../ui";

type Overview = {
  meta: Meta;
  kpis: Record<string, number | string | null>;
  content: Comparison;
  needs: NeedGroup[];
  anomalies: { flag_id: string; post_id: string; reason: string; direction: string }[];
  recommendations: Recommendation[];
};
type Recs = { recommendations: Recommendation[] };

/** Examiner-oriented executive brief: one printable page, every number from the API, limitations included. */
export function BriefView() {
  const { datasetId } = useDataset();
  const { filters } = useFilters();
  const o = useApi<Overview>(datasetId ? "/analytics/overview" : null, { dataset_id: datasetId, ...filters });
  const r = useApi<Recs>(datasetId ? "/recommendations" : null, { dataset_id: datasetId });
  if (o.loading || r.loading) return <LoadingPage label="Preparing brief" />;
  if (o.error || !o.data) return <ErrorState error={o.error ?? "No data"} status={o.status} onRetry={o.reload} />;
  const d = o.data;
  const k = d.kpis;
  const comments = Number(k.comments);
  const content = d.content.rows.filter((x) => x.sufficient).slice(0, 6);
  const recs = (r.data?.recommendations ?? []).slice(0, 6);
  const active = Object.entries(d.meta.filters ?? {});
  return (
    <article className="grid" style={{ maxWidth: 920 }} aria-labelledby="brief-title">
      <div className="row no-print" style={{ justifyContent: "flex-end" }}>
        <button className="btn primary" type="button" onClick={() => window.print()}><Printer size={15} /> Print / save as PDF</button>
        <a className="btn" href={exportUrl({ dataset_id: datasetId, ...filters, format: "pdf" })}><FileType size={15} /> Server PDF summary</a>
      </div>
      <header className="stack" style={{ gap: 6 }}>
        <span className="eyebrow">Executive brief · AudienceIQ PK</span>
        <h1 id="brief-title" className="serif" style={{ fontSize: 30, lineHeight: 1.15 }}>{d.meta.dataset_name}</h1>
        <div className="row"><ModeBadge mode={d.meta.mode} /><span className="faint">{d.meta.disclaimer}</span></div>
        <dl className="kv" style={{ marginTop: 6 }}>
          <dt>Data</dt><dd>{num(Number(k.posts))} posts · {num(comments)} comments · {k.date_min} → {k.date_max} · snapshot {date(d.meta.snapshot_at)}</dd>
          <dt>Model</dt><dd className="mono">{d.meta.run_id} · {d.meta.model_version}</dd>
          <dt>Filters</dt><dd>{active.length ? active.map(([key, v]) => `${key}: ${Array.isArray(v) ? v.join(", ") : v}`).join(" · ") : "none"}</dd>
          <dt>Generated</dt><dd>{d.meta.generated_at.replace("T", " ").slice(0, 16)} UTC</dd>
        </dl>
      </header>
      <section className="panel">
        <h2 className="section">Q1 · Which content attracts attention?</h2>
        <p className="faint" style={{ margin: "4px 0 8px" }}>Median attention index (1.00 = a brand&apos;s typical post on that platform), mature posts only.</p>
        <div className="table-wrap" tabIndex={0}><table className="data"><thead><tr><th>Content type</th><th className="n">n</th><th className="n">Median</th><th className="n">95% CI</th><th>Verdict</th></tr></thead>
          <tbody>{content.map((x) => <tr key={x.group}><td>{x.label}</td><td className="n">{x.n}</td><td className="n">{ratio(x.median)}</td><td className="n">{x.ci_low !== null ? `${ratio(x.ci_low)}–${ratio(x.ci_high)}` : "—"}</td><td>{x.significant && x.effect !== "negligible" ? `${(x.cliffs_delta ?? 0) > 0 ? "higher" : "lower"} (${x.effect})` : "no clear difference"}</td></tr>)}</tbody></table></div>
      </section>
      <section className="panel">
        <h2 className="section">Q2 · What does the audience want?</h2>
        <div className="table-wrap" tabIndex={0} style={{ marginTop: 8 }}><table className="data"><thead><tr><th>Discovered need</th><th className="n">Comments</th><th className="n">Share</th><th>Note</th></tr></thead>
          <tbody>{d.needs.map((n) => <tr key={n.need}><td>{n.label}</td><td className="n">{num(n.comments)}</td><td className="n">{pct(n.comments / Math.max(comments, 1), 1)}</td><td className="faint">{n.uncertain ? "uncertain (mixed or unclustered)" : `${n.clusters.length} cluster${n.clusters.length > 1 ? "s" : ""}`}</td></tr>)}</tbody></table></div>
      </section>
      <section className="panel">
        <h2 className="section">Q3 · Which patterns are unusual?</h2>
        <p style={{ margin: "6px 0" }}>{num(Number(k.posts_flagged))} posts ({num(Number(k.anomaly_flags))} flags) differ sharply from comparable posts. Top examples:</p>
        <ul style={{ margin: 0, paddingLeft: 18 }}>{d.anomalies.map((a) => <li key={a.flag_id} className="muted" style={{ marginBottom: 4 }}><span className="mono">{a.post_id}</span> — {a.reason}</li>)}</ul>
      </section>
      <section className="panel">
        <h2 className="section">Q4 &amp; Q5 · Needs to address and next actions</h2>
        <ol style={{ margin: "8px 0 0", paddingLeft: 20 }}>{recs.map((x) => (
          <li key={x.recommendation_id} style={{ marginBottom: 8 }}><strong>{x.title}</strong> <span className="faint">(P{x.priority}, {x.evidence_strength} evidence, n = {num(x.sample_size)})</span>
            <div className="muted">{x.why_it_matters}</div><div className="faint">Test: {x.test_plan}</div></li>
        ))}</ol>
      </section>
      <section className="panel flat">
        <h2 className="section">Limitations</h2>
        <ul style={{ margin: "6px 0 0", paddingLeft: 18 }} className="muted">
          <li>{d.meta.mode === "synthetic" ? "Synthetic classroom data: demonstrates the method, not findings about real brands." : d.meta.mode === "observed" ? "Observed YouTube data only; viewer location unknown; comment text withheld." : "Imported data as attested by the uploader."}</li>
          <li>All comparisons are associational; campaigns, budgets and seasons are confounded.</li>
          <li>Cluster names come from a keyword reference labeller applied after unsupervised discovery; agreement shares are shown.</li>
          <li>Anomalies are statistical outliers relative to comparable posts — not evidence of fraud, bots or paid activity.</li>
        </ul>
      </section>
    </article>
  );
}
