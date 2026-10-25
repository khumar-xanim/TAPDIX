"""Try Tapdix on your own text.

  python -m tapdix_ml.demo "Mətbəx kranı su axıdır, təcili" --district Nəsimi --urgency Urgent
  python -m tapdix_ml.demo "Usta lazımdır, şəkildə görünür" --detect ac_indoor_unit:0.9 --detect water_leak_stain:0.7

--detect simulates what a photo detector would return (label:confidence); labels are in ml/data/vision/classes.json.
The text model is trained on first use (~15 s) and cached in ml/models/ (git-ignored).
"""

from __future__ import annotations

import argparse
from pathlib import Path

from tapdix_ml.data.taxonomy import DATA_DIR
from tapdix_ml.nlp.classifier import ListingClassifier
from tapdix_ml.nlp.train import train_model
from tapdix_ml.pipeline import load_masters, recommend
from tapdix_ml.vision.fusion import Detection

DEFAULT_MODEL = DATA_DIR.parent / "models" / "text_clf.joblib"
DEFAULT_MASTERS = DATA_DIR / "synthetic" / "masters.csv"


def load_or_train(path: Path = DEFAULT_MODEL) -> ListingClassifier:
    if path.exists():
        return ListingClassifier.load(path)
    print("No saved model yet - training one on the synthetic dataset (about 15 s)...")
    model = train_model(DATA_DIR / "synthetic")
    model.save(path)
    return model


def analyze(
    model: ListingClassifier,
    masters_path: Path,
    text: str,
    *,
    title: str = "",
    city: str = "Bakı",
    district: str = "Nəsimi",
    urgency: str = "Normal",
    detections: list[Detection] | None = None,
    k: int = 3,
) -> str:
    rec = recommend(
        model,
        load_masters(masters_path),
        title=title,
        description=text,
        city=city,
        district=district,
        urgency=urgency,
        detections=detections,
        k=k,
    )
    t, d = rec.text, rec.decision
    lines = [
        "TEXT UNDERSTANDING",
        f"  category     : {t.category} ({t.category_prob:.2f})",
        f"  problem type : {t.problem_type} ({t.problem_prob:.2f})",
        "  top 3        : " + ", ".join(f"{c} {p:.2f}" for c, p in t.top_k),
        "  key words    : " + (", ".join(w for w, _ in t.keywords) or "(none - text too vague)"),
        "DECISION",
        f"  source={d.source}  category={d.category}  problem={d.problem_type}  confidence={d.confidence}",
        *[f"  why: {r}" for r in d.reasons],
    ]
    if d.clarification_az:
        lines.append(f"  ASK THE CUSTOMER: {d.clarification_az}")
    if d.request_photo:
        lines.append("  (also asking for a photo)")
    lines.append("TOP MASTERS (synthetic data)")
    lines += [
        f"  {i}. {m.master_id[:8]}  score={m.score:.3f}  - " + "; ".join(m.reasons)
        for i, m in enumerate(rec.matches, 1)
    ]
    if not rec.matches:
        lines.append("  (none - nothing to match until the problem is clear)")
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("text", help="the customer's announcement")
    ap.add_argument("--title", default="")
    ap.add_argument("--city", default="Bakı")
    ap.add_argument("--district", default="Nəsimi")
    ap.add_argument("--urgency", default="Normal", choices=["Low", "Normal", "Urgent", "Emergency"])
    ap.add_argument(
        "--detect",
        action="append",
        default=[],
        metavar="LABEL:CONF",
        help="simulated photo detection",
    )
    ap.add_argument("--k", type=int, default=3)
    ap.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    ap.add_argument("--masters", type=Path, default=DEFAULT_MASTERS)
    a = ap.parse_args()
    dets = [Detection(x.split(":")[0], float(x.split(":")[1])) for x in a.detect]
    print(
        analyze(
            load_or_train(a.model),
            a.masters,
            a.text,
            title=a.title,
            city=a.city,
            district=a.district,
            urgency=a.urgency,
            detections=dets or None,
            k=a.k,
        )
    )


if __name__ == "__main__":
    main()
