"use client";

import { useApi } from "@/lib/api";
import { LANGUAGE_LABEL, NEED_LABEL, label, num, pct, ratio } from "@/lib/format";
import type { Meta } from "@/lib/types";
import { useDataset } from "../dataset";
import { Bidi, Empty, ErrorState, Kpi, LoadingPage, MethodNote, Notice, PageHead, Panel } from "../ui";

type Ext = { ari: number | null; nmi: number | null; purity: number | null };
type Candidate = {
  run_id: string; embedding: string; algorithm: string; params: Record<string, unknown>; n_clusters: number; noise_rate: number;
  silhouette_cosine: number | null; davies_bouldin: number | null; stability_ari: number | null; min_cluster_share: number | null;
  eligible: boolean; selection_score: number | null; external: Record<string, Ext>;
};
type AuditExample = { audit_id: string; text: string; need: string; language: string; cluster_id: number; cluster_need: string; hit: boolean };
type Method = {
  meta: Meta;
  clustering: {
    selected: { run_id: string; embedding: string; embedding_model: string; algorithm: string; params: Record<string, unknown>; n_clusters: number; noise_rate: number; metrics: Record<string, number | null> };
    selection_rule: Record<string, unknown>;
    audit: null | { n: number; source: string; cluster_need_accuracy?: number; cluster_need_accuracy_by_language?: Record<string, number>; cluster_need_accuracy_by_need?: Record<string, number>; rule_labeller_accuracy: number; langid_accuracy: number; examples?: AuditExample[] };
    synthetic_recovery: null | { note: string; clusters_vs_true_need: Ext; clusters_vs_true_language: Ext };
  };
  nlp: { language_mix?: Record<string, number>; reference_unlabelled_share?: number };
};
type Eval = { evaluation: { clustering?: { candidates: Candidate[]; selected_key: string } } };

const STAGES = [
  { t: "Ingest", d: "Posts + comments from the dataset bundle (synthetic generator, YouTube API, or CSV import)." },
  { t: "Normalise", d: "Unicode NFKC, Urdu letter forms, PII → placeholders, emoji → tokens, Roman-Urdu spelling variants." },
  { t: "Language ID", d: "Script ratio + lexicon: English / Roman Urdu / Urdu / mixed / other." },
  { t: "Strip boilerplate", d: "Greetings and politeness words removed from the embedding input only (ADR-011)." },
  { t: "Roman-Urdu gloss", d: "Frequent Roman-Urdu words translated to English for the embedding input only (ADR-013)." },
  { t: "Embed", d: "Multilingual sentence encoder (semantic), with TF-IDF char/word n-grams as the baseline." },
  { t: "Cluster", d: "KMeans sweep + UMAP/HDBSCAN candidates; selection by silhouette × stability with noise and size gates." },
  { t: "Name & profile", d: "Majority reference label names each cluster after discovery; agreement share always shown." },
  { t: "Evidence", d: "Segments, peer-cohort anomalies and gated recommendations are built from the clusters." },
];

const METHODS = [
  { m: "Unsupervised clustering (used)", q: "What groups exist in the comments?", needs: "No labels — groups emerge from similarity; names attached afterwards.", risk: "Groups can mix needs; names are hints with an agreement share." },
  { m: "Supervised sentiment analysis", q: "Is a comment positive or negative?", needs: "Labelled training data.", risk: "Misses the need: “Delivery kitne din?” is neutral but clearly a delivery need." },
  { m: "Manual keyword taxonomy", q: "Does a comment mention a known topic?", needs: "A hand-written lexicon (our reference labeller).", risk: "Only finds what you already listed; brittle to new phrasing. Used here to name and audit clusters, not to form them." },
  { m: "Anomaly detection (Q3)", q: "Which posts behave unlike their peers?", needs: "Comparable cohorts and robust baselines.", risk: "Outliers are not proof of fraud, promotion or causality." },
];

export function ModelLabView() {
  const { datasetId } = useDataset();
  const m = useApi<Method>(datasetId ? "/methodology" : null, { dataset_id: datasetId });
  const e = useApi<Eval>(datasetId ? "/audience/evaluation" : null, { dataset_id: datasetId });
  if (m.loading) return <LoadingPage />;
  if (m.error || !m.data) return <ErrorState error={m.error ?? "No data"} status={m.status} onRetry={m.reload} />;
  const c = m.data.clustering;
  const sel = c.selected;
  const audit = c.audit;
  const rec = c.synthetic_recovery;
  const cands = e.data?.evaluation.clustering?.candidates ?? [];
  const misses = (audit?.examples ?? []).filter((x) => !x.hit).slice(0, 12);
  return (
    <div className="grid">
      <PageHead eyebrow="Evidence & data · Model lab" title="How the audience clusters were made — and how far to trust them">
        The exact pipeline, the configuration that produced the clusters you see, every candidate that was compared, and the cases the model gets wrong.
      </PageHead>
      <MethodNote meta={m.data.meta} comments={m.data.meta.sample_size} />

      <Panel title="Pipeline" description="Each stage as implemented in backend/audienceiq (nothing here is aspirational).">
        <ol className="grid cols-3" style={{ listStyle: "none", padding: 0, margin: 0, counterReset: "st" }}>
          {STAGES.map((s, i) => (
            <li key={s.t} className="quote" style={{ display: "grid", gap: 4 }}>
              <span className="eyebrow">Stage {i + 1}</span><strong>{s.t}</strong><span className="faint">{s.d}</span>
            </li>
          ))}
        </ol>
      </Panel>

      <div className="grid cols-4">
        <Kpi label="Selected model" value={sel.algorithm === "kmeans" ? `KMeans k=${String(sel.params.k)}` : "HDBSCAN"} sub={`${sel.embedding} representation`} />
        <Kpi label="Silhouette" value={ratio(sel.metrics.silhouette_cosine, 3)} sub="cosine, on a fixed 5,000-comment sample" help="Internal separation between clusters (−1…1). Low in absolute terms for sentence embeddings; not proof of real-world validity." />
        <Kpi label="Stability" value={ratio(sel.metrics.stability_ari, 3)} sub="ARI across re-seeded fits" />
        <Kpi label="Unclustered" value={pct(sel.noise_rate)} sub={`${sel.n_clusters} clusters`} />
      </div>
      <Panel title="Versioned configuration">
        <dl className="kv">
          <dt>Run</dt><dd className="mono">{sel.run_id}</dd>
          <dt>Encoder</dt><dd className="mono">{sel.embedding_model}</dd>
          <dt>Parameters</dt><dd className="mono">{JSON.stringify(sel.params)}</dd>
          <dt>Selection rule</dt><dd>{Object.entries(c.selection_rule).map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join(", ") : String(v)}`).join(" · ")}</dd>
          <dt>Unlabelled by reference lexicon</dt><dd>{pct(m.data.nlp.reference_unlabelled_share ?? null, 0)} of comments (kept as “other”, never forced into a need)</dd>
        </dl>
      </Panel>

      <div className="grid cols-2">
        <Panel title="ADR-013 · Audit cluster-name accuracy" description="The metric behind the “18 % → 52 %” improvement, stated precisely.">
          {audit && audit.cluster_need_accuracy !== undefined ? (
            <div className="stack">
              <div className="callout"><p className="lede">{pct(audit.cluster_need_accuracy, 0)} of {audit.n} hand-labelled audit comments land in a cluster whose post-hoc need equals the human label.</p></div>
              <dl className="kv">
                <dt>Definition</dt><dd>Each audit comment is assigned to its nearest cluster centre; a hit = that cluster&apos;s post-hoc need name equals the human label. Denominator: {audit.n} comments.</dd>
                <dt>History</dt><dd>18 % in the first full build without the Roman-Urdu gloss → {pct(audit.cluster_need_accuracy, 0)} in this build (ADR-013; docs/TEST_EVIDENCE.md). An exploratory run showed 46 % — not the shipped figure.</dd>
                <dt>By language</dt><dd>{Object.entries(audit.cluster_need_accuracy_by_language ?? {}).map(([l, v]) => `${label(LANGUAGE_LABEL, l)} ${pct(v, 0)}`).join(" · ")}</dd>
                <dt>Comparison</dt><dd>Rule-based reference labeller on the same comments: {pct(audit.rule_labeller_accuracy, 0)}. Language ID: {pct(audit.langid_accuracy, 0)}.</dd>
                <dt>What it is not</dt><dd>Not accuracy on real comments; the audit set was written by the same author as the templates and the gloss.</dd>
              </dl>
            </div>
          ) : <Notice tone="info" title="Not evaluated for this dataset">The independent audit runs on the synthetic classroom build. Switch to the synthetic dataset to see it.</Notice>}
        </Panel>
        <Panel title="Recovery of hidden structure (synthetic only)" description="How well clusters match the generator's hidden needs. Reported for transparency; never used to choose the model.">
          {rec ? (
            <dl className="kv">
              <dt>vs hidden need</dt><dd className="num">ARI {ratio(rec.clusters_vs_true_need.ari, 3)} · NMI {ratio(rec.clusters_vs_true_need.nmi, 3)} · purity {pct(rec.clusters_vs_true_need.purity, 0)}</dd>
              <dt>vs language</dt><dd className="num">NMI {ratio(rec.clusters_vs_true_language.nmi, 3)} <span className="faint">(lower = clusters are not driven by language)</span></dd>
              <dt>Caveat</dt><dd className="faint">{rec.note}</dd>
            </dl>
          ) : <Notice tone="info" title="No ground truth">Observed and imported data have no hidden labels, so recovery cannot be measured.</Notice>}
        </Panel>
      </div>

      <Panel title={`Experiment table — ${cands.length} candidates`} description="Every representation × algorithm compared. Only semantic and hybrid candidates may be selected (lexical = baseline, ADR-007a). Stability is computed for the four best eligible candidates.">
        {cands.length ? (
          <div className="table-wrap" tabIndex={0}><table className="data">
            <thead><tr><th>Representation</th><th>Algorithm</th><th className="n">k</th><th className="n">Noise</th><th className="n">Silhouette</th><th className="n">Min share</th><th className="n">Stability</th><th>Eligible</th><th className="n">Score</th><th className="n">NMI vs language</th></tr></thead>
            <tbody>{cands.map((x) => (
              <tr key={x.run_id} style={x.run_id === sel.run_id ? { background: "var(--accent-soft)" } : undefined}>
                <td>{x.embedding}{x.run_id === sel.run_id && <span className="badge accent" style={{ marginLeft: 6 }}>selected</span>}</td>
                <td>{x.algorithm} <span className="faint mono">{Object.entries(x.params).filter(([k]) => !["dims", "min_samples"].includes(k)).map(([k, v]) => `${k}=${v}`).join(",")}</span></td>
                <td className="n">{x.n_clusters}</td><td className="n">{pct(x.noise_rate, 0)}</td><td className="n">{ratio(x.silhouette_cosine, 3)}</td>
                <td className="n">{pct(x.min_cluster_share, 1)}</td><td className="n">{ratio(x.stability_ari, 3)}</td><td>{x.eligible ? "yes" : "no"}</td>
                <td className="n">{ratio(x.selection_score, 3)}</td><td className="n">{ratio(x.external?.language?.nmi ?? null, 3)}</td>
              </tr>))}</tbody></table></div>
        ) : e.loading ? <div className="skeleton" style={{ height: 240 }} /> : <Empty title="No candidate table for this dataset" />}
      </Panel>

      <Panel title="Error cases" description="Audit comments the selected model placed in a cluster named with a different need.">
        {misses.length ? (
          <div className="table-wrap" tabIndex={0}><table className="data"><thead><tr><th>Comment</th><th>Language</th><th>Human label</th><th>Cluster&apos;s need</th></tr></thead>
            <tbody>{misses.map((x) => <tr key={x.audit_id}><td><Bidi text={x.text} /></td><td>{label(LANGUAGE_LABEL, x.language)}</td><td>{label(NEED_LABEL, x.need)}</td><td>{label(NEED_LABEL, x.cluster_need)}</td></tr>)}</tbody></table></div>
        ) : <Empty title="No audit errors available for this dataset" />}
      </Panel>

      <Panel title="Which method answers which question" description="Why this project clusters comments instead of only classifying sentiment.">
        <div className="table-wrap" tabIndex={0}><table className="data"><thead><tr><th>Method</th><th>Question it answers</th><th>Needs</th><th>Main risk</th></tr></thead>
          <tbody>{METHODS.map((x) => <tr key={x.m}><td><strong>{x.m}</strong></td><td>{x.q}</td><td className="faint">{x.needs}</td><td className="faint">{x.risk}</td></tr>)}</tbody></table></div>
      </Panel>
      <p className="faint">Languages in this dataset: {Object.entries(m.data.nlp.language_mix ?? {}).map(([l, n]) => `${label(LANGUAGE_LABEL, l)} ${num(n)}`).join(" · ")}.</p>
    </div>
  );
}
