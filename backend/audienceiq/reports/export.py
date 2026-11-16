"""CSV / Excel / PDF exports. Every export carries the dataset disclaimer and provenance; no comment text is exported
when the dataset's text permission is 'withheld'."""

import io
import json
from datetime import UTC, datetime

import pandas as pd
from fpdf import FPDF

from audienceiq.constants import CONTENT_TYPE_LABELS, NEED_LABELS, PROJECT_TITLE, SHORT_NAME

SECTIONS = ("summary", "posts", "comments", "clusters", "anomalies", "recommendations")
_FORMULA = ("=", "+", "-", "@", "\t", "\r")


def safe_cell(value):
    """CSV/Excel formula-injection guard (pattern from Repo B analytics/metrics.py safe_csv_cell)."""
    if isinstance(value, str) and value.startswith(_FORMULA):
        return "'" + value
    return value


def _safe(df: pd.DataFrame) -> pd.DataFrame:
    return df.apply(lambda col: col.map(safe_cell) if col.dtype == object else col)


def section_frame(f, section: str, posts: pd.DataFrame) -> pd.DataFrame:
    ids = set(posts["post_id"])
    if section == "posts":
        cols = ["post_id", "brand", "platform", "campaign", "content_type", "product_category", "likes", "comments_count",
                "shares", "views", "days_since_post", "published_at", "interactions", "er_views", "er_formula",
                "attention_index", "mature", "source_type", "observed_vs_synthetic", "source_url"]
        return posts[cols]
    if section == "comments":
        cc = f.comments_clustered
        cc = cc[cc["post_id"].isin(ids)]
        cols = ["comment_id", "post_id", "comment_text", "language_type", "topic", "sentiment", "purchase_intent",
                "cluster_id", "cluster_label", "need", "published_at", "text_permission"]
        out = cc[cols].copy()
        if f.meta["text_permission"] == "withheld":
            out["comment_text"] = None
        return out
    if section == "clusters":
        cols = ["cluster_id", "label", "need_category", "label_agreement", "size", "share", "cohesion", "top_terms_json",
                "language_mix_json", "date_min", "date_max", "explanation"]
        return f.profiles[cols]
    if section == "anomalies":
        fl = f.flags[f.flags["post_id"].isin(ids)]
        return fl.merge(posts[["post_id", "brand", "platform", "content_type", "campaign"]], on="post_id", how="left")[
            ["flag_id", "post_id", "brand", "platform", "content_type", "campaign", "kind", "direction", "severity", "metric",
             "value", "baseline_median", "expected_low", "expected_high", "score", "cohort_key", "cohort_size", "reason",
             "caveat"]]
    if section == "recommendations":
        return f.recommendations[["recommendation_id", "priority", "action_type", "title", "what_to_do", "why_it_matters",
                                  "audience_need", "evidence_strength", "sample_size", "test_plan", "limitations_json",
                                  "linked_evidence_json"]]
    return summary_frame(f, posts)


def summary_frame(f, posts: pd.DataFrame) -> pd.DataFrame:
    m = f.meta
    sel = f.selected_run or {}
    rows = [("Project", PROJECT_TITLE), ("Dataset", m["name"]), ("Mode", m["mode"]), ("Disclaimer", m["disclaimer"]),
            ("Snapshot", m["snapshot_at"]), ("Posts in export", len(posts)), ("Posts in dataset", m["post_count"]),
            ("Comments in dataset", m["comment_count"]),
            ("Clustering", f"{sel.get('embedding')} · {sel.get('algorithm')} {sel.get('params_json')} · run {sel.get('run_id')}"),
            ("Anomaly flags", len(f.flags)), ("Recommendations", len(f.recommendations)),
            ("Sources", "; ".join(f"{s['name']} ({s['reuse_permission']})" for s in m.get("sources", []))),
            ("Exported at", datetime.now(UTC).isoformat(timespec="seconds"))]
    return pd.DataFrame(rows, columns=["field", "value"])


def report_metadata(f, filters: dict | None, rows: int | None = None) -> list[tuple[str, str]]:
    """Metadata repeated on every export: source mode, dataset/model versions, filters, time, counts, limitations."""
    sel = f.selected_run or {}
    return [("product", SHORT_NAME), ("disclaimer", f.meta["disclaimer"]), ("mode", f.meta["mode"]),
            ("dataset", f.meta["dataset_id"]), ("snapshot", str(f.meta["snapshot_at"])),
            ("dataset posts / comments", f"{f.meta['post_count']} / {f.meta['comment_count']}"),
            ("clustering run", f"{sel.get('run_id')} ({sel.get('model_version')})"),
            ("filters", "; ".join(f"{k}={v}" for k, v in (filters or {}).items()) or "none"),
            ("rows in this export", "" if rows is None else str(rows)),
            ("generated", datetime.now(UTC).isoformat(timespec="seconds")),
            ("limitations", "Associational analysis; anomalies are statistical outliers, not fraud claims; "
                            "synthetic data demonstrates the method only")]


def to_csv(f, section: str, posts: pd.DataFrame, filters: dict | None = None) -> bytes:
    frame = _safe(section_frame(f, section, posts))
    buf = io.StringIO()
    buf.write(f"# {SHORT_NAME} export — {section}\n")
    for k, v in report_metadata(f, filters, len(frame)):
        buf.write(f"# {k}: {v}\n")
    frame.to_csv(buf, index=False, lineterminator="\n")
    return buf.getvalue().encode("utf-8-sig")


def to_xlsx(f, posts: pd.DataFrame, filters: dict | None = None) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as xw:
        for section in SECTIONS:
            df = _safe(section_frame(f, section, posts))
            if section == "comments" and len(df) > 50_000:
                df = df.head(50_000)
            df.to_excel(xw, sheet_name=section[:31], index=False)
        pd.DataFrame(report_metadata(f, filters), columns=["field", "value"]).to_excel(xw, sheet_name="README", index=False)
    return buf.getvalue()


def _latin(text) -> str:
    return str(text).encode("latin-1", "replace").decode("latin-1").replace("—", "-").replace("–", "-")


def _line(pdf: FPDF, h: float, text: str) -> None:
    pdf.multi_cell(0, h, text, new_x="LMARGIN", new_y="NEXT")


class _PDF(FPDF):
    disclaimer = ""

    def header(self):
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(150, 40, 40)
        self.cell(0, 6, _latin(self.disclaimer), new_x="LMARGIN", new_y="NEXT", align="C")
        self.set_text_color(0, 0, 0)

    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", "", 8)
        self.cell(0, 8, f"{SHORT_NAME} - page {self.page_no()}", align="C")


def to_pdf(f, posts: pd.DataFrame, content: dict) -> bytes:
    pdf = _PDF()
    pdf.disclaimer = f.meta["disclaimer"].replace("—", "-")
    pdf.set_auto_page_break(True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 14)
    _line(pdf, 7, _latin(PROJECT_TITLE))
    pdf.set_font("Helvetica", "", 10)
    for field, value in summary_frame(f, posts).itertuples(index=False):
        _line(pdf, 5, _latin(f"{field}: {value}"))
    pdf.ln(2)

    def heading(t):
        pdf.set_font("Helvetica", "B", 12)
        _line(pdf, 7, _latin(t))
        pdf.set_font("Helvetica", "", 9)

    heading("Q1 Which content attracts attention? (median attention index, mature posts)")
    for r in content.get("rows", [])[:8]:
        ci = f"{r['ci_low']:.2f}-{r['ci_high']:.2f}" if r.get("ci_low") is not None else "n/a"
        sig = f", BH p={r['p_adj']:.3f} ({r['effect']})" if r.get("p_adj") is not None else ""
        _line(pdf, 5, _latin(f"- {CONTENT_TYPE_LABELS.get(r['group'], r['group'])}: n={r['n']}, median "
                                    f"{(r['median'] or 0):.2f} (95% CI {ci}){sig}"))
    heading("Q2/Q4 Discovered audience-need clusters")
    for p in f.profiles.sort_values("size", ascending=False).head(12).itertuples(index=False):
        terms = ", ".join(json.loads(p.top_terms_json)[:5])
        _line(pdf, 5, _latin(f"- #{p.cluster_id} {p.label}: {p.size} comments ({p.share:.1%}), name agreement "
                                    f"{p.label_agreement:.0%}; terms: {terms}"))
    heading("Q3 Unusual posts (statistical outliers vs comparable posts; not fraud claims)")
    fl = f.flags[f.flags["post_id"].isin(set(posts["post_id"]))].copy()
    fl["abs"] = fl["score"].abs()
    for r in fl.sort_values("abs", ascending=False).head(10).itertuples(index=False):
        _line(pdf, 5, _latin(f"- {r.post_id} [{r.kind}, {r.direction}]: {r.reason}"))
    heading("Q5 Recommendations (evidence-linked)")
    for r in f.recommendations.head(10).itertuples(index=False):
        _line(pdf, 5, _latin(f"- P{r.priority} {r.title} ({r.evidence_strength}, n={r.sample_size}): {r.why_it_matters}"))
        _line(pdf, 5, _latin(f"  Test: {r.test_plan}"))
    heading("Limitations")
    for t in ["Associational analysis, not causal.", "Synthetic data, if shown, demonstrates the method only.",
              "Cluster names come from a rule-based reference labeller applied after unsupervised discovery.",
              "Urdu-script text is omitted from this PDF (font limitation); see the CSV/Excel exports."]:
        _line(pdf, 5, _latin(f"- {t}"))
    return bytes(pdf.output())


def need_label(n: str | None) -> str:
    return NEED_LABELS.get(n or "", n or "")
