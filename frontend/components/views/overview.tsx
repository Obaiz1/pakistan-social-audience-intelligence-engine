"use client";

import { ArrowRight } from "lucide-react";
import Link from "next/link";
import { useApi } from "@/lib/api";
import { ACTION_LABEL, KIND_LABEL, NEED_LABEL, label, num, pct, ratio } from "@/lib/format";
import type { AnomalyFlag, ClusterProfile, Comparison, Meta, Recommendation } from "@/lib/types";
import { CIPlot, CompareTable, HBar, PLATFORM_COLOR, PlatformLabel } from "../charts";
import { useDataset } from "../dataset";
import { FilterBar, useFilters } from "../filters";
import { ChartTable, Empty, ErrorState, Kpi, LoadingPage, MethodNote, ModeBadge, Panel } from "../ui";

type Overview = {
  meta: Meta;
  kpis: Record<string, number | string | null>;
  coverage: { posts: number; overall: Record<string, number | null>; per_platform: Record<string, Record<string, number>> };
  engagement_by_platform: { platform: string; posts: number; weighted_er: number | null; formula: string }[];
  content: Comparison;
  top_clusters: ClusterProfile[];
  anomalies: AnomalyFlag[];
  anomaly_counts: { kind: string; direction: string; n: number }[];
  recommendations: Recommendation[];
  language_mix: Record<string, number>;
};

const JOURNEY = [
  { q: "Q1", href: "/content", title: "Which content attracts attention?", hint: "Compare reels, photos, influencer, styling and sale posts." },
  { q: "Q2", href: "/audience", title: "What does the audience want?", hint: "Multilingual comments grouped by meaning." },
  { q: "Q3", href: "/anomalies", title: "Which patterns are unusual?", hint: "Posts far from comparable peers, with reasons." },
  { q: "Q4", href: "/audience?view=needs", title: "Which needs should we address?", hint: "Need segments by size, language and campaign." },
  { q: "Q5", href: "/recommendations", title: "What should we do next?", hint: "Evidence-linked actions and test plans." },
];

export function OverviewView() {
  const { datasetId, dataset } = useDataset();
  const { filters } = useFilters();
  const s = useApi<Overview>(datasetId ? "/analytics/overview" : null, { dataset_id: datasetId, ...filters });
  if (!datasetId) return dataset === null ? <LoadingPage /> : <Empty title="No dataset available" />;
  if (s.loading) return <LoadingPage />;
  if (s.error || !s.data) return <ErrorState error={s.error ?? "No data"} status={s.status} onRetry={s.reload} />;
  const d = s.data;
  const k = d.kpis;
  return (
    <div className="grid">
      <section className="hero" aria-labelledby="hero-title">
        <div className="row" style={{ marginBottom: 8 }}>
          <ModeBadge mode={d.meta.mode} />
          <span className="chip">{d.meta.product_category}</span>
          <span className="chip">{k.date_min} → {k.date_max}</span>
        </div>
        <h1 id="hero-title">What does a Pakistani lawn-suit audience want, and what should the brand do next?</h1>
        <p>
          {num(Number(k.posts))} posts and {num(Number(k.comments))} multilingual comments across {k.brands} brands and {k.platforms} platforms.
          Comments are grouped by meaning with unsupervised clustering (not sentiment), unusual posts are compared with their peers,
          and every recommendation links back to its evidence. {d.meta.mode === "synthetic" && <strong>All figures here come from a synthetic classroom dataset.</strong>}
        </p>
      </section>

      <Panel title="Try this project — answer the five questions" description="A guided path for evaluators. Each step opens the view that answers one assignment question.">
        <nav className="journey" aria-label="Five-question walkthrough">
          {JOURNEY.map((j) => (
            <Link key={j.q} href={j.href}>
              <span className="qid">{j.q}</span>
              <strong>{j.title}</strong>
              <span>{j.hint}</span>
            </Link>
          ))}
        </nav>
      </Panel>

      <FilterBar />
      <MethodNote meta={d.meta} posts={Number(k.posts)} comments={Number(k.comments)} />

      <div className="grid cols-4">
        <Kpi label="Posts" value={num(Number(k.posts))} sub={`${num(Number(k.posts_mature))} mature (≥7 days)`} />
        <Kpi label="Comments analysed" value={num(Number(k.comments))} sub={`on ${num(Number(k.posts_with_comments))} posts`} />
        <Kpi label="Audience-need clusters" value={num(Number(k.clusters))} sub={`${pct(Number(k.noise_share))} unclustered`} help="Discovered without labels; named afterwards." />
        <Kpi label="Unusual posts" value={num(Number(k.posts_flagged))} sub={`${num(Number(k.anomaly_flags))} flags · ${num(Number(k.recommendations))} recommendations`} />
      </div>

      <Panel title="Data coverage" description="Share of posts where each metric is reported. Missing is shown as missing — never as zero.">
        <div className="table-wrap">
          <table className="data">
            <thead><tr><th>Platform</th><th className="n">Posts</th><th className="n">Likes</th><th className="n">Comments</th><th className="n">Shares</th><th className="n">Views</th></tr></thead>
            <tbody>
              {Object.entries(d.coverage.per_platform).map(([p, c]) => (
                <tr key={p}><td><PlatformLabel name={p} /></td><td className="n">{num(c.posts)}</td>
                  {["likes", "comments_count", "shares", "views"].map((m) => <td key={m} className="n">{pct(c[m], 0)}</td>)}</tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>

      <div className="grid cols-2">
        <Panel title="Q1 · Engagement rate by platform" description="Weighted rate = Σ interactions ÷ Σ views over mature posts that report views. Formulas differ by platform, so compare within a platform.">
          <ChartTable label="Engagement by platform" summary={d.engagement_by_platform.map((p) => `${p.platform} ${pct(p.weighted_er, 2)}`).join(", ")}
            chart={<HBar data={d.engagement_by_platform.map((p) => ({ label: p.platform, value: p.weighted_er ?? 0, n: p.posts }))} valueKey="value" fmt={(v) => pct(v, 1)} colorKey={(r) => PLATFORM_COLOR[String(r.label)]} />}
            table={<div className="table-wrap"><table className="data"><thead><tr><th>Platform</th><th className="n">Posts</th><th className="n">Weighted ER</th><th>Formula</th></tr></thead>
              <tbody>{d.engagement_by_platform.map((p) => <tr key={p.platform}><td>{p.platform}</td><td className="n">{num(p.posts)}</td><td className="n">{pct(p.weighted_er, 2)}</td><td className="faint">{p.formula}</td></tr>)}</tbody></table></div>} />
        </Panel>
        <Panel title="Q1 · Attention by content type" description={d.content.metric_help} actions={<Link className="btn sm" href="/content">Details <ArrowRight size={14} /></Link>}>
          <ChartTable label="Attention index by content type" summary={`Median attention index with 95% CI; ${num(d.content.posts_compared)} mature posts; filled = tested (n ≥ 20); * = significant after BH correction with at least a small effect.`}
            chart={<CIPlot rows={d.content.rows} />} table={<CompareTable rows={d.content.rows} />} />
        </Panel>
      </div>

      <div className="grid cols-2">
        <Panel title="Q2/Q4 · Leading audience-need clusters" description="Largest discovered clusters in this view. Share = of clustered (non-noise) comments." actions={<Link className="btn sm" href="/audience">Explore <ArrowRight size={14} /></Link>}>
          {d.top_clusters.length ? (
            <div className="stack">
              {d.top_clusters.map((c) => (
                <Link key={c.cluster_id} href={`/audience?cluster=${c.cluster_id}`} className="card-link quote" style={{ display: "grid", gap: 6 }}>
                  <div className="row" style={{ justifyContent: "space-between" }}>
                    <strong>#{c.cluster_id} {c.label}</strong>
                    <span className="num">{pct(c.filtered_share)} · {num(c.filtered_size)}</span>
                  </div>
                  <div className="meter" aria-hidden="true"><span style={{ width: `${Math.min(100, c.filtered_share * 300)}%` }} /></div>
                  <div className="faint">{c.top_terms.slice(0, 6).join(" · ")} · name agreement {pct(c.label_agreement, 0)}</div>
                </Link>
              ))}
            </div>
          ) : <Empty title="No clusters in this view" />}
        </Panel>
        <Panel title="Q3 · Unusual posts snapshot" description="Statistical outliers relative to comparable posts — not fraud or bot claims." actions={<Link className="btn sm" href="/anomalies">Investigate <ArrowRight size={14} /></Link>}>
          <div className="row" style={{ marginBottom: 10 }}>
            {d.anomaly_counts.map((a) => <span key={`${a.kind}${a.direction}`} className={`badge ${a.direction === "positive" ? "ok" : "critical"}`}>{label(KIND_LABEL, a.kind)} · {a.direction} · {a.n}</span>)}
          </div>
          <div className="stack">
            {d.anomalies.map((a) => (
              <Link key={a.flag_id} href={`/anomalies?flag=${a.flag_id}`} className="card-link quote">
                <div className="row" style={{ justifyContent: "space-between" }}><strong className="mono">{a.post_id}</strong><span className={`badge ${a.severity === "high" ? "critical" : "warn"}`}>{a.severity}</span></div>
                <div className="faint" style={{ marginTop: 4 }}>{a.reason}</div>
              </Link>
            ))}
            {!d.anomalies.length && <Empty title="No flags in this view" />}
          </div>
        </Panel>
      </div>

      <Panel title="Q5 · Priority recommendations" description="Generated deterministically from linked evidence; open a card for limitations and the test plan." actions={<Link className="btn sm" href="/recommendations">All recommendations <ArrowRight size={14} /></Link>}>
        <div className="grid cols-3">
          {d.recommendations.map((r) => (
            <Link key={r.recommendation_id} href={`/recommendations#${r.recommendation_id}`} className="card-link rec">
              <div className="row"><span className="badge accent">P{r.priority}</span><span className="badge">{label(ACTION_LABEL, r.action_type)}</span><span className="badge">{r.evidence_strength}</span></div>
              <h3>{r.title}</h3>
              <p className="why">{r.why_it_matters}</p>
              {r.audience_need && <span className="faint">Need: {label(NEED_LABEL, r.audience_need)} · n = {num(r.sample_size)}</span>}
            </Link>
          ))}
          {!d.recommendations.length && <Empty title="No recommendation passed the evidence gates" />}
        </div>
      </Panel>
      <p className="faint">Language mix of analysed comments: {Object.entries(d.language_mix).map(([l, n]) => `${l.replace("_", " ")} ${num(n)}`).join(" · ")}. Attention index median of 1.00 = a brand&apos;s typical post ({ratio(1)}).</p>
    </div>
  );
}
