"use client";

import { ArrowRight } from "lucide-react";
import Link from "next/link";
import { useApi } from "@/lib/api";
import { ACTION_LABEL, LANGUAGE_LABEL, NEED_LABEL, label, num, pct, ratio } from "@/lib/format";
import type { ClusterProfile, CommentRow, Meta, NeedsBy, PageInfo, Recommendation } from "@/lib/types";
import { HBar, LANGUAGE_COLOR, NeedHeat, SERIES, StackRows, Trend, languageKeys } from "../charts";
import { useDataset } from "../dataset";
import { FilterBar, useFilters } from "../filters";
import { ChartTable, Empty, ErrorState, Kpi, LoadingPage, MethodNote, Notice, PageHead, Pager, Panel, TextCell } from "../ui";

type ClustersResp = {
  meta: Meta;
  run: { run_id: string; embedding: string; embedding_model: string; algorithm: string; params: Record<string, number | string>; n_comments: number; n_clusters: number; noise_rate: number; quality: Record<string, number | null>; model_version: string; created_at: string };
  comments_in_view: number;
  clusters: ClusterProfile[];
  needs_by_campaign: NeedsBy[];
  needs_by_platform: NeedsBy[];
};
type Breakdown = { value: string; label: string; n: number; share: number; lift: number | null };
type DetailResp = {
  meta: Meta;
  cluster: ClusterProfile;
  breakdowns: Record<string, Breakdown[]>;
  monthly: Record<string, number>;
  engagement_context: { posts_with_cluster_comments: number; median_attention_index_posts_with_cluster: number | null; median_attention_index_all_commented_posts: number | null };
  comments: CommentRow[];
  page: PageInfo;
  comments_note: string | null;
  recommendations: Recommendation[];
};

function BreakdownTable({ rows, title }: { rows: Breakdown[]; title: string }) {
  return (
    <div className="table-wrap">
      <table className="data">
        <caption className="sr-only">{title}</caption>
        <thead><tr><th>{title}</th><th className="n">Comments</th><th className="n">Share</th><th className="n">Lift</th></tr></thead>
        <tbody>{rows.slice(0, 8).map((r) => (
          <tr key={r.value}><td>{r.label}</td><td className="n">{num(r.n)}</td><td className="n">{pct(r.share, 0)}</td>
            <td className="n" style={{ fontWeight: (r.lift ?? 0) >= 1.5 ? 800 : 500, color: (r.lift ?? 0) >= 1.5 ? "var(--accent)" : undefined }}>{r.lift === null ? "—" : `${r.lift.toFixed(2)}×`}</td></tr>
        ))}</tbody>
      </table>
    </div>
  );
}

function ClusterDetail({ id }: { id: number }) {
  const { datasetId } = useDataset();
  const { filters, get, setParam } = useFilters();
  const page = Number(get("cpage") ?? 1);
  const s = useApi<DetailResp>(datasetId ? `/audience/clusters/${id}` : null, { dataset_id: datasetId, ...filters, page, page_size: 10 });
  if (s.loading) return <div className="skeleton" style={{ height: 420 }} />;
  if (s.error || !s.data) return <ErrorState error={s.error ?? "No data"} status={s.status} onRetry={s.reload} />;
  const d = s.data;
  const c = d.cluster;
  const monthly = Object.entries(d.monthly).map(([month, n]) => ({ month, n }));
  return (
    <Panel id="cluster-detail" title={`#${c.cluster_id} · ${c.label}`} description={c.explanation}
      actions={<Link className="btn sm" href={`/comments?cluster_id=${c.cluster_id}`}>All comments <ArrowRight size={14} /></Link>}>
      <div className="grid cols-4">
        <Kpi label="Comments (view)" value={num(c.filtered_size)} sub={`${pct(c.filtered_share)} of clustered comments`} />
        <Kpi label="Name agreement" value={pct(c.label_agreement, 0)} sub="members with this reference label" help="Share of members whose rule-based reference label matches the cluster name. Low = treat the name with caution." />
        <Kpi label="Cohesion" value={ratio(c.cohesion)} sub="mean cosine to centre" />
        <Kpi label="Posts with this need" value={num(d.engagement_context.posts_with_cluster_comments)} sub={`median attention ${ratio(d.engagement_context.median_attention_index_posts_with_cluster)} vs ${ratio(d.engagement_context.median_attention_index_all_commented_posts)}`} />
      </div>
      <div className="grid cols-2" style={{ marginTop: 14 }}>
        <div className="stack">
          <h3 className="section">Why this group exists</h3>
          <div>{c.top_terms.map((t) => <span key={t} className="term bidi">{t}</span>)}</div>
          <div className="stack">
            {c.exemplars.map((e) => (
              <div key={e.comment_id} className="quote">
                <TextCell text={e.text} withheld={e.text === null} />
                <div className="faint">{label(LANGUAGE_LABEL, e.language_type)}{e.similarity !== null && ` · similarity ${e.similarity.toFixed(2)}`}{d.meta.mode === "synthetic" && " · synthetic, illustrative"}</div>
              </div>
            ))}
          </div>
          <p className="faint">Reference-label mix inside the cluster: {Object.entries(c.need_mix).slice(0, 5).map(([n, v]) => `${label(NEED_LABEL, n)} ${v}`).join(" · ")}</p>
        </div>
        <div className="stack">
          <h3 className="section">Where it shows up</h3>
          <BreakdownTable rows={d.breakdowns.campaign ?? []} title="Campaign" />
          <BreakdownTable rows={d.breakdowns.platform ?? []} title="Platform" />
          <BreakdownTable rows={d.breakdowns.language_type ?? []} title="Language" />
          <p className="faint">Lift = share of this cluster&apos;s comments in a group ÷ that group&apos;s share of all comments in view (≥1.5× in bold).</p>
        </div>
      </div>
      <div className="grid cols-2" style={{ marginTop: 14 }}>
        <div className="stack"><h3 className="section">Monthly volume</h3>{monthly.length > 1 ? <Trend data={monthly} /> : <p className="faint">Not enough dated comments.</p>}</div>
        <div className="stack">
          <h3 className="section">Linked recommendations</h3>
          {d.recommendations.length ? d.recommendations.map((r) => (
            <Link key={r.recommendation_id} className="card-link quote" href={`/recommendations#${r.recommendation_id}`}><strong>{r.title}</strong><div className="faint">{label(ACTION_LABEL, r.action_type)} · {r.evidence_strength} · n = {num(r.sample_size)}</div></Link>
          )) : <p className="faint">No recommendation is linked to this cluster (its evidence did not pass the gates, or the need is not actionable).</p>}
        </div>
      </div>
      <div className="stack" style={{ marginTop: 14 }}>
        <h3 className="section">Member comments (closest to the centre first)</h3>
        {d.comments_note && <Notice tone="warn">{d.comments_note}</Notice>}
        <div className="table-wrap"><table className="data"><thead><tr><th>Comment</th><th>Language</th><th>Reference topic</th><th>Campaign</th><th className="n">Distance</th></tr></thead>
          <tbody>{d.comments.map((cm) => <tr key={cm.comment_id}><td><TextCell text={cm.comment_text} /></td><td>{label(LANGUAGE_LABEL, cm.language_type)}</td><td>{label(NEED_LABEL, cm.topic)}</td><td>{cm.campaign}</td><td className="n">{ratio(cm.distance ?? null, 3)}</td></tr>)}</tbody></table></div>
        <Pager page={d.page.page} pages={d.page.pages} total={d.page.total} onPage={(n) => setParam("cpage", String(n))} />
      </div>
    </Panel>
  );
}

export function AudienceView() {
  const { datasetId } = useDataset();
  const { filters, get, setParam } = useFilters();
  const s = useApi<ClustersResp>(datasetId ? "/audience/clusters" : null, { dataset_id: datasetId, ...filters });
  const selected = get("cluster");
  return (
    <div className="grid">
      <PageHead eyebrow="Q2 · Q4 · Audience needs" title="What does the audience want — and which needs should the brand address?">
        Comments in English, Roman Urdu and Urdu are embedded with a multilingual sentence model and grouped by meaning using unsupervised clustering. Groups are named afterwards and every name shows how many members agree with it.
      </PageHead>
      <FilterBar />
      {s.loading && <LoadingPage />}
      {s.error && <ErrorState error={s.error} status={s.status} onRetry={s.reload} />}
      {s.data && (() => {
        const d = s.data;
        const real = d.clusters.filter((c) => c.cluster_id !== -1);
        const noise = d.clusters.find((c) => c.cluster_id === -1);
        const topNeeds = Array.from(new Set(real.filter((c) => c.need_category !== "mixed").map((c) => c.need_category))).slice(0, 8);
        return (
          <>
            <MethodNote meta={d.meta} comments={d.comments_in_view} />
            <div className="grid cols-4">
              <Kpi label="Model" value={d.run.algorithm === "kmeans" ? `KMeans k=${d.run.params.k}` : `HDBSCAN`} sub={`${d.run.embedding} · ${d.run.embedding_model.split(" (")[0].split("/").pop()}`} />
              <Kpi label="Silhouette (cosine)" value={ratio(d.run.quality.silhouette_cosine, 3)} sub="internal separation (−1…1)" help="Computed on a fixed 5,000-comment sample. High values on synthetic text do not prove real-world validity." />
              <Kpi label="Stability (ARI)" value={ratio(d.run.quality.stability_ari, 3)} sub="agreement across re-fits" />
              <Kpi label="Unclustered" value={pct(d.run.noise_rate)} sub={noise ? `${num(noise.filtered_size)} comments kept as noise` : "every comment assigned"} />
            </div>
            {d.comments_in_view < 30 && <Notice tone="warn" title="Low sample size">Only {d.comments_in_view} comments in this view.</Notice>}
            <div className="grid cols-2">
              <Panel title="Cluster size" description="Share of clustered comments in the current view (denominator: non-noise comments).">
                <ChartTable label="Cluster sizes" summary={real.slice(0, 6).map((c) => `#${c.cluster_id} ${c.label} ${pct(c.filtered_share)}`).join("; ")}
                  chart={<HBar data={real.map((c) => ({ label: `#${c.cluster_id} ${c.label}`.slice(0, 34), value: c.filtered_share, n: c.filtered_size }))} valueKey="value" fmt={(v) => pct(v, 1)} colorKey={(_, i) => SERIES[i % SERIES.length]} />}
                  table={<div className="table-wrap"><table className="data"><thead><tr><th>Cluster</th><th className="n">Comments</th><th className="n">Share</th><th className="n">Agreement</th></tr></thead>
                    <tbody>{real.map((c) => <tr key={c.cluster_id}><td>#{c.cluster_id} {c.label}</td><td className="n">{num(c.filtered_size)}</td><td className="n">{pct(c.filtered_share)}</td><td className="n">{pct(c.label_agreement, 0)}</td></tr>)}</tbody></table></div>} />
              </Panel>
              <Panel title="Language composition per cluster" description="A cluster dominated by one language may be held together partly by language rather than need — the explanation says so when it happens.">
                <StackRows keys={languageKeys} colors={LANGUAGE_COLOR} labels={LANGUAGE_LABEL}
                  rows={real.slice(0, 14).map((c) => ({ id: c.cluster_id, label: `#${c.cluster_id} ${c.label}`, parts: c.language_mix }))} />
              </Panel>
            </div>
            <Panel title="Discovered clusters" description="Select a cluster to see why it exists, where it appears, its exemplars and linked actions.">
              {real.length ? (
                <div className="grid cols-3">
                  {real.map((c) => (
                    <button key={c.cluster_id} type="button" className="cluster-card" aria-pressed={selected === String(c.cluster_id)} onClick={() => setParam("cluster", String(c.cluster_id))}>
                      <div className="row" style={{ justifyContent: "space-between" }}>
                        <strong>#{c.cluster_id} {c.label}</strong>
                        <span className={`badge ${c.need_category === "mixed" ? "warn" : "accent"}`}>{pct(c.label_agreement, 0)} agree</span>
                      </div>
                      <div className="meter" aria-hidden="true"><span style={{ width: `${Math.min(100, c.filtered_share * 300)}%` }} /></div>
                      <span className="faint num">{num(c.filtered_size)} comments · {pct(c.filtered_share)}</span>
                      <span className="faint bidi">{c.top_terms.slice(0, 6).join(" · ")}</span>
                    </button>
                  ))}
                </div>
              ) : <Empty title="No clusters in this view" />}
            </Panel>
            {selected !== null && <ClusterDetail id={Number(selected)} />}
            <Panel title="Q4 · Needs by campaign" description="Share of each discovered need within a campaign's clustered comments; ▲ marks needs at least 1.5× more common than overall. Campaigns with fewer than 30 comments are not compared.">
              <NeedHeat rows={d.needs_by_campaign} dim="campaign" needs={topNeeds} caption="Discovered needs by campaign" />
            </Panel>
            <Panel title="Needs by platform" description="Cross-platform view; platforms differ in audience and in how comments are collected.">
              <NeedHeat rows={d.needs_by_platform} dim="platform" needs={topNeeds} caption="Discovered needs by platform" />
            </Panel>
            <p className="faint">Run {d.run.run_id} · {d.run.model_version} · {num(d.run.n_comments)} comments clustered · created {d.run.created_at?.slice(0, 10)}. See Methodology for the candidate comparison and audit.</p>
          </>
        );
      })()}
    </div>
  );
}
