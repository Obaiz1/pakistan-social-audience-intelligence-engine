"use client";

import { ArrowRight, Info } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { useApi } from "@/lib/api";
import { ACTION_LABEL, CONTENT_LABEL, LANGUAGE_LABEL, NEED_LABEL, compact, label, num, pct, ratio } from "@/lib/format";
import type { ClusterProfile, CommentRow, Meta, NeedsBy, PageInfo, Recommendation } from "@/lib/types";
import { HBar, LANGUAGE_COLOR, NeedHeat, PlatformLabel, SERIES, StackRows, Trend, languageKeys } from "../charts";
import { useDataset } from "../dataset";
import { FilterBar, useFilters } from "../filters";
import { NeedsDistribution, type NeedGroup } from "../needs";
import { QuestionStepper } from "../story";
import { Bidi, ChartTable, Empty, ErrorState, Kpi, LoadingPage, MethodNote, Notice, PageHead, Pager, Panel, TextCell } from "../ui";
import { PostDrawer } from "./content";

type ClustersResp = {
  meta: Meta;
  run: { run_id: string; embedding: string; embedding_model: string; algorithm: string; params: Record<string, number | string>; n_comments: number; n_clusters: number; noise_rate: number; quality: Record<string, number | null>; model_version: string; created_at: string };
  comments_in_view: number;
  clusters: ClusterProfile[];
  needs_by_campaign: NeedsBy[];
  needs_by_platform: NeedsBy[];
};
type Breakdown = { value: string; label: string; n: number; share: number; lift: number | null };
type LinkedPost = { post_id: string; cluster_comments: number; brand: string; platform: string; campaign: string; content_type: string; likes: number | null; comments_count: number | null; views: number | null; attention_index: number | null; source_url: string | null };
type DetailResp = {
  meta: Meta;
  cluster: ClusterProfile;
  breakdowns: Record<string, Breakdown[]>;
  monthly: Record<string, number>;
  engagement_context: { posts_with_cluster_comments: number; median_attention_index_posts_with_cluster: number | null; median_attention_index_all_commented_posts: number | null };
  comments: (CommentRow & { gloss: string | null })[];
  page: PageInfo;
  comments_note: string | null;
  gloss_note: string | null;
  linked_posts: LinkedPost[];
  recommendations: Recommendation[];
};

function groupNeeds(clusters: ClusterProfile[]): NeedGroup[] {
  const m = new Map<string, NeedGroup>();
  for (const c of clusters) {
    const key = c.cluster_id === -1 ? "noise" : c.need_category;
    const g = m.get(key) ?? { need: key, label: key === "noise" ? "Unclustered (noise)" : key === "mixed" ? "Mixed / uncertain" : c.need_label, comments: 0, share: 0, uncertain: key === "mixed" || key === "noise", clusters: [] };
    g.comments += c.filtered_size;
    g.clusters.push({ cluster_id: c.cluster_id, label: c.label, size: c.filtered_size, agreement: c.label_agreement });
    m.set(key, g);
  }
  return [...m.values()].sort((a, b) => Number(a.need === "noise") - Number(b.need === "noise") || b.comments - a.comments);
}

function BreakdownTable({ rows, title }: { rows: Breakdown[]; title: string }) {
  return (
    <div className="table-wrap" tabIndex={0}>
      <table className="data">
        <caption className="sr-only">{title}</caption>
        <thead><tr><th>{title}</th><th className="n">Comments</th><th className="n">Share</th><th className="n">Lift</th></tr></thead>
        <tbody>{rows.slice(0, 6).map((r) => (
          <tr key={r.value}><td>{r.label}</td><td className="n">{num(r.n)}</td><td className="n">{pct(r.share, 0)}</td>
            <td className="n" style={{ fontWeight: (r.lift ?? 0) >= 1.5 ? 700 : 400, color: (r.lift ?? 0) >= 1.5 ? "var(--accent)" : undefined }}>{r.lift === null ? "—" : `${r.lift.toFixed(2)}×`}</td></tr>
        ))}</tbody>
      </table>
    </div>
  );
}

function ClusterDetail({ id }: { id: number }) {
  const { datasetId } = useDataset();
  const { filters, get, setParam } = useFilters();
  const [post, setPost] = useState<string | null>(null);
  const page = Number(get("cpage") ?? 1);
  const language = get("clang");
  const s = useApi<DetailResp>(datasetId ? `/audience/clusters/${id}` : null, { dataset_id: datasetId, ...filters, page, page_size: 8, language });
  if (s.loading) return <div className="skeleton" style={{ height: 520 }} />;
  if (s.error || !s.data) return <ErrorState error={s.error ?? "No data"} status={s.status} onRetry={s.reload} />;
  const d = s.data;
  const c = d.cluster;
  const monthly = Object.entries(d.monthly).map(([month, n]) => ({ month, n }));
  const uncertain = c.need_category === "mixed" || c.need_category === "other" || c.label_agreement < 0.5;
  return (
    <Panel id="cluster-detail" title={<span className="serif" style={{ fontSize: 22 }}>#{c.cluster_id} · {c.label}</span>} description={c.explanation}
      actions={<Link className="btn sm" href={`/comments?cluster_id=${c.cluster_id}`}>All comments <ArrowRight size={14} /></Link>}>
      <nav className="pipeline" aria-label="Evidence trail" style={{ marginBottom: 14 }}>
        <a className="step" href="#trail-why">1 · Why it exists</a><span className="arrow" aria-hidden="true">→</span>
        <a className="step" href="#trail-comments">2 · Original comments</a><span className="arrow" aria-hidden="true">→</span>
        <a className="step" href="#trail-posts">3 · Linked posts</a><span className="arrow" aria-hidden="true">→</span>
        <a className="step" href="#trail-actions">4 · Recommended action</a>
      </nav>
      {uncertain && <Notice tone="warn" title="Uncertain cluster">{c.need_category === "other" || c.need_category === "mixed"
        ? "This is a catch-all group: its comments do not share one specific, actionable need, so it is not treated as a confident need anywhere in the app. Read the comments below before acting."
        : <>Only {pct(c.label_agreement, 0)} of members carry the reference label used to name it. Treat the name as a hint; read the comments below before acting.</>}</Notice>}
      <div className="grid cols-4" style={{ marginTop: 12 }}>
        <Kpi label="Comments (view)" value={num(c.filtered_size)} sub={`${pct(c.filtered_share)} of clustered comments`} />
        <Kpi label="Name agreement" value={pct(c.label_agreement, 0)} sub="members with this reference label" help="Share of members whose rule-based reference label matches the cluster name. Low = name is uncertain." />
        <Kpi label="Cohesion" value={ratio(c.cohesion)} sub="mean cosine similarity to the centre" />
        <Kpi label="Posts reached" value={num(d.engagement_context.posts_with_cluster_comments)} sub={`median attention ${ratio(d.engagement_context.median_attention_index_posts_with_cluster)} vs ${ratio(d.engagement_context.median_attention_index_all_commented_posts)}`} />
      </div>
      <div className="grid cols-2" style={{ marginTop: 16 }} id="trail-why">
        <div className="stack">
          <h3 className="section">1 · Why this group exists</h3>
          <div>{c.top_terms.map((t) => <span key={t} className="term"><Bidi text={t} /></span>)}</div>
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
          <BreakdownTable rows={d.breakdowns.language_type ?? []} title="Language" />
          <p className="faint">Lift = this cluster&apos;s share in a group ÷ the group&apos;s share of all comments in view (≥ 1.5× in bold).</p>
          {monthly.length > 1 && <><h3 className="section">Monthly volume</h3><Trend data={monthly} /></>}
        </div>
      </div>
      <div className="stack" style={{ marginTop: 18 }} id="trail-comments">
        <div className="row" style={{ justifyContent: "space-between" }}>
          <h3 className="section">2 · Original comments (closest to the centre first)</h3>
          <label className="field" style={{ minWidth: 170 }}>Language
            <select className="select" value={language ?? ""} onChange={(e) => setParam("clang", e.target.value || null)}>
              <option value="">All languages</option>
              {["english", "roman_urdu", "urdu", "mixed", "other"].map((l) => <option key={l} value={l}>{label(LANGUAGE_LABEL, l)}</option>)}
            </select>
          </label>
        </div>
        {d.comments_note && <Notice tone="warn" title="No permission to show comment text">{d.comments_note}</Notice>}
        {d.gloss_note && <p className="faint"><Info size={12} aria-hidden="true" /> {d.gloss_note}</p>}
        {d.comments.length ? (
          <div className="table-wrap" tabIndex={0}><table className="data"><thead><tr><th>Comment</th><th>Language</th><th>Reference topic</th><th>Post</th><th className="n">Distance</th></tr></thead>
            <tbody>{d.comments.map((cm) => (
              <tr key={cm.comment_id}>
                <td style={{ maxWidth: 420 }}><TextCell text={cm.comment_text} />{cm.gloss && <div className="gloss">gloss used for embedding: {cm.gloss}</div>}</td>
                <td>{label(LANGUAGE_LABEL, cm.language_type)}</td><td>{label(NEED_LABEL, cm.topic)}</td>
                <td><button type="button" className="link mono" onClick={() => setPost(cm.post_id)}>{cm.post_id}</button><div className="faint">{cm.campaign}</div></td>
                <td className="n">{ratio(cm.distance ?? null, 3)}</td>
              </tr>))}</tbody></table></div>
        ) : <Empty title="No comments for this language in the cluster" />}
        <Pager page={d.page.page} pages={d.page.pages} total={d.page.total} onPage={(n) => setParam("cpage", String(n))} />
      </div>
      <div className="stack" style={{ marginTop: 18 }} id="trail-posts">
        <h3 className="section">3 · Posts where this need is concentrated</h3>
        <div className="table-wrap" tabIndex={0}><table className="data"><thead><tr><th>Post</th><th>Platform</th><th>Type · campaign</th><th className="n">Comments in cluster</th><th className="n">Likes</th><th className="n">Views</th><th className="n">Attention</th></tr></thead>
          <tbody>{d.linked_posts.map((p) => (
            <tr key={p.post_id}><td><button type="button" className="link mono" onClick={() => setPost(p.post_id)}>{p.post_id}</button><div className="faint">{p.brand}</div></td>
              <td><PlatformLabel name={p.platform} /></td><td>{label(CONTENT_LABEL, p.content_type)}<div className="faint">{p.campaign}</div></td>
              <td className="n">{p.cluster_comments}</td><td className="n">{compact(p.likes)}</td><td className="n">{compact(p.views)}</td><td className="n">{ratio(p.attention_index)}</td></tr>
          ))}</tbody></table></div>
      </div>
      <div className="stack" style={{ marginTop: 18 }} id="trail-actions">
        <h3 className="section">4 · Recommended action</h3>
        {d.recommendations.length ? d.recommendations.map((r) => (
          <Link key={r.recommendation_id} className="card-link quote" href={`/recommendations#${r.recommendation_id}`}><strong>{r.title}</strong><div className="faint">{label(ACTION_LABEL, r.action_type)} · {r.evidence_strength} evidence · n = {num(r.sample_size)}</div></Link>
        )) : <p className="muted">No action is linked: this cluster&apos;s evidence did not pass the gates (agreement, size, significance) or the need is not actionable. That is a deliberate outcome, not a missing feature.</p>}
      </div>
      <PostDrawer postId={post} onClose={() => setPost(null)} />
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
      <QuestionStepper current={2} />
      <PageHead eyebrow="Question 2 · Audience needs" title="What does the audience want?">
        Comments in English, Roman Urdu and Urdu are embedded with a multilingual sentence model and grouped by meaning, without labels. Groups are named afterwards, and every name shows how many members agree with it.
      </PageHead>
      <FilterBar />
      {s.loading && <LoadingPage />}
      {s.error && <ErrorState error={s.error} status={s.status} onRetry={s.reload} />}
      {s.data && (() => {
        const d = s.data;
        const real = d.clusters.filter((c) => c.cluster_id !== -1);
        const mixed = real.filter((c) => c.need_category === "mixed" || c.label_agreement < 0.5);
        const needs = groupNeeds(d.clusters);
        const topNeeds = Array.from(new Set(real.filter((c) => c.need_category !== "mixed").map((c) => c.need_category))).slice(0, 8);
        return (
          <>
            <MethodNote meta={d.meta} comments={d.comments_in_view} />
            {d.comments_in_view < 30 && <Notice tone="warn" title="Low sample size">Only {d.comments_in_view} comments in this view; patterns are anecdotal.</Notice>}
            <div className="grid cols-7-5">
              <Panel title="Needs discovered in the comments" description="Select a need to open its cluster: why it exists, original comments, linked posts and the recommended action.">
                <NeedsDistribution needs={needs} total={d.comments_in_view} onSelect={(id) => setParam("cluster", String(id))} />
              </Panel>
              <Panel title="Model & uncertainty" description="What produced these groups, and how much to trust them.">
                <dl className="kv">
                  <dt>Model</dt><dd>{d.run.algorithm === "kmeans" ? `KMeans, k = ${d.run.params.k}` : "HDBSCAN"} on {d.run.embedding} embeddings</dd>
                  <dt>Encoder</dt><dd className="mono">{d.run.embedding_model.split(" (")[0]}</dd>
                  <dt>Silhouette</dt><dd className="num">{ratio(d.run.quality.silhouette_cosine, 3)} <span className="faint">(cosine, −1…1)</span></dd>
                  <dt>Stability</dt><dd className="num">{ratio(d.run.quality.stability_ari, 3)} <span className="faint">(ARI across re-fits)</span></dd>
                  <dt>Unclustered</dt><dd>{pct(d.run.noise_rate)}</dd>
                  <dt>Uncertain clusters</dt><dd>{mixed.length ? `${mixed.length} of ${real.length} (name agreement < 50 % or mixed)` : "none"}</dd>
                  <dt>Run</dt><dd className="mono">{d.run.run_id} · {d.run.model_version}</dd>
                </dl>
                <p className="faint" style={{ marginTop: 10 }}>Roman-Urdu comments are glossed to English before embedding (ADR-013). Earlier, delivery, discount and availability were merged into “Mixed” clusters; the evidence and the audit metric are in the <Link href="/model">Model lab</Link>.</p>
              </Panel>
            </div>
            {selected !== null && <ClusterDetail id={Number(selected)} />}
            <div className="grid cols-2">
              <Panel title="Cluster size" description="Share of clustered comments in view (denominator: non-noise comments).">
                <ChartTable label="Cluster sizes" summary={real.slice(0, 6).map((c) => `#${c.cluster_id} ${c.label} ${pct(c.filtered_share)}`).join("; ")}
                  chart={<HBar data={real.map((c) => ({ label: `#${c.cluster_id} ${c.label}`.slice(0, 34), value: c.filtered_share, n: c.filtered_size }))} valueKey="value" fmt={(v) => pct(v, 1)} colorKey={(_, i) => SERIES[i % SERIES.length]} />}
                  table={<div className="table-wrap" tabIndex={0}><table className="data"><thead><tr><th>Cluster</th><th className="n">Comments</th><th className="n">Share</th><th className="n">Agreement</th></tr></thead>
                    <tbody>{real.map((c) => <tr key={c.cluster_id}><td><button type="button" className="link" onClick={() => setParam("cluster", String(c.cluster_id))}>#{c.cluster_id} {c.label}</button></td><td className="n">{num(c.filtered_size)}</td><td className="n">{pct(c.filtered_share)}</td><td className="n">{pct(c.label_agreement, 0)}</td></tr>)}</tbody></table></div>} />
              </Panel>
              <Panel title="Language composition per cluster" description="A cluster dominated by one language may be held together partly by language rather than need; its explanation says so.">
                <StackRows keys={languageKeys} colors={LANGUAGE_COLOR} labels={LANGUAGE_LABEL} rows={real.slice(0, 12).map((c) => ({ id: c.cluster_id, label: `#${c.cluster_id} ${c.label}`, parts: c.language_mix }))} />
              </Panel>
            </div>
            <Panel title="All discovered clusters" description="Every cluster from the selected run, including uncertain ones.">
              {real.length ? (
                <div className="grid cols-3">
                  {real.map((c) => (
                    <button key={c.cluster_id} type="button" className="cluster-card" aria-pressed={selected === String(c.cluster_id)} onClick={() => setParam("cluster", String(c.cluster_id))}>
                      <div className="row" style={{ justifyContent: "space-between" }}>
                        <span className="ct">#{c.cluster_id} {c.label}</span>
                        <span className={`badge ${c.need_category === "mixed" || c.label_agreement < 0.5 ? "warn" : "accent"}`}>{pct(c.label_agreement, 0)} agree</span>
                      </div>
                      <div className="meter" aria-hidden="true"><span style={{ width: `${Math.min(100, c.filtered_share * 250)}%` }} /></div>
                      <span className="faint num">{num(c.filtered_size)} comments · {pct(c.filtered_share)}</span>
                      <span className="faint">{c.top_terms.slice(0, 6).map((t, i) => <span key={t}>{i > 0 && " · "}<Bidi text={t} /></span>)}</span>
                    </button>
                  ))}
                </div>
              ) : <Empty title="No clusters in this view" />}
            </Panel>
            <Panel title="Needs by campaign" description="Share of each discovered need within a campaign's clustered comments; ▲ = at least 1.5× the overall share. Campaigns with fewer than 30 comments are not compared.">
              <NeedHeat rows={d.needs_by_campaign} dim="campaign" needs={topNeeds} caption="Discovered needs by campaign" />
            </Panel>
            <p className="faint">Run {d.run.run_id} · {num(d.run.n_comments)} comments clustered · created {d.run.created_at?.slice(0, 10)}.</p>
          </>
        );
      })()}
    </div>
  );
}
