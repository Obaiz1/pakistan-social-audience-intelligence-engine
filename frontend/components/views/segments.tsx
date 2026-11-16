"use client";

import { ArrowRight, Users } from "lucide-react";
import Link from "next/link";
import { useApi } from "@/lib/api";
import { LANGUAGE_LABEL, heatAlpha, label, num, pct } from "@/lib/format";
import type { Meta } from "@/lib/types";
import { Trend } from "../charts";
import { useDataset } from "../dataset";
import { FilterBar, useFilters } from "../filters";
import { QuestionStepper } from "../story";
import { Empty, ErrorState, LoadingPage, MethodNote, Notice, PageHead, Panel, Segmented, TextCell } from "../ui";

type Top = { value: string; label: string; n: number; share: number; lift: number };
type Segment = {
  segment: string; name: string; need_label: string; uncertain: boolean;
  clusters: { cluster_id: number; label: string; size: number; agreement: number }[];
  comments: number; share_of_valid: number; name_agreement: number | null; posts_reached: number;
  language_mix: Record<string, number>; intent_mix: Record<string, number>;
  top: { campaign: Top[]; brand: Top[]; content_type: Top[] };
  monthly: Record<string, number>;
  examples: { comment_id: string; language_type: string; text: string | null; similarity: number | null }[];
  recommendations: { recommendation_id: string; title: string; priority: number }[];
};
type Resp = {
  meta: Meta; valid_comments: number; noise_comments: number; segments: Segment[]; text_visible: boolean;
  compare: { dimension: string; rows: { value: string; label: string; comments: number; shares: Record<string, number> }[] };
};

const DIMS = [
  { value: "campaign", label: "Campaign" }, { value: "brand", label: "Brand" },
  { value: "content_type", label: "Content type" }, { value: "platform", label: "Platform" },
] as const;

function TopList({ title, rows }: { title: string; rows: Top[] }) {
  if (!rows.length) return null;
  return (
    <div><div className="faint" style={{ fontWeight: 600 }}>{title}</div>
      <div className="row" style={{ gap: 6, marginTop: 4 }}>{rows.map((r) => (
        <span key={r.value} className="chip" title={`${pct(r.share, 0)} of this segment; ${r.lift.toFixed(2)}× its overall share`}>{r.label} <strong style={{ color: r.lift >= 1.5 ? "var(--accent-text)" : undefined }}>{r.lift.toFixed(1)}×</strong></span>
      ))}</div>
    </div>
  );
}

function SegmentCard({ s, total, textVisible }: { s: Segment; total: number; textVisible: boolean }) {
  const intent = (s.intent_mix.possible_inquiry ?? 0) + (s.intent_mix.strong_intent ?? 0);
  const trend = Object.entries(s.monthly).map(([month, n]) => ({ month, n }));
  return (
    <article className="rec" aria-labelledby={`seg-${s.segment}`}>
      <div className="row" style={{ justifyContent: "space-between" }}>
        <span className="eyebrow">{s.need_label}</span>
        {s.uncertain ? <span className="badge warn">uncertain</span> : <span className="badge accent">{pct(s.name_agreement, 0)} name agreement</span>}
      </div>
      <h3 id={`seg-${s.segment}`}>{s.name}</h3>
      <div className="row" style={{ gap: 18 }}>
        <div><div className="kpi-value" style={{ fontSize: 22 }}>{num(s.comments)}</div><div className="faint">comments · {pct(s.share_of_valid, 1)} of {num(total)}</div></div>
        <div><div className="kpi-value" style={{ fontSize: 22 }}>{num(s.posts_reached)}</div><div className="faint">posts reached</div></div>
        <div><div className="kpi-value" style={{ fontSize: 22 }}>{pct(intent / Math.max(s.comments, 1), 0)}</div><div className="faint">buying inquiries</div></div>
      </div>
      <div className="stack" style={{ gap: 6 }}>
        {s.examples.slice(0, 3).map((e) => (
          <div key={e.comment_id} className="quote"><TextCell text={e.text} withheld={!textVisible} /><div className="faint">{label(LANGUAGE_LABEL, e.language_type)}</div></div>
        ))}
      </div>
      <TopList title="Over-represented campaigns" rows={s.top.campaign} />
      <TopList title="Brands" rows={s.top.brand} />
      {trend.length > 2 && <Trend data={trend} height={90} />}
      <div className="row" style={{ gap: 6 }}>
        <span className="faint">From clusters:</span>
        {s.clusters.map((c) => <Link key={c.cluster_id} className="chip" href={`/audience?cluster=${c.cluster_id}`}>#{c.cluster_id} {c.label}</Link>)}
      </div>
      {s.recommendations.length ? (
        <div className="row" style={{ gap: 6 }}><span className="faint">Next action:</span>
          {s.recommendations.map((r) => <Link key={r.recommendation_id} className="chip" href={`/recommendations#${r.recommendation_id}`}>P{r.priority} · {r.title}</Link>)}</div>
      ) : <p className="faint">No action passed the evidence gates for this segment.</p>}
    </article>
  );
}

export function SegmentsView() {
  const { datasetId } = useDataset();
  const { filters, get, setParam } = useFilters();
  const compareBy = get("compare_by") ?? "campaign";
  const s = useApi<Resp>(datasetId ? "/audience/segments" : null, { dataset_id: datasetId, ...filters, compare_by: compareBy });
  return (
    <div className="grid">
      <QuestionStepper current={4} />
      <PageHead eyebrow="Question 4 · Segments" title="Which audience needs should the brand address?">
        Segments group the discovered comment clusters by the need they express — price askers, delivery-concerned shoppers, availability inquirers. They describe comments, not people.
      </PageHead>
      <FilterBar />
      <Notice tone="info" title="Unit of analysis: comments">
        A segment counts comments that fall in clusters sharing a need. No individual is profiled, identified or tracked; usernames are never stored.
      </Notice>
      {s.loading && <LoadingPage />}
      {s.error && <ErrorState error={s.error} status={s.status} onRetry={s.reload} />}
      {s.data && (s.data.segments.length ? (
        <>
          <MethodNote meta={s.data.meta} comments={s.data.valid_comments} extra={s.data.noise_comments ? <span className="chip">{num(s.data.noise_comments)} unclustered</span> : undefined} />
          <div className="grid cols-2">
            {s.data.segments.map((seg) => <SegmentCard key={seg.segment} s={seg} total={s.data!.valid_comments} textVisible={s.data!.text_visible} />)}
          </div>
          <Panel title="Compare segments" description="Share of each segment within a group's clustered comments (groups with at least 30 comments). Darker = larger share.">
            <div className="row" style={{ marginBottom: 12 }}>
              <Segmented label="Compare by" value={compareBy} onChange={(v) => setParam("compare_by", v)} options={DIMS.map((d) => ({ value: d.value, label: d.label }))} />
            </div>
            {s.data.compare.rows.length ? (
              <div className="table-wrap" tabIndex={0}><table className="data">
                <caption className="sr-only">Segment share by {compareBy}</caption>
                <thead><tr><th>{DIMS.find((d) => d.value === compareBy)?.label}</th><th className="n">Comments</th>{s.data.segments.map((g) => <th key={g.segment} className="n" title={g.name}>{g.need_label}</th>)}</tr></thead>
                <tbody>{s.data.compare.rows.map((r) => (
                  <tr key={r.value}><td>{r.label}</td><td className="n">{num(r.comments)}</td>
                    {s.data!.segments.map((g) => { const v = r.shares[g.segment] ?? 0; return <td key={g.segment} className="heat-cell" style={{ background: `rgba(var(--heat), ${heatAlpha(v)})` }}>{pct(v, 0)}</td>; })}</tr>
                ))}</tbody></table></div>
            ) : <Empty title="No group has 30 or more clustered comments" />}
          </Panel>
          <p className="faint"><Users size={12} aria-hidden="true" /> Segments are built from the selected clustering run; see the <Link href="/model">Model lab <ArrowRight size={11} /></Link> for how clusters were chosen.</p>
        </>
      ) : <Panel><Empty title="No segments in this view">There are no clustered comments for the current filters.</Empty></Panel>)}
    </div>
  );
}
