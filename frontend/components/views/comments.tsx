"use client";

import { useEffect, useState } from "react";
import { useApi } from "@/lib/api";
import { LANGUAGE_LABEL, NEED_LABEL, label, num } from "@/lib/format";
import type { CommentRow, Meta, PageInfo } from "@/lib/types";
import { useDataset } from "../dataset";
import { FilterBar, useFilters, useOptions } from "../filters";
import { Empty, ErrorState, LoadingPage, MethodNote, Notice, PageHead, Pager, Panel, TextCell } from "../ui";

type Resp = {
  meta: Meta;
  permission: { text_permission: string; text_visible: boolean; note: string };
  summary: Record<"languages" | "topics" | "intent" | "sentiment", Record<string, number>>;
  page: PageInfo;
  rows: CommentRow[];
};

const INTENTS = [{ value: "strong_intent", label: "Strong intent" }, { value: "possible_inquiry", label: "Possible inquiry" }, { value: "none", label: "None" }, { value: "unknown", label: "Unknown" }];
const SENTIMENTS = ["positive", "neutral", "negative", "unknown"];

export function CommentsView() {
  const { datasetId } = useDataset();
  const { filters, get, setParam } = useFilters();
  const opts = useOptions().data;
  const [q, setQ] = useState(get("q") ?? "");
  useEffect(() => {
    const t = setTimeout(() => { if ((get("q") ?? "") !== q) setParam("q", q || null); }, 350);
    return () => clearTimeout(t);
  }, [q, get, setParam]);
  const params = { dataset_id: datasetId, ...filters, cluster_id: get("cluster_id"), language: get("language"), topic: get("topic"),
    intent: get("intent"), sentiment: get("sentiment"), q: get("q"), page: Number(get("page") ?? 1), page_size: 25 };
  const s = useApi<Resp>(datasetId ? "/comments" : null, params);
  const sel = (key: string, lab: string, options: { value: string | number; label: string }[]) => (
    <label className="field" htmlFor={`c-${key}`}>{lab}
      <select id={`c-${key}`} className="select" value={get(key) ?? ""} onChange={(e) => setParam(key, e.target.value || null)}>
        <option value="">All</option>
        {options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>
    </label>
  );
  return (
    <div className="grid">
      <PageHead eyebrow="Q2 · Comment explorer" title="Read what the audience actually says">
        Each comment carries its discovered cluster, detected language, a rule-based reference topic, a purchase-intent hint and a heuristic sentiment. Usernames are never stored; observed comment text is withheld where reuse is not permitted.
      </PageHead>
      <FilterBar />
      <div className="filterbar" aria-label="Comment filters">
        {sel("cluster_id", "Cluster", opts?.clusters ?? [])}
        {sel("language", "Language", opts?.languages ?? [])}
        {sel("topic", "Reference topic", opts?.topics ?? [])}
        {sel("intent", "Purchase intent", INTENTS)}
        {sel("sentiment", "Sentiment", SENTIMENTS.map((x) => ({ value: x, label: x })))}
        <label className="field" htmlFor="c-q">Search text<input id="c-q" className="input" value={q} onChange={(e) => setQ(e.target.value)} placeholder="e.g. delivery" maxLength={80} /></label>
      </div>
      {s.loading && <LoadingPage />}
      {s.error && <ErrorState error={s.error} status={s.status} onRetry={s.reload} />}
      {s.data && (
        <>
          <MethodNote meta={s.data.meta} comments={s.data.page.total} />
          <Notice tone={s.data.permission.text_visible ? "info" : "warn"} title={s.data.permission.text_visible ? "Text visibility" : "No permission to show comment text"}>{s.data.permission.note}</Notice>
          <div className="grid cols-4">
            {(["languages", "topics", "intent", "sentiment"] as const).map((k) => (
              <Panel key={k} flat title={k === "topics" ? "Reference topics" : k[0].toUpperCase() + k.slice(1)}>
                <div className="stack" style={{ gap: 4 }}>
                  {Object.entries(s.data!.summary[k]).slice(0, 6).map(([name, n]) => (
                    <div key={name} className="row" style={{ justifyContent: "space-between", fontSize: 13 }}>
                      <span>{k === "languages" ? label(LANGUAGE_LABEL, name) : k === "topics" ? label(NEED_LABEL, name) : name.replace("_", " ")}</span>
                      <span className="num faint">{num(n)}</span>
                    </div>
                  ))}
                </div>
              </Panel>
            ))}
          </div>
          <Panel title="Comments" description="Purchase intent 'possible inquiry' is a question about buying — not a confirmed purchase. Sentiment is a supporting heuristic only.">
            {s.data.rows.length ? (
              <div className="stack">
                <div className="table-wrap"><table className="data">
                  <thead><tr><th>Comment</th><th>Language</th><th>Cluster</th><th>Reference topic</th><th>Intent</th><th>Sentiment</th><th>Post</th></tr></thead>
                  <tbody>{s.data.rows.map((c) => (
                    <tr key={c.comment_id}>
                      <td style={{ maxWidth: 380 }}><TextCell text={c.comment_text} withheld={!s.data!.permission.text_visible} /></td>
                      <td>{label(LANGUAGE_LABEL, c.language_type)}</td>
                      <td>{c.cluster_id === null ? "—" : <button className="link" type="button" onClick={() => setParam("cluster_id", String(c.cluster_id))}>{c.cluster_label}</button>}</td>
                      <td>{label(NEED_LABEL, c.topic)}</td>
                      <td>{c.purchase_intent.replace("_", " ")}</td>
                      <td>{c.sentiment}</td>
                      <td className="mono faint">{c.post_id}<div>{c.platform} · {c.campaign}</div></td>
                    </tr>
                  ))}</tbody>
                </table></div>
                <Pager page={s.data.page.page} pages={s.data.page.pages} total={s.data.page.total} onPage={(n) => setParam("page", String(n))} />
              </div>
            ) : <Empty title="No comments match these filters">Clear a filter or widen the date range.</Empty>}
          </Panel>
        </>
      )}
    </div>
  );
}
