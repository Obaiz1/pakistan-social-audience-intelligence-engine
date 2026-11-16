"use client";

import { ExternalLink } from "lucide-react";
import { useApi } from "@/lib/api";
import { CONTENT_LABEL, KIND_LABEL, NEED_LABEL, date, label, metricValue, num, pct, ratio } from "@/lib/format";
import type { AnomalyFlag, Meta, PageInfo, Post } from "@/lib/types";
import { Histogram, PlatformLabel } from "../charts";
import { useDataset } from "../dataset";
import { FilterBar, useFilters } from "../filters";
import { ChartTable, Drawer, Empty, ErrorState, Kpi, LoadingPage, MethodNote, Notice, PageHead, Pager, Panel, Segmented } from "../ui";

type ListResp = {
  meta: Meta;
  run: { run_id: string; method: string; params: Record<string, unknown>; metrics: Record<string, unknown> };
  summary: { flags: number; posts: number; by_kind: Record<string, number>; by_direction: Record<string, number>; by_severity: Record<string, number>; posts_scored: number };
  z_histogram: { from: number; to: number; n: number }[];
  page: PageInfo;
  rows: AnomalyFlag[];
};
type DetailResp = {
  meta: Meta;
  flag: AnomalyFlag;
  post: Post | null;
  all_flags_for_post: AnomalyFlag[];
  cohort: { key: string; size: number; quantiles: Record<string, number | null>; histogram_log: { from: number; to: number; n: number }[] };
  need_mix_post: Record<string, number>;
  need_mix_cohort: Record<string, number>;
};

function FlagDrawer({ id, onClose }: { id: string | null; onClose: () => void }) {
  const { datasetId } = useDataset();
  const s = useApi<DetailResp>(id && datasetId ? `/anomalies/${encodeURIComponent(id)}` : null, { dataset_id: datasetId });
  const d = s.data;
  return (
    <Drawer open={!!id} onClose={onClose} title={d ? `${label(KIND_LABEL, d.flag.kind)} · ${d.flag.post_id}` : "Anomaly"} subtitle={d?.post ? `${d.post.brand} · ${d.post.platform} · ${label(CONTENT_LABEL, d.post.content_type)} · ${d.post.campaign}` : undefined}>
      {s.loading && <LoadingPage label="Loading anomaly" />}
      {s.error && <ErrorState error={s.error} status={s.status} />}
      {d && (
        <>
          <Notice tone={d.flag.direction === "positive" ? "ok" : "warn"} title={`${d.flag.direction === "positive" ? "Above" : "Below"} comparable posts · severity ${d.flag.severity}`}>{d.flag.reason}</Notice>
          <dl className="kv">
            <dt>Metric</dt><dd>{d.flag.metric}</dd>
            <dt>Value</dt><dd className="num">{metricValue(d.flag.metric, d.flag.value)}</dd>
            <dt>Cohort median</dt><dd className="num">{metricValue(d.flag.metric, d.flag.baseline_median)}</dd>
            <dt>Typical range</dt><dd className="num">{d.flag.expected_low !== null ? `${metricValue(d.flag.metric, d.flag.expected_low)} – ${metricValue(d.flag.metric, d.flag.expected_high)} (P5–P95)` : "n/a"}</dd>
            <dt>Score</dt><dd className="num">{ratio(d.flag.score, 2)} {d.flag.kind === "need_mix" ? "(−log10 adjusted p)" : d.flag.kind === "multivariate" ? "(Isolation Forest)" : "(robust z)"}</dd>
            <dt>Isolation Forest</dt><dd className="num">{ratio(d.flag.iforest_score, 3)}</dd>
            <dt>Peer cohort</dt><dd>{d.cohort.key} · {d.cohort.size} mature posts ({d.flag.cohort_level.replace(/_/g, " ")})</dd>
          </dl>
          {d.cohort.histogram_log.length > 0 && (
            <Panel flat title="Where this post sits in its cohort" description="Distribution of the cohort's metric (log-spaced bins); the bin containing this post is highlighted.">
              <Histogram data={d.cohort.histogram_log} fmtX={(v) => metricValue(d.flag.kind === "engagement" ? d.flag.metric : "er_views", v)}
                highlight={(b) => d.flag.kind === "engagement" && d.flag.value !== null && d.flag.value >= b.from && d.flag.value <= b.to} height={180} />
            </Panel>
          )}
          {Object.keys(d.need_mix_post).length > 0 && (
            <Panel flat title="Comment needs: this post vs its cohort">
              <div className="table-wrap"><table className="data"><thead><tr><th>Need</th><th className="n">This post</th><th className="n">Cohort share</th></tr></thead>
                <tbody>{Object.entries(d.need_mix_post).map(([n, c]) => <tr key={n}><td>{label(NEED_LABEL, n)}</td><td className="n">{c}</td><td className="n">{pct(d.need_mix_cohort[n] ?? 0, 0)}</td></tr>)}</tbody></table></div>
            </Panel>
          )}
          {d.post && (
            <dl className="kv">
              <dt>Published</dt><dd>{date(d.post.published_at)} ({d.post.days_since_post} days)</dd>
              <dt>Likes · comments · shares · views</dt><dd className="num">{num(d.post.likes)} · {num(d.post.comments_count)} · {num(d.post.shares)} · {num(d.post.views)}</dd>
              {d.post.source_url && <><dt>Source</dt><dd><a href={d.post.source_url} target="_blank" rel="noreferrer noopener">Open original <ExternalLink size={12} /></a></dd></>}
            </dl>
          )}
          <p className="faint">{d.flag.caveat}</p>
        </>
      )}
    </Drawer>
  );
}

export function AnomaliesView() {
  const { datasetId } = useDataset();
  const { filters, get, setParam } = useFilters();
  const kind = get("kind") ?? "";
  const direction = get("direction") ?? "";
  const s = useApi<ListResp>(datasetId ? "/anomalies" : null, { dataset_id: datasetId, ...filters, kind, direction, severity: get("severity"), page: Number(get("page") ?? 1), page_size: 25 });
  const flagId = get("flag");
  return (
    <div className="grid">
      <PageHead eyebrow="Q3 · Unusual patterns" title="Which marketing patterns are unusual?">
        Each post is compared with comparable posts (same brand, platform and content type when there are at least 20; otherwise a broader peer group). Flags are statistical outliers for investigation — never accusations of fraud or bot activity.
      </PageHead>
      <FilterBar />
      <div className="row">
        <Segmented label="Anomaly kind" value={kind as string} onChange={(v) => setParam("kind", v || null)}
          options={[{ value: "", label: "All kinds" }, { value: "engagement", label: "Engagement" }, { value: "comment_pattern", label: "Comment pattern" }, { value: "need_mix", label: "Need mix" }, { value: "multivariate", label: "Multivariate" }]} />
        <Segmented label="Direction" value={direction as string} onChange={(v) => setParam("direction", v || null)}
          options={[{ value: "", label: "Both directions" }, { value: "positive", label: "Above peers" }, { value: "negative", label: "Below peers" }]} />
      </div>
      {s.loading && <LoadingPage />}
      {s.error && <ErrorState error={s.error} status={s.status} onRetry={s.reload} />}
      {s.data && (
        <>
          <MethodNote meta={s.data.meta} posts={s.data.summary.posts_scored} extra={<span className="chip">{String(s.data.run.method)}</span>} />
          <div className="grid cols-4">
            <Kpi label="Posts scored" value={num(s.data.summary.posts_scored)} sub="mature posts with a peer cohort ≥ 20" />
            <Kpi label="Flags" value={num(s.data.summary.flags)} sub={`${num(s.data.summary.posts)} posts`} />
            <Kpi label="Above / below peers" value={`${num(s.data.summary.by_direction.positive ?? 0)} / ${num(s.data.summary.by_direction.negative ?? 0)}`} />
            <Kpi label="High severity" value={num(s.data.summary.by_severity.high ?? 0)} sub="|z| ≥ 5 or p < 0.001" />
          </div>
          <Panel title="Robust z-score distribution (engagement)" description="Every scored post's engagement relative to its peer cohort; bars beyond ±3.5 contain flagged posts.">
            <ChartTable label="Robust z distribution" summary={`${num(s.data.summary.posts_scored)} scored posts; threshold |z| ≥ 3.5.`}
              chart={<Histogram data={s.data.z_histogram} fmtX={(v) => v.toFixed(1)} highlight={(b) => b.to <= -3.5 || b.from >= 3.5} />}
              table={<div className="table-wrap"><table className="data"><thead><tr><th>z from</th><th>z to</th><th className="n">Posts</th></tr></thead><tbody>{s.data.z_histogram.filter((b) => b.n).map((b) => <tr key={b.from}><td>{b.from}</td><td>{b.to}</td><td className="n">{b.n}</td></tr>)}</tbody></table></div>} />
          </Panel>
          <Panel title="Flagged posts" description="Open a flag for the comparator cohort, expected range, score and caveat.">
            {s.data.rows.length ? (
              <div className="stack">
                <div className="table-wrap"><table className="data">
                  <thead><tr><th>Post</th><th>Kind</th><th>Direction</th><th>Platform</th><th>Type · campaign</th><th className="n">Value</th><th className="n">Cohort median</th><th className="n">Score</th><th className="n">Cohort n</th></tr></thead>
                  <tbody>{s.data.rows.map((f) => (
                    <tr key={f.flag_id}>
                      <td><button className="link mono" type="button" onClick={() => setParam("flag", f.flag_id)}>{f.post_id}</button><div><span className={`badge ${f.severity === "high" ? "critical" : "warn"}`}>{f.severity}</span></div></td>
                      <td>{label(KIND_LABEL, f.kind)}</td>
                      <td><span className={`badge ${f.direction === "positive" ? "ok" : "critical"}`}>{f.direction === "positive" ? "▲ above" : "▼ below"}</span></td>
                      <td>{f.platform ? <PlatformLabel name={f.platform} /> : "—"}</td>
                      <td>{label(CONTENT_LABEL, f.content_type)}<div className="faint">{f.campaign}</div></td>
                      <td className="n">{metricValue(f.metric, f.value)}</td><td className="n">{metricValue(f.metric, f.baseline_median)}</td>
                      <td className="n">{ratio(f.score, 1)}</td><td className="n">{f.cohort_size}</td>
                    </tr>
                  ))}</tbody>
                </table></div>
                <Pager page={s.data.page.page} pages={s.data.page.pages} total={s.data.page.total} onPage={(n) => setParam("page", String(n))} />
              </div>
            ) : <Empty title="No unusual posts in this view">Nothing crossed the thresholds for the current filters.</Empty>}
          </Panel>
        </>
      )}
      <FlagDrawer id={flagId} onClose={() => setParam("flag", null)} />
    </div>
  );
}
