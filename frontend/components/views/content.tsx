"use client";

import { Download, ExternalLink } from "lucide-react";
import { useState } from "react";
import { exportUrl, useApi } from "@/lib/api";
import { CONTENT_LABEL, KIND_LABEL, LANGUAGE_LABEL, NEED_LABEL, compact, date, label, num, pct, ratio } from "@/lib/format";
import type { AnomalyFlag, CommentRow, Comparison, Meta, PageInfo, Post } from "@/lib/types";
import { BoxRows, CIPlot, CompareTable, PlatformLabel } from "../charts";
import { useDataset } from "../dataset";
import { FilterBar, useFilters } from "../filters";
import { QuestionStepper } from "../story";
import { useToast } from "../toast";
import { ChartTable, Drawer, Empty, ErrorState, LoadingPage, LowSample, MethodNote, PageHead, Pager, Panel, TextCell } from "../ui";

type ContentResp = {
  meta: Meta;
  formulas: Record<string, string>;
  by_content_type: Comparison;
  by_content_type_er: Comparison;
  by_platform: Comparison;
  distribution: { group: string; label: string; n: number; p10: number | null; p25: number | null; p50: number | null; p75: number | null; p90: number | null }[];
  platform_matrix: { platform: string; content_type: string; label: string; n: number; sufficient: boolean; median_attention_index: number | null; median_er_views: number | null; weighted_er: number | null; views_reported_share: number }[];
  top_bottom: { metric: string; top: Post[]; bottom: Post[] };
  notes: string[];
};
type PostsResp = { meta: Meta; page: PageInfo; rows: Post[] };
type PostDetail = { meta: Meta; post: Post; comments: CommentRow[]; comments_note: string | null; flags: AnomalyFlag[]; need_mix: Record<string, number> };

const SORTS = [
  { value: "attention_index", label: "Attention index" }, { value: "er_views", label: "Engagement rate" }, { value: "likes", label: "Likes" },
  { value: "comments_count", label: "Comments" }, { value: "views", label: "Views" }, { value: "published_at", label: "Newest" },
];

export function PostDrawer({ postId, onClose }: { postId: string | null; onClose: () => void }) {
  const { datasetId } = useDataset();
  const s = useApi<PostDetail>(postId && datasetId ? `/posts/${encodeURIComponent(postId)}` : null, { dataset_id: datasetId });
  const p = s.data?.post;
  return (
    <Drawer open={!!postId} onClose={onClose} title={postId ?? ""} subtitle={p ? `${p.brand} · ${p.platform} · ${label(CONTENT_LABEL, p.content_type)} · ${p.campaign}` : undefined}>
      {s.loading && <LoadingPage label="Loading post" />}
      {s.error && <ErrorState error={s.error} status={s.status} />}
      {p && (
        <>
          <dl className="kv">
            <dt>Published</dt><dd>{date(p.published_at)} ({p.days_since_post} days before snapshot{p.mature ? "" : " — immature"})</dd>
            <dt>Likes · comments</dt><dd className="num">{num(p.likes)} · {num(p.comments_count)}</dd>
            <dt>Shares · views</dt><dd className="num">{num(p.shares)} · {num(p.views)}</dd>
            <dt>Engagement rate</dt><dd className="num">{pct(p.er_views, 2)} <span className="faint">{p.er_formula}</span></dd>
            <dt>Attention index</dt><dd className="num">{ratio(p.attention_index)} <span className="faint">(1.00 = brand&apos;s typical {p.platform} post)</span></dd>
            <dt>Source</dt><dd>{p.observed_vs_synthetic} · {p.source_type}{p.source_url && <> · <a href={p.source_url} target="_blank" rel="noreferrer noopener">open source <ExternalLink size={12} /></a></>}</dd>
          </dl>
          {s.data!.flags.length > 0 && (
            <Panel flat title="Anomaly flags on this post">
              <div className="stack">{s.data!.flags.map((f) => <div key={f.flag_id} className="quote"><strong>{label(KIND_LABEL, f.kind)} · {f.direction}</strong><div className="faint">{f.reason}</div></div>)}</div>
            </Panel>
          )}
          <Panel flat title={`Retained comments (${s.data!.comments.length})`} description={s.data!.comments_note ?? "Cluster = discovered group; topic = rule-based reference label."}>
            {s.data!.comments.length ? (
              <div className="table-wrap" tabIndex={0}><table className="data"><thead><tr><th>Comment</th><th>Language</th><th>Cluster</th></tr></thead>
                <tbody>{s.data!.comments.slice(0, 40).map((c) => <tr key={c.comment_id}><td><TextCell text={c.comment_text} /></td><td>{label(LANGUAGE_LABEL, c.language_type)}</td><td>{c.cluster_label ?? "—"}</td></tr>)}</tbody></table></div>
            ) : <Empty title="No retained comments" />}
            {Object.keys(s.data!.need_mix).length > 0 && <p className="faint" style={{ marginTop: 8 }}>Need mix: {Object.entries(s.data!.need_mix).map(([n, c]) => `${label(NEED_LABEL, n)} ${c}`).join(" · ")}</p>}
          </Panel>
        </>
      )}
    </Drawer>
  );
}

function PostTable({ onOpen }: { onOpen: (id: string) => void }) {
  const { datasetId } = useDataset();
  const toast = useToast();
  const { filters, get, setParam } = useFilters();
  const sort = get("sort") ?? "attention_index";
  const page = Number(get("page") ?? 1);
  const s = useApi<PostsResp>(datasetId ? "/posts" : null, { dataset_id: datasetId, ...filters, sort, order: sort === "published_at" ? "desc" : "desc", page, page_size: 15 });
  return (
    <Panel title="Post explorer" description="Every post in the current filter. Open a post for its metrics, comments and any anomaly flags."
      actions={<>
        <label className="field" style={{ minWidth: 170 }}>Sort by<select className="select" value={sort} onChange={(e) => setParam("sort", e.target.value)}>{SORTS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}</select></label>
        <a className="btn sm" style={{ alignSelf: "flex-end" }} href={exportUrl({ dataset_id: datasetId, ...filters, format: "csv", section: "posts" })} onClick={() => toast(`Downloading ${s.data ? s.data.page.total.toLocaleString("en-PK") : ""} filtered posts as CSV`)}><Download size={14} /> Filtered CSV</a>
      </>}>
      {s.error && <ErrorState error={s.error} status={s.status} onRetry={s.reload} />}
      {s.loading && <div className="skeleton" style={{ height: 300 }} />}
      {s.data && (
        <div className="stack">
          <div className="table-wrap" tabIndex={0}>
            <table className="data">
              <thead><tr><th>Post</th><th>Platform</th><th>Type</th><th>Campaign</th><th className="n">Likes</th><th className="n">Comments</th><th className="n">Shares</th><th className="n">Views</th><th className="n">ER</th><th className="n">Attention</th><th className="n">Age (d)</th></tr></thead>
              <tbody>
                {s.data.rows.map((p) => (
                  <tr key={p.post_id}>
                    <td><button className="link mono" type="button" onClick={() => onOpen(p.post_id)}>{p.post_id}</button>{p.flagged && <span className="badge warn" style={{ marginLeft: 6 }}>flagged</span>}<div className="faint">{p.brand}</div></td>
                    <td><PlatformLabel name={p.platform} /></td><td>{label(CONTENT_LABEL, p.content_type)}</td><td>{p.campaign}</td>
                    <td className="n">{compact(p.likes)}</td><td className="n">{compact(p.comments_count)}</td><td className="n">{compact(p.shares)}</td><td className="n">{compact(p.views)}</td>
                    <td className="n">{pct(p.er_views, 2)}</td><td className="n">{ratio(p.attention_index)}</td><td className="n">{p.days_since_post}{!p.mature && <span title="Immature: excluded from comparisons"> *</span>}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <Pager page={s.data.page.page} pages={s.data.page.pages} total={s.data.page.total} onPage={(n) => setParam("page", String(n))} />
          <p className="faint">N/A = the platform or export does not report that metric. * = younger than 7 days (excluded from comparisons).</p>
        </div>
      )}
    </Panel>
  );
}

export function ContentView() {
  const { datasetId } = useDataset();
  const { filters } = useFilters();
  const [open, setOpen] = useState<string | null>(null);
  const s = useApi<ContentResp>(datasetId ? "/analytics/content" : null, { dataset_id: datasetId, ...filters });
  return (
    <div className="grid">
      <QuestionStepper current={1} />
      <PageHead eyebrow="Question 1 · Attention" title="Which content attracts attention?">
        Compare reels, product photos, influencer posts, styling videos and sale announcements using each platform&apos;s own metrics. The attention index compares every post with its brand&apos;s typical post on the same platform, so formats can be compared fairly.
      </PageHead>
      <FilterBar />
      {s.loading && <LoadingPage />}
      {s.error && <ErrorState error={s.error} status={s.status} onRetry={s.reload} />}
      {s.data && (
        <>
          <MethodNote meta={s.data.meta} posts={s.data.meta.sample_size} extra={<span className="chip">{num(s.data.by_content_type.posts_excluded_immature)} immature posts excluded</span>} />
          <LowSample n={s.data.by_content_type.posts_compared} />
          <div className="grid cols-2">
            <Panel title="Attention index by content type" description={s.data.by_content_type.metric_help}>
              <ChartTable label="Attention index by content type" summary={`Median with 95% bootstrap CI. Kruskal–Wallis p = ${s.data.by_content_type.kruskal_p === null ? "n/a" : s.data.by_content_type.kruskal_p < 0.001 ? "< 0.001" : s.data.by_content_type.kruskal_p.toFixed(3)}. Hollow = fewer than 20 posts (not tested).`}
                chart={<CIPlot rows={s.data.by_content_type.rows} />} table={<CompareTable rows={s.data.by_content_type.rows} />} />
            </Panel>
            <Panel title="Engagement rate index (view-based posts only)" description={s.data.by_content_type_er.metric_help + " Photos are excluded because they report no views."}>
              <ChartTable label="Engagement-rate index by content type" summary={`${num(s.data.by_content_type_er.posts_compared)} mature posts with views.`}
                chart={<CIPlot rows={s.data.by_content_type_er.rows} />} table={<CompareTable rows={s.data.by_content_type_er.rows} />} />
            </Panel>
          </div>
          <div className="grid cols-2">
            <Panel title="Distribution of attention index" description="P10–P90 whiskers, P25–P75 box, median line. The vertical line marks 1.00 (typical post).">
              <ChartTable label="Attention index distribution" summary={s.data.distribution.map((d) => `${d.label} median ${ratio(d.p50)}`).join(", ")}
                chart={<BoxRows rows={s.data.distribution} />}
                table={<div className="table-wrap" tabIndex={0}><table className="data"><thead><tr><th>Type</th><th className="n">n</th><th className="n">P10</th><th className="n">P25</th><th className="n">Median</th><th className="n">P75</th><th className="n">P90</th></tr></thead>
                  <tbody>{s.data.distribution.map((d) => <tr key={d.group}><td>{d.label}</td><td className="n">{d.n}</td>{[d.p10, d.p25, d.p50, d.p75, d.p90].map((v, i) => <td key={i} className="n">{ratio(v)}</td>)}</tr>)}</tbody></table></div>} />
            </Panel>
            <Panel title="Engagement rate by platform" description="Each platform uses its own formula; do not rank platforms against each other on this alone.">
              <CompareTable rows={s.data.by_platform.rows} fmt={(v) => pct(v, 2)} />
              <ul className="faint" style={{ marginTop: 10, paddingLeft: 18 }}>{Object.entries(s.data.formulas).map(([p, f]) => <li key={p}><strong>{p}</strong>: {f}</li>)}</ul>
            </Panel>
          </div>
          <Panel title="Platform × content type" description="Median attention index and weighted engagement rate per cell (mature posts). Cells with fewer than 20 posts are shown but flagged.">
            <div className="table-wrap" tabIndex={0}><table className="data"><thead><tr><th>Platform</th><th>Content type</th><th className="n">Posts</th><th className="n">Median attention</th><th className="n">Median ER</th><th className="n">Weighted ER</th><th className="n">Views reported</th></tr></thead>
              <tbody>{s.data.platform_matrix.map((r) => (
                <tr key={`${r.platform}${r.content_type}`}><td><PlatformLabel name={r.platform} /></td><td>{r.label}{!r.sufficient && <span className="badge" style={{ marginLeft: 6 }}>n&lt;20</span>}</td><td className="n">{r.n}</td><td className="n">{ratio(r.median_attention_index)}</td><td className="n">{pct(r.median_er_views, 2)}</td><td className="n">{pct(r.weighted_er, 2)}</td><td className="n">{pct(r.views_reported_share, 0)}</td></tr>
              ))}</tbody></table></div>
          </Panel>
          <div className="grid cols-2">
            {(["top", "bottom"] as const).map((which) => (
              <Panel key={which} title={which === "top" ? "Highest attention (mature posts)" : "Lowest attention (mature posts)"} description="Relative to each post's own brand × platform baseline.">
                <div className="stack">{s.data!.top_bottom[which].map((p) => (
                  <button key={p.post_id} type="button" className="cluster-card" onClick={() => setOpen(p.post_id)}>
                    <div className="row" style={{ justifyContent: "space-between" }}><strong className="mono">{p.post_id}</strong><span className="num">{ratio(p.attention_index)}×</span></div>
                    <span className="faint">{p.brand} · {p.platform} · {label(CONTENT_LABEL, p.content_type)} · {p.campaign}</span>
                  </button>
                ))}</div>
              </Panel>
            ))}
          </div>
          <ul className="faint" style={{ paddingLeft: 18 }}>{s.data.notes.map((n) => <li key={n}>{n}</li>)}</ul>
        </>
      )}
      <PostTable onOpen={setOpen} />
      <PostDrawer postId={open} onClose={() => setOpen(null)} />
    </div>
  );
}
