"use client";

import { ArrowRight, CheckCircle2, CircleDashed } from "lucide-react";
import Link from "next/link";
import { useApi } from "@/lib/api";
import { ACTION_LABEL, CONTENT_LABEL, KIND_LABEL, label, num, pct, ratio } from "@/lib/format";
import type { AnomalyFlag, Comparison, Meta, Recommendation } from "@/lib/types";
import { CIPlot, CompareTable, HBar, PLATFORM_COLOR, PlatformLabel } from "../charts";
import { useDataset } from "../dataset";
import { FilterBar, useFilters } from "../filters";
import { NeedsDistribution, type NeedGroup } from "../needs";
import { ChartTable, Empty, ErrorState, Kpi, LoadingPage, MethodNote, ModeBadge, Panel } from "../ui";

type Overview = {
  meta: Meta;
  kpis: Record<string, number | string | null>;
  coverage: { posts: number; overall: Record<string, number | null>; per_platform: Record<string, Record<string, number>> };
  engagement_by_platform: { platform: string; posts: number; weighted_er: number | null; formula: string }[];
  content: Comparison;
  anomalies: AnomalyFlag[];
  anomaly_counts: { kind: string; direction: string; n: number }[];
  recommendations: Recommendation[];
  language_mix: Record<string, number>;
  needs: NeedGroup[];
  pipeline: { step: string; status: string; seconds: number | null }[];
  dataset_created_at: string | null;
};

/** Pipeline steps in execution order (the API returns them alphabetically). */
const STEP_ORDER = ["normalize_posts", "enrich_comments", "embed", "cluster", "anomalies", "recommendations"];
const stepRank = (step: string) => { const i = STEP_ORDER.indexOf(step); return i === -1 ? STEP_ORDER.length : i; };

export function OverviewView() {
  const { datasetId, dataset } = useDataset();
  const { filters } = useFilters();
  const s = useApi<Overview>(datasetId ? "/analytics/overview" : null, { dataset_id: datasetId, ...filters });
  if (!datasetId) return dataset === null ? <LoadingPage /> : <Empty title="No dataset available">Generate the demo or import a CSV in the Data hub.</Empty>;
  if (s.loading) return <LoadingPage />;
  if (s.error || !s.data) return <ErrorState error={s.error ?? "No data"} status={s.status} onRetry={s.reload} />;
  const d = s.data;
  const k = d.kpis;
  const comments = Number(k.comments);
  const confident = d.needs.filter((n) => !n.uncertain);
  const topNeed = confident[0];
  const best = d.content.rows.filter((r) => r.sufficient && r.significant && (r.cliffs_delta ?? 0) > 0 && r.effect !== "negligible")
    .sort((a, b) => (b.median ?? 0) - (a.median ?? 0))[0];
  const answers = [
    { q: 1, href: "/content", title: "Which content attracts attention?",
      answer: best ? `${best.label} lead: median attention ${ratio(best.median)}× a brand's typical post (n = ${best.n}).` : "No content type is reliably above its peers in this view." },
    { q: 2, href: "/audience", title: "What does the audience want?",
      answer: topNeed ? `${topNeed.label} is the largest confident need: ${pct(topNeed.comments / Math.max(comments, 1), 0)} of comments.` : "No need cluster passes the naming threshold in this view." },
    { q: 3, href: "/anomalies", title: "Which patterns are unusual?",
      answer: `${num(Number(k.posts_flagged))} posts differ sharply from comparable posts (${num(Number(k.anomaly_flags))} flags).` },
    { q: 4, href: "/segments", title: "Which needs should we address?",
      answer: `${confident.length} need segments are clearly named; ${d.needs.filter((n) => n.uncertain).length} groups stay marked uncertain.` },
    { q: 5, href: "/recommendations", title: "What should we do next?",
      answer: `${num(Number(k.recommendations))} actions passed the evidence gates, each with a test plan.` },
  ];
  return (
    <div className="grid">
      <section className="hero" aria-labelledby="hero-title">
        <div className="row" style={{ marginBottom: 10 }}>
          <ModeBadge mode={d.meta.mode} />
          <span className="chip">{d.meta.product_category}</span>
          <span className="chip">{k.date_min} → {k.date_max}</span>
          <span className="chip mono">{d.meta.dataset_id}</span>
        </div>
        <h1 id="hero-title">What does this audience want — and what should the brand do next?</h1>
        <p>
          {num(Number(k.posts))} posts and {num(comments)} comments in English, Roman Urdu and Urdu across {k.brands} brands and {k.platforms} platform{Number(k.platforms) === 1 ? "" : "s"}.
          Comments are grouped by meaning with unsupervised clustering, unusual posts are compared with their own peers, and every action links back to its evidence.
          {d.meta.mode === "synthetic" && <strong> Figures come from a synthetic classroom dataset, not real brands.</strong>}
        </p>
      </section>

      <Panel title="The five questions — answered from this dataset" description="Each answer is computed live from the selected dataset and filters. Open a card for the full evidence.">
        <nav className="journey" aria-label="Five-question walkthrough">
          {answers.map((a) => (
            <Link key={a.q} href={a.href}>
              <span className="qid">QUESTION {a.q}</span>
              <strong>{a.title}</strong>
              <span className="answer">{a.answer}</span>
            </Link>
          ))}
        </nav>
      </Panel>

      <FilterBar />
      <MethodNote meta={d.meta} posts={Number(k.posts)} comments={comments} />

      <div className="grid cols-5">
        <Kpi label="Posts" value={num(Number(k.posts))} sub={`${num(Number(k.posts_mature))} mature (≥ 7 days)`} href="/content" help="Posts in the current filter. Comparisons use only mature posts." />
        <Kpi label="Comments" value={num(comments)} sub={`on ${num(Number(k.posts_with_comments))} posts`} href="/comments" help="Retained comments in view (a platform's comment count can be higher)." />
        <Kpi label="Brands · campaigns" value={`${k.brands} · ${k.campaigns}`} sub={`${k.platforms} platform${Number(k.platforms) === 1 ? "" : "s"}`} href="/campaigns" />
        <Kpi label="Need clusters" value={num(Number(k.clusters))} sub={`${pct(Number(k.noise_share))} unclustered`} href="/audience" help="Discovered without labels; named afterwards with an agreement share." />
        <Kpi label="Unusual posts" value={num(Number(k.posts_flagged))} sub={`${num(Number(k.anomaly_flags))} flags vs peer cohorts`} href="/anomalies" />
      </div>

      <div className="grid cols-7-5">
        <Panel title="Audience needs distribution" description={`Discovered comment clusters grouped by their post-hoc need. Share = of ${num(comments)} comments in view. Striped rows are mixed or unclustered — shown, not hidden.`}
          actions={<Link className="btn sm" href="/audience">Cluster explorer <ArrowRight size={14} /></Link>}>
          {d.needs.length ? <NeedsDistribution needs={d.needs} total={comments} hrefFor={(g) => `/audience?cluster=${[...g.clusters].sort((a, b) => b.size - a.size)[0].cluster_id}`} />
            : <Empty title="No comments in this view" />}
        </Panel>
        <div className="stack">
          <Panel title="Top unusual posts" description="Statistical outliers vs comparable posts — never fraud claims." actions={<Link className="btn sm" href="/anomalies">Anomaly lab <ArrowRight size={14} /></Link>}>
            <div className="stack">
              {d.anomalies.map((a) => (
                <Link key={a.flag_id} href={`/anomalies?flag=${a.flag_id}`} className="card-link quote">
                  <div className="row" style={{ justifyContent: "space-between" }}><strong className="mono">{a.post_id}</strong>
                    <span className={`badge ${a.direction === "positive" ? "ok" : "critical"}`}>{a.direction === "positive" ? "▲ above" : "▼ below"} · {label(KIND_LABEL, a.kind)}</span></div>
                  <div className="faint" style={{ marginTop: 4 }}>{a.reason}</div>
                </Link>
              ))}
              {!d.anomalies.length && <Empty title="No flags in this view" />}
            </div>
          </Panel>
          <Panel title="Data pipeline" description={d.dataset_created_at ? `Built ${d.dataset_created_at.slice(0, 16).replace("T", " ")} UTC` : undefined}>
            <div className="pipeline" aria-label="Pipeline steps">
              {[...d.pipeline].sort((a, b) => stepRank(a.step) - stepRank(b.step)).map((p, i) => (
                <span key={p.step} className="row" style={{ gap: 6 }}>
                  <span className="step">{p.status === "ok" ? <CheckCircle2 size={13} color="var(--ok)" aria-hidden="true" /> : <CircleDashed size={13} aria-hidden="true" />}{p.step.replace(/_/g, " ")}{p.seconds !== null && <span className="faint">{p.seconds}s</span>}</span>
                  {i < d.pipeline.length - 1 && <span className="arrow" aria-hidden="true">→</span>}
                </span>
              ))}
            </div>
          </Panel>
        </div>
      </div>

      <Panel title="Top evidence-backed actions" actions={<Link className="btn sm" href="/recommendations">Action center <ArrowRight size={14} /></Link>}>
        <div className="grid cols-3">
          {d.recommendations.map((r) => (
            <Link key={r.recommendation_id} href={`/recommendations#${r.recommendation_id}`} className="card-link rec">
              <div className="row"><span className="badge accent">P{r.priority}</span><span className="badge">{label(ACTION_LABEL, r.action_type)}</span><span className="badge">{r.evidence_strength} evidence</span></div>
              <h3>{r.title}</h3>
              <p className="why">{r.why_it_matters}</p>
            </Link>
          ))}
          {!d.recommendations.length && <Empty title="No recommendation passed the evidence gates" />}
        </div>
      </Panel>

      <div className="grid cols-2">
        <Panel title="Q1 · Attention by content type" description={d.content.metric_help} actions={<Link className="btn sm" href="/content">Details <ArrowRight size={14} /></Link>}>
          {d.content.rows.length ? (
            <ChartTable label="Attention index by content type" summary={`Median attention index with 95% CI; ${num(d.content.posts_compared)} mature posts. Filled = tested (n ≥ 20); * = significant after correction with at least a small effect.`}
              chart={<CIPlot rows={d.content.rows} />} table={<CompareTable rows={d.content.rows} />} />
          ) : <Empty title="Insufficient comparable data">Not enough mature posts with comparable metrics in this view.</Empty>}
        </Panel>
        <Panel title="Engagement rate by platform" description="Weighted rate = Σ interactions ÷ Σ views (mature posts reporting views). Platforms use different formulas — compare within a platform.">
          <ChartTable label="Engagement by platform" summary={d.engagement_by_platform.map((p) => `${p.platform} ${pct(p.weighted_er, 2)}`).join(", ")}
            chart={<HBar data={d.engagement_by_platform.map((p) => ({ label: p.platform, value: p.weighted_er ?? 0, n: p.posts }))} valueKey="value" fmt={(v) => pct(v, 1)} colorKey={(r) => PLATFORM_COLOR[String(r.label)]} />}
            table={<div className="table-wrap" tabIndex={0}><table className="data"><thead><tr><th>Platform</th><th className="n">Posts</th><th className="n">Weighted ER</th><th>Formula</th></tr></thead>
              <tbody>{d.engagement_by_platform.map((p) => <tr key={p.platform}><td><PlatformLabel name={p.platform} /></td><td className="n">{num(p.posts)}</td><td className="n">{pct(p.weighted_er, 2)}</td><td className="faint">{p.formula}</td></tr>)}</tbody></table></div>} />
          <div className="table-wrap" tabIndex={0} style={{ marginTop: 12 }}>
            <table className="data"><caption className="sr-only">Metric coverage by platform</caption>
              <thead><tr><th>Coverage</th><th className="n">Likes</th><th className="n">Comments</th><th className="n">Shares</th><th className="n">Views</th></tr></thead>
              <tbody>{Object.entries(d.coverage.per_platform).map(([p, c]) => (
                <tr key={p}><td><PlatformLabel name={p} /></td>{["likes", "comments_count", "shares", "views"].map((m) => <td key={m} className="n">{c[m] === 0 ? <span className="faint">not reported</span> : pct(c[m], 0)}</td>)}</tr>))}</tbody></table>
          </div>
        </Panel>
      </div>
      <p className="faint">Languages of analysed comments: {Object.entries(d.language_mix).map(([l, n]) => `${l.replace("_", " ")} ${num(n)}`).join(" · ")}. Content labels: {Object.values(CONTENT_LABEL).slice(0, 6).join(", ")}.</p>
    </div>
  );
}
