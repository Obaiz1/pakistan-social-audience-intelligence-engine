"use client";

import { useApi } from "@/lib/api";
import { CONTENT_LABEL, NEED_LABEL, label, num, pct, ratio } from "@/lib/format";
import type { Comparison, Meta, NeedsBy } from "@/lib/types";
import { CIPlot, CompareTable, NeedHeat } from "../charts";
import { useDataset } from "../dataset";
import { FilterBar, useFilters } from "../filters";
import { ChartTable, ErrorState, LoadingPage, MethodNote, Notice, PageHead, Panel } from "../ui";

type Resp = {
  meta: Meta;
  comparison: Comparison;
  campaigns: { campaign: string; posts: number; posts_mature: number; immature_share: number; maturity_warning: boolean; date_min: string; date_max: string; platforms: Record<string, number>; content_types: Record<string, number>; weighted_er: number | null; median_attention_index: number | null }[];
  needs_by_campaign: NeedsBy[];
  campaign_calendar: { campaign_id: string; name: string; campaign_type: string; start_date: string | null; end_date: string | null; campaign_source: string }[];
};

export function CampaignsView() {
  const { datasetId } = useDataset();
  const { filters } = useFilters();
  const s = useApi<Resp>(datasetId ? "/analytics/campaigns" : null, { dataset_id: datasetId, ...filters });
  return (
    <div className="grid">
      <PageHead eyebrow="Q1 · Q4 · Campaigns" title="How do campaigns compare, and what does each campaign's audience ask for?">
        Eid, 11.11, 12.12, sale and seasonal campaigns compared on the attention index, with the discovered audience needs that are over-represented in each campaign. Comparisons are associational: campaigns differ in budget, timing and product.
      </PageHead>
      <FilterBar show={["platform", "brand", "content_type", "date"]} />
      {s.loading && <LoadingPage />}
      {s.error && <ErrorState error={s.error} status={s.status} onRetry={s.reload} />}
      {s.data && (() => {
        const d = s.data;
        const warn = d.campaigns.filter((c) => c.maturity_warning);
        const needs = Array.from(new Set(d.needs_by_campaign.flatMap((r) => r.needs.filter((n) => n.lift >= 1.3).map((n) => n.need))))
          .concat(["price", "discount", "delivery", "availability"]).filter((v, i, a) => a.indexOf(v) === i && !["mixed", "noise"].includes(v)).slice(0, 8);
        return (
          <>
            <MethodNote meta={d.meta} posts={d.meta.sample_size} />
            {warn.length > 0 && <Notice tone="warn" title="Immature campaigns">{warn.map((c) => c.campaign).join(", ")}: most posts are younger than 7 days, so their engagement is still accumulating and they are excluded from the comparison until mature.</Notice>}
            <Panel title="Attention index by campaign" description={d.comparison.metric_help}>
              <ChartTable label="Attention index by campaign" summary={`Median attention index with 95% CI for ${num(d.comparison.posts_compared)} mature posts; * = significant after BH correction with at least a small effect.`}
                chart={<CIPlot rows={d.comparison.rows} />} table={<CompareTable rows={d.comparison.rows} />} />
            </Panel>
            <Panel title="Campaign summary" description="Posts, maturity and weighted engagement rate (Σ interactions ÷ Σ views, mature posts that report views).">
              <div className="table-wrap"><table className="data">
                <thead><tr><th>Campaign</th><th>Window</th><th className="n">Posts</th><th className="n">Mature</th><th className="n">Weighted ER</th><th className="n">Median attention</th><th>Main formats</th></tr></thead>
                <tbody>{d.campaigns.map((c) => (
                  <tr key={c.campaign}>
                    <td>{c.campaign}{c.maturity_warning && <span className="badge warn" style={{ marginLeft: 6 }}>immature</span>}</td>
                    <td className="faint">{c.date_min} → {c.date_max}</td>
                    <td className="n">{num(c.posts)}</td><td className="n">{num(c.posts_mature)}</td>
                    <td className="n">{pct(c.weighted_er, 2)}</td><td className="n">{ratio(c.median_attention_index)}</td>
                    <td className="faint">{Object.entries(c.content_types).slice(0, 3).map(([t, n]) => `${label(CONTENT_LABEL, t)} ${n}`).join(" · ")}</td>
                  </tr>
                ))}</tbody>
              </table></div>
            </Panel>
            <Panel title="Q4 · Audience needs by campaign" description="Share of each discovered need among a campaign's clustered comments. ▲ = at least 1.5× the overall share. This is where campaign-specific service and messaging actions come from.">
              <NeedHeat rows={d.needs_by_campaign} dim="campaign" needs={needs} caption="Audience needs by campaign" />
              <p className="faint" style={{ marginTop: 8 }}>Needs shown: {needs.map((n) => label(NEED_LABEL, n)).join(", ")}.</p>
            </Panel>
            <Panel title="Campaign calendar" description="Campaign definitions in this dataset and how they were assigned.">
              <div className="table-wrap"><table className="data"><thead><tr><th>Campaign</th><th>Type</th><th>Start</th><th>End</th><th>Source</th></tr></thead>
                <tbody>{d.campaign_calendar.length ? d.campaign_calendar.map((c) => <tr key={c.campaign_id}><td>{c.name}</td><td>{c.campaign_type}</td><td>{c.start_date ?? "—"}</td><td>{c.end_date ?? "—"}</td><td className="faint">{c.campaign_source.replace(/_/g, " ")}</td></tr>)
                  : <tr><td colSpan={5} className="faint">Campaigns come from the imported/collected data (no calendar table).</td></tr>}</tbody></table></div>
            </Panel>
          </>
        );
      })()}
    </div>
  );
}
