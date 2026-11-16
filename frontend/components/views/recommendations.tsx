"use client";

import Link from "next/link";
import { useApi } from "@/lib/api";
import { ACTION_LABEL, CONTENT_LABEL, NEED_LABEL, label, num } from "@/lib/format";
import type { Evidence, Meta, Recommendation } from "@/lib/types";
import { useDataset } from "../dataset";
import { useFilters } from "../filters";
import { Empty, ErrorState, LoadingPage, MethodNote, Notice, PageHead, Panel, Segmented } from "../ui";

type Resp = { meta: Meta; llm_wording_enabled: boolean; recommendations: Recommendation[]; counts: { by_action: Record<string, number>; by_priority: Record<string, number> } };

function EvidenceLink({ e }: { e: Evidence }) {
  if (e.type === "cluster") return <Link className="chip" href={`/audience?cluster=${e.id}`}>Cluster #{e.id} · {e.label} · {num(e.size ?? 0)}</Link>;
  if (e.type === "anomaly") return <Link className="chip mono" href={`/anomalies?flag=${e.id}`}>{e.post_id}</Link>;
  if (e.type === "need_concentration") return <Link className="chip" href={`/campaigns`}>{label(NEED_LABEL, e.need)} in {e.dimension}: {e.value} · {e.lift?.toFixed(2)}×</Link>;
  if (e.type === "content_comparison") return <Link className="chip" href={`/content?content_type=${e.group}`}>Content comparison · {label(CONTENT_LABEL, e.group)}</Link>;
  return <span className="chip">{e.type}</span>;
}

export function RecCard({ r }: { r: Recommendation }) {
  return (
    <article className="rec" id={r.recommendation_id} aria-labelledby={`${r.recommendation_id}-t`}>
      <div className="row">
        <span className="badge accent">Priority {r.priority}</span>
        <span className="badge">{label(ACTION_LABEL, r.action_type)}</span>
        <span className={`badge ${r.evidence_strength === "strong" ? "ok" : r.evidence_strength === "moderate" ? "" : "warn"}`}>{r.evidence_strength} evidence</span>
        {r.audience_need && <span className="badge">{label(NEED_LABEL, r.audience_need)}</span>}
        <span className="faint mono" style={{ marginLeft: "auto" }}>{r.recommendation_id}</span>
      </div>
      <h3 id={`${r.recommendation_id}-t`}>{r.title}</h3>
      <p><strong>What to do: </strong>{r.what_to_do}</p>
      <p className="why"><strong>Why: </strong>{r.why_it_matters}</p>
      <div className="row"><span className="faint">Evidence:</span>{r.linked_evidence.slice(0, 8).map((e, i) => <EvidenceLink key={i} e={e} />)}{r.linked_evidence.length > 8 && <span className="faint">+{r.linked_evidence.length - 8} more</span>}</div>
      <div className="row"><span className="faint">Where:</span>{Object.entries(r.where).map(([k, v]) => <span key={k} className="chip">{k.replace("_", " ")}: {k === "content_type" ? label(CONTENT_LABEL, v) : v}</span>)}<span className="chip num">n = {num(r.sample_size)}</span></div>
      <details>
        <summary>Test plan, numbers and limitations</summary>
        <p style={{ marginTop: 8 }}><strong>Suggested test: </strong>{r.test_plan}</p>
        <ul>{Object.entries(r.metrics).map(([k, v]) => <li key={k}><span className="mono">{k}</span>: {String(v)}</li>)}</ul>
        <ul>{r.limitations.map((l) => <li key={l}>{l}</li>)}</ul>
      </details>
    </article>
  );
}

export function RecommendationsView() {
  const { datasetId } = useDataset();
  const { get, setParam } = useFilters();
  const action = get("action_type") ?? "";
  const priority = get("priority") ?? "";
  const s = useApi<Resp>(datasetId ? "/recommendations" : null, { dataset_id: datasetId, action_type: action, priority });
  return (
    <div className="grid">
      <PageHead eyebrow="Q5 · Recommendations" title="What should the marketing team do next?">
        Each card is generated from evidence that passed explicit gates — cluster support and name agreement, statistically significant need concentrations, significant content effects, or recurring anomalies. If the evidence is not there, no card is produced.
      </PageHead>
      <div className="row">
        <Segmented label="Action type" value={action} onChange={(v) => setParam("action_type", v || null)}
          options={[{ value: "", label: "All actions" }, ...Object.entries(ACTION_LABEL).map(([value, l]) => ({ value, label: l }))]} />
        <Segmented label="Priority" value={priority} onChange={(v) => setParam("priority", v || null)}
          options={[{ value: "", label: "Any priority" }, { value: "1", label: "P1" }, { value: "2", label: "P2" }, { value: "3", label: "P3" }]} />
      </div>
      {s.loading && <LoadingPage />}
      {s.error && <ErrorState error={s.error} status={s.status} onRetry={s.reload} />}
      {s.data && (
        <>
          <MethodNote meta={s.data.meta} extra={<span className="chip">{s.data.llm_wording_enabled ? "AI wording available (numbers locked)" : "Deterministic wording (no AI)"}</span>} />
          {s.data.meta.mode === "synthetic" && <Notice tone="warn" title="Synthetic demonstration">These recommendations demonstrate the method on simulated data. They are not findings about any real brand.</Notice>}
          {s.data.recommendations.length ? (
            <div className="grid cols-2">{s.data.recommendations.map((r) => <RecCard key={r.recommendation_id} r={r} />)}</div>
          ) : <Panel><Empty title="No recommendation passed the evidence gates">Try removing filters or check the Methodology page for the gate thresholds.</Empty></Panel>}
        </>
      )}
    </div>
  );
}
