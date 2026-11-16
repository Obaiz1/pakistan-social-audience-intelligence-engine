"""Dataset factories (synthetic demo, CSV import, observed YouTube) and their evaluation extras."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from audienceiq.clustering.candidates import assign_nearest
from audienceiq.clustering.evaluate import external_agreement
from audienceiq.config import ROOT, get_settings
from audienceiq.constants import LANGUAGES, NEED_LABELS
from audienceiq.data import importer
from audienceiq.data.synthetic import CATEGORY, GENERATOR_VERSION, generate
from audienceiq.nlp.embeddings import hybrid
from audienceiq.nlp.gloss import embedding_text
from audienceiq.nlp.intent import label_need
from audienceiq.nlp.langid import detect_language
from audienceiq.nlp.normalize import normalize_text, strip_boilerplate
from audienceiq.services.build import RUNTIME_K, BuildConfig, build_dataset
from audienceiq.storage.db import write_bundle_dir
from audienceiq.storage.repository import get_repository

AUDIT_PATH = ROOT / "backend" / "tests" / "fixtures" / "multilingual_audit.csv"
DEMO_ID = "synthetic-lawn-demo-v1"
SYNTHETIC_SOURCE = {
    "source_id": "SRC-SYNTH", "source_type": "synthetic_generator", "name": f"AudienceIQ synthetic generator {GENERATOR_VERSION}",
    "url": None, "collection_method": "deterministic simulation (numpy default_rng)", "collected_at": None,
    "reuse_permission": "Synthetic; freely reusable for teaching. Not real social-media observations.",
    "notes": "Fictional brands (Brand A–F); comment texts are invented, compositional and illustrative.",
}


# ------------------------------------------------------------------ evaluation helpers
def audit_set() -> pd.DataFrame:
    return pd.read_csv(AUDIT_PATH, dtype=str) if AUDIT_PATH.exists() else pd.DataFrame()


def transform_like_selected(texts: list[str], result: dict, encoder=None) -> np.ndarray | None:
    emb = result["clustering"].selected["embedding"]
    stripped = [embedding_text(strip_boilerplate(normalize_text(t)), detect_language(t)) for t in texts]
    if emb == "lexical":
        return result["lexical"].transform(stripped)
    if encoder is None:
        return None
    sem = encoder(stripped)
    return sem if emb == "semantic" else hybrid(sem, result["lexical"].transform(stripped))


def run_audit(result: dict, encoder=None) -> dict | None:
    """Assign independently written, hand-labelled comments to the fitted clusters (nearest centroid) and compare the
    cluster's post-hoc need name with the human label. Also scores the rule labeller and language ID on the same set."""
    a = audit_set()
    if a.empty:
        return None
    x = transform_like_selected(a["text"].tolist(), result, encoder)
    profiles = {p["cluster_id"]: p for p in result["clustering"].profiles}
    out = {"n": int(len(a)), "source": "backend/tests/fixtures/multilingual_audit.csv (100 comments written for this "
           "audit, phrased differently from the generator templates; same author, so not fully independent)"}
    if x is not None:
        cid, dist = assign_nearest(x, result["clustering"].centroids)
        a["cluster_need"] = [profiles[int(c)]["need_category"] if int(c) in profiles else "noise" for c in cid]
        a["cluster_id"] = cid
        a["hit"] = a["cluster_need"] == a["need"]
        out["cluster_need_accuracy"] = round(float(a["hit"].mean()), 4)
        out["cluster_need_accuracy_by_language"] = {k: round(float(g["hit"].mean()), 4) for k, g in a.groupby("language")}
        out["cluster_need_accuracy_by_need"] = {k: round(float(g["hit"].mean()), 4) for k, g in a.groupby("need")}
        out["examples"] = a[["audit_id", "text", "need", "language", "cluster_id", "cluster_need", "hit"]].head(100).to_dict(
            orient="records")
    a["rule"] = [label_need(t).topic for t in a["text"]]
    out["rule_labeller_accuracy"] = round(float((a["rule"] == a["need"]).mean()), 4)
    a["lang_pred"] = [detect_language(t) for t in a["text"]]
    out["langid_accuracy"] = round(float((a["lang_pred"] == a["language"]).mean()), 4)
    out["langid_by_language"] = {k: round(float((g["lang_pred"] == g["language"]).mean()), 4) for k, g in a.groupby("language")}
    return out


def synthetic_recovery(result: dict, truth_comments: pd.DataFrame) -> dict:
    labels = result["clustering"].labels
    need = truth_comments["true_need"].to_numpy()
    lang = truth_comments["true_language"].to_numpy()
    c = result["comments"]
    return {
        "note": "Agreement with the generator's hidden latent need/language. Reported only — never used for model selection. "
                "High values on synthetic text do not imply real-world validity.",
        "clusters_vs_true_need": external_agreement(labels, need),
        "clusters_vs_true_language": external_agreement(labels, lang),
        "rule_labeller_accuracy_vs_true_need": round(float((c["topic"].to_numpy() == need).mean()), 4),
        "langid_accuracy_vs_true_language": round(float((c["language_type"].to_numpy() == lang).mean()), 4),
        "langid_confusion": pd.crosstab(pd.Series(lang, name="true"), pd.Series(c["language_type"].to_numpy(), name="pred"))
        .to_dict(),
    }


def anomaly_recovery(result: dict, truth_posts: pd.DataFrame) -> dict:
    flags = result["anomalies"]["flags"]
    injected = truth_posts[truth_posts["injected_anomaly"] != ""]
    flagged = set(flags["post_id"]) if len(flags) else set()
    scored = set(result["anomalies"]["scores"]["post_id"])
    by_type = {}
    for kind, g in injected.groupby("injected_anomaly"):
        ids = set(g["post_id"])
        by_type[kind] = {"injected": len(ids), "scored": len(ids & scored), "detected": len(ids & flagged),
                         "recall": round(len(ids & flagged) / len(ids), 4) if ids else None}
    inj = set(injected["post_id"])
    return {"note": "Recall against anomalies deliberately injected into the synthetic corpus. Precision is a lower bound: "
                    "natural extremes in the simulated data are also legitimately unusual.",
            "injected": len(inj), "flagged_posts": len(flagged), "detected_injected": len(inj & flagged),
            "recall": round(len(inj & flagged) / len(inj), 4) if inj else None,
            "share_of_flags_that_were_injected": round(len(inj & flagged) / len(flagged), 4) if flagged else None,
            "by_type": by_type}


# ------------------------------------------------------------------ synthetic
def build_synthetic(n_posts: int = 3000, seed: int = 42, embedding: str = "lexical", semantic_encoder=None,
                    semantic_model: str = "", out_dir: Path | None = None, persist_user: bool = False,
                    k_values: list[int] | None = None, hdbscan_sizes: list[int] | None = None,
                    hdbscan_reducer: str = "pca", preferred: str | list[str] | None = None) -> dict:
    corpus = generate(n_posts, seed)
    default = n_posts == 3000 and seed == 42 and out_dir is not None
    dataset_id = DEMO_ID if default else f"synthetic-lawn-s{seed}-n{n_posts}"
    cfg = BuildConfig(
        dataset_id=dataset_id, name=("Synthetic lawn-suit classroom demo (seed 42)" if default
                                     else f"Synthetic lawn-suit demo (seed {seed}, {n_posts} posts)"),
        mode="synthetic", product_category=CATEGORY,
        description=("Deterministic SYNTHETIC corpus of women's lawn-suit social posts for six fictional brands on Instagram, "
                     "TikTok, Facebook and YouTube with multilingual (English, Roman Urdu, Urdu, mixed) comments. Simulates "
                     "brand-owned analytics exports; injected anomalies are recorded separately for evaluation."),
        snapshot_at=corpus.snapshot_at.isoformat().replace("+00:00", "Z"), text_permission="illustrative",
        sources=[SYNTHETIC_SOURCE], seed=seed, generator_version=GENERATOR_VERSION, embedding=embedding,
        semantic_encoder=semantic_encoder, semantic_model=semantic_model, k_values=k_values or list(RUNTIME_K),
        hdbscan_sizes=hdbscan_sizes or [], hdbscan_reducer=hdbscan_reducer, preferred_embedding=preferred,
        truth={"synthetic_true_need": corpus.truth_comments["true_need"].to_numpy(),
               "synthetic_true_language": corpus.truth_comments["true_language"].to_numpy()})
    result = build_dataset(corpus.posts, corpus.comments, corpus.campaigns, cfg)
    ev = result["evaluation"]
    ev["synthetic_recovery"] = synthetic_recovery(result, corpus.truth_comments)
    ev["anomaly_recovery"] = anomaly_recovery(result, corpus.truth_posts)
    ev["audit"] = run_audit(result, semantic_encoder)
    ev["langid"] = {"synthetic": ev["synthetic_recovery"]["langid_accuracy_vs_true_language"],
                    "audit": (ev["audit"] or {}).get("langid_accuracy")}
    ds = result["dataset"]
    if out_dir is not None:
        write_bundle_dir(out_dir / dataset_id, ds, result["tables"], {
            "evaluation.json": ev, "synthetic_truth_posts": corpus.truth_posts,
            "synthetic_truth_comments": corpus.truth_comments})
    if persist_user:
        import json
        ds = dict(ds, manifest_json=json.dumps({"evaluation": ev}, default=str))
        get_repository().save_user_bundle(ds, result["tables"])
    result["dataset"] = ds
    return ds | {"evaluation": ev} if out_dir is None else result


# ------------------------------------------------------------------ CSV import
def build_import(req) -> dict:
    import json

    snapshot = datetime.now(UTC)
    raw_p = importer.read_csv_text(req.posts_csv or "", importer.MAX_POST_ROWS)
    pmap = {**importer.suggest_mapping(list(raw_p.columns), importer.POST_FIELDS), **(req.posts_mapping or {})}
    vp = importer.validate_posts(raw_p, pmap, snapshot)
    raw_c = importer.read_csv_text(req.comments_csv or "", importer.MAX_COMMENT_ROWS)
    cmap = {**importer.suggest_mapping(list(raw_c.columns), importer.COMMENT_FIELDS), **(req.comments_mapping or {})}
    vc = importer.validate_comments(raw_c, cmap, set(vp["frame"]["post_id"]))
    if vp["rows_valid"] < 20 or vc["rows_valid"] < 30:
        raise importer.ImportError_("Need at least 20 valid posts and 30 valid joined comments to analyse an import.")
    posts = vp["frame"].drop(columns=["platform_raw"], errors="ignore")
    if (req.product_category or "").strip():
        posts["product_category"] = posts["product_category"].replace("Unspecified", req.product_category)
    stamp = snapshot.strftime("%Y%m%d%H%M%S")
    slug = "".join(ch if ch.isalnum() else "-" for ch in req.name.lower()).strip("-")[:40]
    att = req.attestation
    source = {"source_id": "SRC-IMPORT", "source_type": "user_csv", "name": req.name, "url": att.source_url,
              "collection_method": f"CSV upload ({'observed export' if att.data_kind == 'observed' else 'synthetic/simulated'})",
              "collected_at": att.collected_at, "reuse_permission": "Uploader attested permission to use and store locally",
              "notes": att.source_description}
    cfg = BuildConfig(
        dataset_id=f"import-{slug}-{stamp}", name=req.name, mode="imported", product_category=req.product_category,
        description=f"Imported CSV ({att.data_kind}); {att.source_description}",
        snapshot_at=snapshot.isoformat(timespec="seconds").replace("+00:00", "Z"), text_permission="full",
        sources=[source], embedding="lexical", k_values=list(RUNTIME_K))
    comments = vc["frame"][["comment_id", "post_id", "comment_text", "published_at", "like_count"]]
    result = build_dataset(posts, comments, pd.DataFrame(columns=["campaign_id"]), cfg)
    ds = dict(result["dataset"], manifest_json=json.dumps({"evaluation": result["evaluation"],
                                                           "validation": {"posts_warnings": vp["warnings"],
                                                                          "comments_warnings": vc["warnings"]}}, default=str))
    get_repository().save_user_bundle(ds, result["tables"])
    return {"dataset_id": ds["dataset_id"], "posts": ds["post_count"], "comments": ds["comment_count"],
            "clusters": int(result["clustering"].selected["n_clusters"]),
            "selected_model": result["evaluation"]["clustering"]["selected_key"],
            "anomaly_flags": int(len(result["anomalies"]["flags"])), "recommendations": int(len(result["tables"]["recommendations"])),
            "warnings": vp["warnings"] + vc["warnings"]}


# ------------------------------------------------------------------ observed YouTube
def build_observed(posts: pd.DataFrame, comments: pd.DataFrame, snapshot: datetime, quota_used: int, brands: list[str],
                   semantic_encoder=None, semantic_model: str = "", out_dir: Path | None = None,
                   k_values: list[int] | None = None) -> dict:
    expires = snapshot + timedelta(days=30)
    source = {"source_id": "SRC-YT", "source_type": "youtube_data_api_v3",
              "name": "YouTube Data API v3 (public channel, video and top-level comment data)",
              "url": "https://developers.google.com/youtube/v3", "collection_method": f"Official API, API key; ~{quota_used} quota units",
              "collected_at": snapshot.date().isoformat(),
              "reuse_permission": ("YouTube API Services Terms: stored API data refreshed or deleted within 30 days; comment "
                                   "text and author identity not redistributed"),
              "notes": f"Official channels pinned by channel ID (from Repo A config): {', '.join(brands)}."}
    snap = snapshot.isoformat(timespec="seconds").replace("+00:00", "Z")
    cfg = BuildConfig(
        dataset_id=f"observed-youtube-{snapshot.strftime('%Y%m%d')}", name=f"Observed YouTube snapshot {snapshot.date()}",
        mode="observed", product_category="Pakistani clothing brands (YouTube channels)",
        description=("OBSERVED public YouTube statistics for official Pakistani clothing-brand channels. Platform = YouTube "
                     "only; content type 'video' (no reel/short claim); campaign inferred from title keywords. Comment text "
                     "is withheld from this bundle; clusters were fitted locally on the text and only derived labels ship."),
        snapshot_at=snap, expires_at=expires.isoformat(timespec="seconds").replace("+00:00", "Z"), text_permission="withheld",
        sources=[source], embedding="semantic" if semantic_encoder else "lexical", semantic_encoder=semantic_encoder,
        semantic_model=semantic_model, k_values=k_values or [4, 5, 6, 7, 8, 9, 10])
    result = build_dataset(posts, comments, pd.DataFrame(columns=["campaign_id"]), cfg)
    result["evaluation"]["langid"] = {"note": "No ground truth for observed comments."}
    if out_dir is not None:
        write_bundle_dir(out_dir / cfg.dataset_id, result["dataset"], result["tables"], {"evaluation.json": result["evaluation"]})
    return result


LANGUAGE_SET = set(LANGUAGES)
NEED_SET = set(NEED_LABELS)
_ = get_settings
