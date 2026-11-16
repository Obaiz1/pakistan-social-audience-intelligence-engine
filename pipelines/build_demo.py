"""Build the committed SYNTHETIC classroom dataset bundle (seed 42 by default).

    python pipelines/build_demo.py                       # semantic comparison (needs the [ml] extra), writes data/datasets/
    python pipelines/build_demo.py --embedding lexical    # no torch needed (lexical baseline only)

Output: data/datasets/synthetic-lawn-demo-v1/ — CSV tables + dataset.json (SHA-256 manifest) + evaluation.json.
"""

import argparse
import json
import shutil
import time

from common import ROOT, semantic_encoder  # first: puts backend/ on sys.path

# isort: split
from audienceiq.services.datasets import DEMO_ID, build_synthetic


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--posts", type=int, default=3000)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--embedding", choices=["lexical", "semantic", "hybrid", "compare"], default="compare")
    ap.add_argument("--model", choices=["minilm", "e5-small", "mpnet"], default="mpnet")
    ap.add_argument("--prefer", default=None, help="restrict selection to one representation (documented in evaluation)")
    ap.add_argument("--out", default=str(ROOT / "data" / "datasets"))
    args = ap.parse_args()

    encoder, model_desc = (None, "")
    if args.embedding != "lexical":
        encoder, model_desc = semantic_encoder(args.model)
    out = ROOT / "data" / "datasets"
    target = out / DEMO_ID
    if target.exists():
        shutil.rmtree(target)
    t = time.time()
    result = build_synthetic(
        n_posts=args.posts, seed=args.seed, embedding=args.embedding, semantic_encoder=encoder, semantic_model=model_desc,
        out_dir=out, k_values=[8, 10, 12, 14, 16, 18, 20, 24, 28], hdbscan_sizes=[60, 120, 250], hdbscan_reducer="umap",
        preferred=args.prefer)
    ev = result["evaluation"]
    print(json.dumps({
        "dataset": result["dataset"]["dataset_id"], "posts": result["dataset"]["post_count"],
        "comments": result["dataset"]["comment_count"], "seconds": round(time.time() - t, 1),
        "selected": ev["clustering"]["selected_key"],
        "synthetic_recovery": ev["synthetic_recovery"]["clusters_vs_true_need"],
        "audit_cluster_need_accuracy": (ev.get("audit") or {}).get("cluster_need_accuracy"),
        "anomaly_recall": ev["anomaly_recovery"]["recall"], "recommendations": len(result["tables"]["recommendations"]),
    }, indent=2))


if __name__ == "__main__":
    main()
