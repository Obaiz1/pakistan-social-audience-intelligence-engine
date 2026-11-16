"use client";

import { ArrowRight, Clock } from "lucide-react";
import Link from "next/link";
import { Fragment } from "react";
import { useApi } from "@/lib/api";
import { num, pct, ratio } from "@/lib/format";
import type { Meta, Source } from "@/lib/types";
import { useDataset } from "../dataset";
import { ErrorState, LoadingPage, MethodNote, Notice, Panel } from "../ui";

type Candidate = { run_id: string; embedding: string; algorithm: string; params: Record<string, unknown>; n_clusters: number; noise_rate: number; silhouette_cosine: number | null; davies_bouldin: number | null; stability_ari: number | null; min_cluster_share: number | null; eligible: boolean; selection_score: number | null; external: Record<string, { ari: number | null; nmi: number | null; purity: number | null }> };
type Method = {
  meta: Meta;
  project_title: string; product_name: string; short_name: string;
  questions: { id: string; question: string; route: string; method: string }[];
  dataset: { name: string; mode: string; disclaimer: string; posts: number; comments: number; snapshot_at: string; seed: number | null; generator_version: string | null; sources: Source[]; text_permission: string; description: string | null };
  engagement: { formulas: Record<string, string>; mature_days: number; attention_index: string; weighted_er: string; missing_values: string };
  clustering: { selected: { run_id: string; embedding: string; embedding_model: string; algorithm: string; params: Record<string, unknown>; n_clusters: number; noise_rate: number; metrics: Record<string, unknown> }; selection_rule: Record<string, unknown>; candidates: number; naming: string;
    audit: null | { n: number; source: string; cluster_need_accuracy?: number; cluster_need_accuracy_by_language?: Record<string, number>; rule_labeller_accuracy: number; langid_accuracy: number; langid_by_language: Record<string, number> };
    synthetic_recovery: null | { note: string; clusters_vs_true_need: Record<string, number>; clusters_vs_true_language: Record<string, number>; rule_labeller_accuracy_vs_true_need: number; langid_accuracy_vs_true_language: number } };
  anomalies: { min_cohort: number; z_threshold: number; high_z: number; mix_alpha: number; iforest_top: number; caveat: string; evaluation: null | { note: string; injected: number; flagged_posts: number; detected_injected: number; recall: number; share_of_flags_that_were_injected: number; by_type: Record<string, { injected: number; detected: number; recall: number }> } };
  recommendations: Record<string, number | string>;
  limitations: string[]; reproducibility: string[];
  upstream: { repo: string; commit: string; reused: string }[]; new_in_project3: string[];
};
type Eval = { evaluation: { clustering?: { candidates: Candidate[]; selected_key: string } } };

const DEMO: { min: string; route: string; title: string; say: string }[] = [
  { min: "0:00", route: "/", title: "Overview", say: "State the data mode and disclaimer first, then read the five answers in order." },
  { min: "1:00", route: "/content", title: "Q1 · Attention", say: "Open the content-type chart; point at the confidence intervals and the 'no clear difference' verdicts — not just the winner." },
  { min: "2:00", route: "/audience", title: "Q2 · Audience needs", say: "Pick the price-inquiry cluster, show a Roman-Urdu comment with its gloss, then the linked post and the evidence trail." },
  { min: "3:15", route: "/anomalies", title: "Q3 · Anomaly lab", say: "Open the strongest flag; read the cohort, the baseline and the caveat that outliers are not fraud." },
  { min: "4:15", route: "/segments", title: "Q4 · Segments", say: "Compare segments by campaign; stress that segments count comments, not people." },
  { min: "5:00", route: "/recommendations", title: "Q5 · Action center", say: "Walk one card: opportunity → why → evidence chips → suggested test → caveat. Set it to 'Planned'." },
  { min: "6:00", route: "/model", title: "Model lab", say: "Show the selection rule, the 18 % → 52 % audit and an error case. Finish on the printable brief (/reports/brief)." },
];

export function MethodologyView() {
  const { datasetId } = useDataset();
  const s = useApi<Method>(datasetId ? "/methodology" : null, { dataset_id: datasetId });
  const e = useApi<Eval>(datasetId ? "/audience/evaluation" : null, { dataset_id: datasetId });
  if (s.loading) return <LoadingPage />;
  if (s.error || !s.data) return <ErrorState error={s.error ?? "No data"} status={s.status} onRetry={s.reload} />;
  const m = s.data;
  const sel = m.clustering.selected;
  const cands = e.data?.evaluation.clustering?.candidates ?? [];
  const audit = m.clustering.audit;
  const rec = m.clustering.synthetic_recovery;
  const an = m.anomalies.evaluation;
  return (
    <div className="grid">
      <section className="hero" aria-labelledby="mtitle">
        <div className="eyebrow">Evidence &amp; data · Methodology</div>
        <h1 id="mtitle">{m.project_title}</h1>
        <p>{m.product_name} ({m.short_name}) — a small web application that groups similar audience behaviour, identifies unusual patterns and turns those discoveries into evidence-based marketing decisions. The central technique is unsupervised clustering of multilingual comments, not sentiment classification.</p>
      </section>
      <MethodNote meta={m.meta} posts={m.dataset.posts} comments={m.dataset.comments} />

      <Panel title="The five questions and where they are answered">
        <div className="table-wrap" tabIndex={0}><table className="data"><thead><tr><th>ID</th><th>Question</th><th>Method</th><th>View</th></tr></thead>
          <tbody>{m.questions.map((q) => <tr key={q.id}><td><strong>{q.id}</strong></td><td>{q.question}</td><td className="faint">{q.method}</td><td><Link className="btn sm" href={q.route}>Open</Link></td></tr>)}</tbody></table></div>
      </Panel>

      <Panel title="Seven-minute demo walkthrough" description="A suggested path for presenting the project. Each step opens the screen it describes.">
        <ol className="stack" style={{ margin: 0, paddingLeft: 0, listStyle: "none", gap: 8 }}>
          {DEMO.map((d) => (
            <li key={d.route} className="row" style={{ alignItems: "flex-start", gap: 12, flexWrap: "nowrap" }}>
              <span className="chip num" style={{ minWidth: 58, justifyContent: "center" }}><Clock size={11} aria-hidden="true" /> {d.min}</span>
              <span><Link href={d.route}><strong>{d.title}</strong></Link> <span className="muted">— {d.say}</span></span>
            </li>
          ))}
        </ol>
      </Panel>

      <div className="grid cols-2">
        <Panel title="Data" description={m.dataset.description ?? undefined}>
          <dl className="kv">
            <dt>Dataset</dt><dd>{m.dataset.name}</dd><dt>Mode</dt><dd>{m.dataset.mode} — {m.dataset.disclaimer}</dd>
            <dt>Records</dt><dd className="num">{num(m.dataset.posts)} posts · {num(m.dataset.comments)} comments</dd>
            <dt>Snapshot</dt><dd>{m.dataset.snapshot_at}</dd>
            {m.dataset.seed !== null && <><dt>Seed</dt><dd>{m.dataset.seed} · {m.dataset.generator_version}</dd></>}
            <dt>Comment text</dt><dd>{m.dataset.text_permission}</dd>
            {m.dataset.sources.map((src) => <Fragment key={src.source_id}><dt>Source</dt><dd>{src.name}. {src.collection_method}. <span className="faint">{src.reuse_permission}</span></dd></Fragment>)}
          </dl>
        </Panel>
        <Panel title="Engagement metrics (Q1)">
          <dl className="kv">
            {Object.entries(m.engagement.formulas).map(([p, f]) => <Fragment key={p}><dt>{p}</dt><dd className="mono">{f}</dd></Fragment>)}
            <dt>Attention index</dt><dd>{m.engagement.attention_index}</dd>
            <dt>Weighted ER</dt><dd>{m.engagement.weighted_er}</dd>
            <dt>Maturity</dt><dd>Posts younger than {m.engagement.mature_days} days are excluded from comparisons and baselines.</dd>
            <dt>Missing values</dt><dd>{m.engagement.missing_values}</dd>
            <dt>Statistics</dt><dd>Medians with bootstrap 95% CIs (2,000 resamples), Mann-Whitney U vs rest, Cliff&apos;s δ, Benjamini–Hochberg, n ≥ 20 per tested group.</dd>
          </dl>
        </Panel>
      </div>

      <Panel title="Comment clustering (Q2/Q4)" description={m.clustering.naming}>
        <div className="grid cols-2">
          <dl className="kv">
            <dt>Pipeline</dt><dd>Unicode/PII normalisation → Roman-Urdu spelling variants → greeting/politeness removal → sentence embedding → clustering → post-hoc naming → profiling.</dd>
            <dt>Selected run</dt><dd className="mono">{sel.run_id}</dd>
            <dt>Representation</dt><dd>{sel.embedding} · {sel.embedding_model}</dd>
            <dt>Algorithm</dt><dd>{sel.algorithm} {JSON.stringify(sel.params)}</dd>
            <dt>Clusters · noise</dt><dd className="num">{sel.n_clusters} · {pct(sel.noise_rate)}</dd>
            <dt>Silhouette (cosine)</dt><dd className="num">{ratio(sel.metrics.silhouette_cosine as number, 3)}</dd>
            <dt>Davies–Bouldin</dt><dd className="num">{ratio(sel.metrics.davies_bouldin as number, 3)}</dd>
            <dt>Stability (ARI)</dt><dd className="num">{ratio(sel.metrics.stability_ari as number, 3)}</dd>
            <dt>Selection rule</dt><dd>{Object.entries(m.clustering.selection_rule).map(([k, v]) => `${k}: ${String(v)}`).join(" · ")}</dd>
          </dl>
          <div className="stack">
            {audit && (
              <Notice tone="info" title={`Independent multilingual audit (${audit.n} hand-labelled comments)`}>
                <span>Cluster-name accuracy {audit.cluster_need_accuracy !== undefined ? pct(audit.cluster_need_accuracy, 0) : "n/a"}{audit.cluster_need_accuracy_by_language && ` (${Object.entries(audit.cluster_need_accuracy_by_language).map(([l, v]) => `${l.replace("_", " ")} ${pct(v, 0)}`).join(", ")})`}. Rule labeller {pct(audit.rule_labeller_accuracy, 0)}. Language ID {pct(audit.langid_accuracy, 0)}.</span>
                <span className="faint" style={{ display: "block" }}>{audit.source}</span>
              </Notice>
            )}
            {rec && (
              <Notice tone="warn" title="Recovery of the synthetic generator's hidden needs (reported, not used for selection)">
                <span>Clusters vs true need: ARI {ratio(rec.clusters_vs_true_need.ari, 3)}, NMI {ratio(rec.clusters_vs_true_need.nmi, 3)}, purity {pct(rec.clusters_vs_true_need.purity, 0)}. Clusters vs language: NMI {ratio(rec.clusters_vs_true_language.nmi, 3)} (lower = less driven by language). Language ID {pct(rec.langid_accuracy_vs_true_language, 0)}; rule labeller {pct(rec.rule_labeller_accuracy_vs_true_need, 0)}.</span>
                <span className="faint" style={{ display: "block" }}>{rec.note}</span>
              </Notice>
            )}
          </div>
        </div>
        <p className="faint" style={{ marginTop: 12 }}>All {cands.length || "the"} candidate runs, the error cases and the method comparison are in the <Link href="/model">Model lab <ArrowRight size={11} aria-hidden="true" /></Link>.</p>
      </Panel>

      <div className="grid cols-2">
        <Panel title="Unusual-post detection (Q3)">
          <dl className="kv">
            <dt>Peer cohort</dt><dd>Most specific of brand × platform × content type → platform × content type → platform with ≥ {m.anomalies.min_cohort} mature posts.</dd>
            <dt>Engagement</dt><dd>Robust z of log metric (median/MAD); |z| ≥ {m.anomalies.z_threshold} flags, ≥ {m.anomalies.high_z} high severity.</dd>
            <dt>Comment pattern</dt><dd>Robust z of log(comments ÷ likes), posts with ≥ 20 comments.</dd>
            <dt>Need mix</dt><dd>Exact binomial test of the most over-represented discovered need vs cohort; BH-adjusted p &lt; {m.anomalies.mix_alpha}.</dd>
            <dt>Multivariate</dt><dd>Isolation Forest (seed 42) as a secondary score; top {pct(m.anomalies.iforest_top, 0)} only when no rule fired.</dd>
            <dt>Caveat</dt><dd>{m.anomalies.caveat}</dd>
          </dl>
          {an && <Notice tone="warn" title="Recovery of injected synthetic anomalies"><span>{an.detected_injected} of {an.injected} injected anomalies flagged (recall {pct(an.recall, 0)}); {pct(an.share_of_flags_that_were_injected, 0)} of flagged posts were injected. By type: {Object.entries(an.by_type).map(([k, v]) => `${k.replace(/_/g, " ")} ${v.detected}/${v.injected}`).join(", ")}.</span><span className="faint" style={{ display: "block" }}>{an.note}</span></Notice>}
        </Panel>
        <Panel title="Recommendations (Q5)">
          <dl className="kv">
            <dt>Need cards</dt><dd>Cluster name agreement ≥ {pct(Number(m.recommendations.min_agreement), 0)}, ≥ {m.recommendations.min_support} comments and ≥ {pct(Number(m.recommendations.min_share), 0)} of clustered comments.</dd>
            <dt>Concentration cards</dt><dd>Lift ≥ {m.recommendations.min_lift}×, two-proportion z-test, BH-adjusted p &lt; {m.recommendations.alpha}.</dd>
            <dt>Content cards</dt><dd>Significant attention-index difference with effect size ≥ small.</dd>
            <dt>Investigation cards</dt><dd>≥ {m.recommendations.min_flags} anomaly flags of one kind and direction.</dd>
            <dt>AI wording</dt><dd>{String(m.recommendations.llm)}</dd>
          </dl>
        </Panel>
      </div>

      <div className="grid cols-2">
        <Panel title="Limitations"><ul style={{ margin: 0, paddingLeft: 18 }}>{m.limitations.map((l) => <li key={l} className="muted" style={{ marginBottom: 4 }}>{l}</li>)}</ul></Panel>
        <Panel title="Reproduce">
          <pre className="mono" style={{ whiteSpace: "pre-wrap", margin: 0, background: "var(--surface)", padding: 12, borderRadius: 10, border: "1px solid var(--line)" }}>{m.reproducibility.join("\n")}</pre>
        </Panel>
      </div>

      <Panel title="What came from earlier projects, and what is new">
        <div className="grid cols-2">
          <div className="table-wrap" tabIndex={0}><table className="data"><thead><tr><th>Upstream repository</th><th>Reused</th></tr></thead>
            <tbody>{m.upstream.map((u) => <tr key={u.repo}><td className="mono">{u.repo}@{u.commit}</td><td className="faint">{u.reused}</td></tr>)}</tbody></table></div>
          <div><strong>New for Project 3</strong><ul style={{ paddingLeft: 18 }}>{m.new_in_project3.map((n) => <li key={n} className="muted">{n}</li>)}</ul></div>
        </div>
      </Panel>
    </div>
  );
}
