"""Train + evaluate the listing classifier.

  python -m tapdix_ml.nlp.train --data ml/data/synthetic --gold ml/data/gold/gold.json \
         --out ml/models/text_clf.joblib --report ml/reports/text_clf_report.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from tapdix_ml.nlp.classifier import ListingClassifier, listing_text
from tapdix_ml.nlp.evaluate import evaluate, max_category_confidence, risk_coverage
from tapdix_ml.text.normalize import normalize


def load_listings(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


def train_model(data: Path) -> ListingClassifier:
    """Fit the production-style model on the clear, train-split listings (no evaluation, ~10-20 s)."""
    rows = [
        r
        for r in load_listings(data / "listings.jsonl")
        if r["text_quality"] == "clear" and r["split"] == "train"
    ]
    return ListingClassifier().fit(
        [listing_text(r["title"], r["description"]) for r in rows],
        [r["labels"]["problem_type"] for r in rows],
    )


def run(data: Path, gold_path: Path, out: Path | None, report: Path | None) -> dict[str, Any]:
    rows = load_listings(data / "listings.jsonl")
    clear = [r for r in rows if r["text_quality"] == "clear"]
    vague = [r for r in rows if r["text_quality"] == "vague"]
    train = [r for r in clear if r["split"] == "train"]
    test = [r for r in clear if r["split"] == "test"]
    txt = lambda r: listing_text(r["title"], r["description"])  # noqa: E731
    gold = json.loads(gold_path.read_text(encoding="utf-8"))

    model = ListingClassifier().fit(
        [txt(r) for r in train], [r["labels"]["problem_type"] for r in train]
    )
    g_clear, g_vague = gold["clear"], gold["vague"]
    res: dict[str, Any] = {
        "train_size": len(train),
        "synthetic_test_unseen_phrasings": evaluate(
            model, [txt(r) for r in test], [r["labels"]["problem_type"] for r in test]
        ),
        "gold_independent": evaluate(
            model, [g["text"] for g in g_clear], [g["problem_type"] for g in g_clear]
        ),
        "gold_by_style": {},
    }
    for style in sorted({g["style"] for g in g_clear}):
        sub = [g for g in g_clear if g["style"] == style]
        res["gold_by_style"][style] = evaluate(
            model, [g["text"] for g in sub], [g["problem_type"] for g in sub]
        )["category_accuracy"]

    gold_conf = max_category_confidence(model, [g["text"] for g in g_clear])
    vague_conf = max_category_confidence(
        model, [g["text"] for g in g_vague] + [txt(r) for r in vague]
    )
    res["confidence_clear_gold_median"] = round(float(sorted(gold_conf)[len(gold_conf) // 2]), 3)
    res["confidence_vague_median"] = round(float(sorted(vague_conf)[len(vague_conf) // 2]), 3)
    res["risk_coverage_gold"] = risk_coverage(
        model, [g["text"] for g in g_clear], [g["problem_type"] for g in g_clear]
    )
    res["vague_share_above_threshold"] = {
        str(t): round(float((vague_conf >= t).mean()), 3) for t in (0.5, 0.6, 0.7, 0.8)
    }

    res["risk_coverage_synthetic_test"] = risk_coverage(
        model, [txt(r) for r in test], [r["labels"]["problem_type"] for r in test]
    )

    # learning curve: does accuracy grow with the NUMBER OF DIFFERENT WORDINGS seen per problem type?
    res["learning_curve_unseen_phrasings"] = []
    for k in (1, 2, 3, 4):
        keep = {f"az{i}" for i in range(k)} | {"ru0"}
        sub = [r for r in train if r["bundle"] in keep]
        m = ListingClassifier().fit(
            [txt(r) for r in sub], [r["labels"]["problem_type"] for r in sub]
        )
        ev = evaluate(m, [txt(r) for r in test], [r["labels"]["problem_type"] for r in test])
        res["learning_curve_unseen_phrasings"].append(
            {
                "az_phrasings_per_problem": k,
                "train_size": len(sub),
                "problem_acc": ev["problem_accuracy"],
                "category_acc": ev["category_accuracy"],
                "skill_hit_rate": ev["skill_hit_rate"],
            }
        )

    # ablation: what does the Azerbaijani-aware normalisation buy us?
    abl = ListingClassifier(normalize_fn=lambda t: normalize(t, fold=False)).fit(
        [txt(r) for r in train], [r["labels"]["problem_type"] for r in train]
    )
    res["ablation_no_diacritic_folding_gold_category_acc"] = evaluate(
        abl, [g["text"] for g in g_clear], [g["problem_type"] for g in g_clear]
    )["category_accuracy"]

    if out:
        model.save(out)
    if report:
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    return res


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--data", type=Path, default=Path("ml/data/synthetic"))
    ap.add_argument("--gold", type=Path, default=Path("ml/data/gold/gold.json"))
    ap.add_argument("--out", type=Path, default=Path("ml/models/text_clf.joblib"))
    ap.add_argument("--report", type=Path, default=Path("ml/reports/text_clf_report.json"))
    a = ap.parse_args()
    print(json.dumps(run(a.data, a.gold, a.out, a.report), indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
