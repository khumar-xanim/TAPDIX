"""Synthetic dataset generator for the 8 core repair groups.

Outputs (in --out):
  listings.jsonl   one announcement per line (JSON): text, structured details, location, budget, photos, labels
  listings.csv     the same listings as a flat table (photo links live in `photo_paths`)
  masters.csv      synthetic masters (skills, areas, rating, availability)
  manifest.json    counts + sha256 of each file (reproducibility check)
  DATASET_CARD.md  what the data is - and is NOT

HONESTY NOTE: text comes from hand-written phrasings recombined with random context; it is for building and
testing the pipeline. It does not reproduce the difficulty of real customer text, and prices/ratings are
invented. Real accuracy must be measured on real listings.

Run:  python -m tapdix_ml.data.generate --out ml/data/synthetic
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
import uuid
from collections import Counter
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from .taxonomy import load_phrasebank, load_taxonomy, problem_index

NAMESPACE = uuid.UUID("6f1c2e0a-5b7d-4c53-9a58-0d6f4f2b9a11")
AS_OF = datetime(2026, 10, 23, 12, 0, 0, tzinfo=UTC)
URGENCIES = ["Low", "Normal", "Urgent", "Emergency"]
_DIACRITICS = str.maketrans(
    {
        "ə": "e",
        "Ə": "E",
        "ı": "i",
        "İ": "I",
        "ö": "o",
        "Ö": "O",
        "ü": "u",
        "Ü": "U",
        "ç": "c",
        "Ç": "C",
        "ş": "s",
        "Ş": "S",
        "ğ": "g",
        "Ğ": "G",
    }
)
CAR_MAKES = ["Toyota", "Hyundai", "Kia", "Mercedes", "BMW", "Chevrolet", "Lada", "Nissan"]
DEVICE_BRANDS = ["Apple", "Samsung", "Xiaomi", "Lenovo", "HP", "Sony", "LG", "Asus"]


def _nice(x: float) -> int:
    step = 5 if x >= 40 else 1
    return max(step, int(round(x / step)) * step)


def _details(cat: str, code: str, rng: random.Random) -> dict[str, Any]:
    if cat == "plumbing":
        return {"water_can_be_shut_off": rng.random() < 0.7, "floor": rng.randint(1, 16)}
    if cat == "electrical":
        return {
            "whole_flat_affected": rng.random() < 0.35,
            "building_age_years": rng.choice([3, 10, 20, 35, 50]),
        }
    if cat == "locksmith":
        return {
            "door_type": "car" if code == "car_lockout" else rng.choice(["entry", "interior"]),
            "child_or_pet_inside": rng.random() < 0.08,
        }
    if cat == "appliance_repair":
        return {"appliance_age_years": rng.randint(0, 15), "under_warranty": rng.random() < 0.2}
    if cat == "automotive_repair":
        return {
            "car_make": rng.choice(CAR_MAKES),
            "model_year": rng.randint(2000, 2025),
            "drivable": rng.random() < 0.6,
        }
    if cat == "electronics_repair":
        return {"device_brand": rng.choice(DEVICE_BRANDS), "device_age_years": rng.randint(0, 8)}
    if cat == "painting_renovation":
        return {
            "area_sqm": rng.randint(10, 120),
            "materials_provided_by_customer": rng.random() < 0.3,
        }
    return {
        "unit_btu": rng.choice([9000, 12000, 18000, 24000]),
        "gas_involved": code == "boiler_combi_error",
    }


def _budget(price: list[int], rng: random.Random) -> dict[str, Any]:
    lo, hi = price
    r = rng.random()
    if r < 0.35:
        return {"min": None, "max": None, "type": "Negotiable", "currency": "AZN"}
    center = math.exp(rng.uniform(math.log(lo), math.log(hi)))
    if r < 0.50:
        v = _nice(center)
        return {"min": v, "max": v, "type": "Fixed", "currency": "AZN"}
    bmin = _nice(center * rng.uniform(0.6, 0.95))
    bmax = max(_nice(center * rng.uniform(1.05, 1.6)), bmin + 1)
    return {"min": bmin, "max": bmax, "type": "Range", "currency": "AZN"}


def _typo(word: str, rng: random.Random) -> str:
    if len(word) < 5:
        return word
    i = rng.randint(1, len(word) - 3)
    return word[:i] + word[i + 1] + word[i] + word[i + 2 :]


def _noise(text: str, flags: dict[str, Any], rng: random.Random) -> str:
    if flags["typo"]:
        words = text.split(" ")
        for _ in range(rng.randint(1, 2)):
            j = rng.randrange(len(words))
            words[j] = _typo(words[j], rng)
        text = " ".join(words)
    if flags["strip"]:
        text = text.translate(_DIACRITICS)
    if flags["case"] == "lower":
        text = text.lower()
    elif flags["case"] == "upper":
        text = text.upper()
    if flags["bang"]:
        text = text.rstrip(".") + "!!"
    return text


def _compose(
    code: str,
    lang: str,
    vague: bool,
    bundle_idx: int,
    urgency: str,
    budget: dict[str, Any],
    city: str,
    district: str,
    rng: random.Random,
) -> tuple[str, str]:
    bank, ctx, vg = (
        load_phrasebank()["bundles"][code],
        load_phrasebank()["context"],
        load_phrasebank()["vague"],
    )
    if vague:
        title = rng.choice(vg[lang]["titles"])
        main = rng.choice(vg[lang]["sentences"])
    else:
        title, main = bank[lang][bundle_idx]
    extras: list[str] = []
    if rng.random() < 0.45:
        extras.append(rng.choice(ctx["time"][lang]))
    if rng.random() < 0.60:
        extras.append(rng.choice(ctx["location"][lang]).format(district=district))
    if rng.random() < 0.40:
        if budget["type"] == "Range":
            extras.append(
                rng.choice([s for s in ctx["budget"][lang] if "{min}" in s or "{max}" in s]).format(
                    min=budget["min"], max=budget["max"]
                )
            )
        elif budget["type"] == "Fixed":
            extras.append(f"{budget['max']} AZN.")
        else:
            extras.append(rng.choice([s for s in ctx["budget"][lang] if "{" not in s]))
    rng.shuffle(extras)
    cues = ctx["urgency"][lang][urgency]
    sentences = [main]
    if cues and rng.random() < 0.85:
        sentences.insert(1, rng.choice(cues))
    sentences += extras
    if rng.random() < 0.35:
        sentences.append(rng.choice(ctx["request"][lang]))
    return title, " ".join(sentences)


def generate_listings(n_per_type: int = 80, seed: int = 20261023) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    pb = load_phrasebank()
    test_az, test_ru = pb["split"]["test_az_bundle_index"], pb["split"]["test_ru_bundle_index"]
    geo, geo_w = pb["geo"], pb["geo_city_weights"]
    cities, weights = list(geo_w), list(geo_w.values())
    rows: list[dict[str, Any]] = []
    idx = 0
    for code, info in problem_index().items():
        for _ in range(n_per_type):
            idx += 1
            vague = rng.random() < 0.08
            lang = "az" if rng.random() < 0.82 else "ru"
            bundle_idx = rng.randrange(5 if lang == "az" else 2)
            is_test_bundle = bundle_idx == (test_az if lang == "az" else test_ru)
            split = (
                ("test" if rng.random() < 0.3 else "train")
                if vague
                else ("test" if is_test_bundle else "train")
            )
            probs = info["urgency_probs"]
            urgency = rng.choices(URGENCIES, weights=[probs[u] for u in URGENCIES])[0]
            city = rng.choices(cities, weights=weights)[0]
            district = rng.choice(geo[city])
            budget = _budget(info["price_azn"], rng)
            title, desc = _compose(
                code, lang, vague, bundle_idx, urgency, budget, city, district, rng
            )
            flags = {
                "strip": rng.random() < 0.30,
                "typo": rng.random() < 0.12,
                "bang": rng.random() < 0.05,
                "case": rng.choices(["keep", "lower", "upper"], weights=[0.82, 0.15, 0.03])[0],
            }
            title, desc = _noise(title, flags, rng), _noise(desc, flags, rng)
            created = AS_OF - timedelta(seconds=rng.randint(0, 365 * 86400))
            rows.append(
                {
                    "listing_id": str(uuid.uuid5(NAMESPACE, f"listing:{seed}:{idx}")),
                    "created_at": created.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "language": lang,
                    "text_quality": "vague" if vague else "clear",
                    "title": title,
                    "description": desc,
                    "problem_details": _details(info["category"], code, rng),
                    "urgency": urgency,
                    "city": city,
                    "district": district,
                    "budget": budget,
                    "photos": [],
                    "labels": {
                        "category": info["category"],
                        "problem_type": code,
                        "skills": list(info["skills"]),
                        "risk_flags": list(info["risk_flags"]),
                    },
                    "split": split,
                    "bundle": None if vague else f"{lang}{bundle_idx}",
                    "noise": {k: v for k, v in flags.items() if v not in (False, "keep")},
                }
            )
    return rows


def generate_masters(n: int = 400, seed: int = 20261023) -> list[dict[str, Any]]:
    rng = random.Random(f"masters:{seed}")
    cats = load_taxonomy()["categories"]
    pb = load_phrasebank()
    geo, geo_w = pb["geo"], pb["geo_city_weights"]
    out = []
    for i in range(n):
        main = rng.choice(cats)
        skills = [
            s["code"]
            for s in rng.sample(main["skills"], k=min(len(main["skills"]), rng.randint(2, 5)))
        ]
        if rng.random() < 0.25:
            other = rng.choice([c for c in cats if c is not main])
            skills += [
                s["code"]
                for s in rng.sample(other["skills"], k=min(len(other["skills"]), rng.randint(1, 2)))
            ]
        years = min(40, int(rng.gammavariate(2.2, 3.2)))
        count = int(rng.expovariate(1 / 18))
        rating = round(min(5.0, max(1.0, rng.gauss(4.35, 0.45))), 2) if count > 0 else 0.0
        city = rng.choices(list(geo_w), weights=list(geo_w.values()))[0]
        districts = rng.sample(
            geo[city], k=min(len(geo[city]), rng.randint(1, 4 if city == "Bakı" else 2))
        )
        out.append(
            {
                "master_id": str(uuid.uuid5(NAMESPACE, f"master:{seed}:{i}")),
                "main_category": main["slug"],
                "skills": skills,
                "years_experience": years,
                "average_rating": rating,
                "rating_count": count,
                "completed_jobs_count": count + int(rng.expovariate(1 / 10)),
                "verification_status": rng.choices(
                    ["Verified", "Pending", "Unverified", "Rejected"],
                    weights=[0.45, 0.15, 0.35, 0.05],
                )[0],
                "is_available": rng.random() < 0.85,
                "accepts_emergency_jobs": rng.random() < 0.30,
                "service_areas": [{"city": city, "district": d} for d in districts],
            }
        )
    return out


def _write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    with path.open(
        "w", encoding="utf-8-sig", newline=""
    ) as f:  # BOM so Excel on Windows shows ə ı ş correctly
        w = csv.DictWriter(f, fieldnames=columns)
        w.writeheader()
        w.writerows(rows)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_dataset(
    out: Path, n_per_type: int = 80, n_masters: int = 400, seed: int = 20261023
) -> dict[str, Any]:
    out.mkdir(parents=True, exist_ok=True)
    listings = generate_listings(n_per_type, seed)
    masters = generate_masters(n_masters, seed)
    with (out / "listings.jsonl").open("w", encoding="utf-8", newline="\n") as f:
        for r in listings:
            f.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")
    flat = [
        {
            "listing_id": r["listing_id"],
            "created_at": r["created_at"],
            "language": r["language"],
            "text_quality": r["text_quality"],
            "category": r["labels"]["category"],
            "problem_type": r["labels"]["problem_type"],
            "urgency": r["urgency"],
            "city": r["city"],
            "district": r["district"],
            "budget_min": r["budget"]["min"],
            "budget_max": r["budget"]["max"],
            "budget_type": r["budget"]["type"],
            "n_photos": len(r["photos"]),
            "photo_paths": json.dumps(r["photos"], ensure_ascii=False),
            "title": r["title"],
            "description": r["description"],
            "split": r["split"],
        }
        for r in listings
    ]
    _write_csv(out / "listings.csv", flat, list(flat[0]))
    mflat = [
        {
            **m,
            "skills": json.dumps(m["skills"]),
            "service_areas": json.dumps(m["service_areas"], ensure_ascii=False),
        }
        for m in masters
    ]
    _write_csv(out / "masters.csv", mflat, list(mflat[0]))
    stats = {
        "seed": seed,
        "n_listings": len(listings),
        "n_masters": len(masters),
        "by_split": dict(Counter(r["split"] for r in listings)),
        "by_text_quality": dict(Counter(r["text_quality"] for r in listings)),
        "by_language": dict(Counter(r["language"] for r in listings)),
        "by_category": dict(Counter(r["labels"]["category"] for r in listings)),
    }
    files = {n: _sha256(out / n) for n in ("listings.jsonl", "listings.csv", "masters.csv")}
    (out / "manifest.json").write_text(
        json.dumps({"stats": stats, "sha256": files}, indent=1, ensure_ascii=False),
        encoding="utf-8",
    )
    (out / "DATASET_CARD.md").write_text(_card(stats), encoding="utf-8")
    return stats


def _card(s: dict[str, Any]) -> str:
    return f"""# Tapdix synthetic dataset v1

Generated by `python -m tapdix_ml.data.generate` (seed {s["seed"]}). **Synthetic - not real customers.**

| | |
|---|---|
| listings | {s["n_listings"]} ({s["by_split"]}) |
| masters | {s["n_masters"]} |
| languages | {s["by_language"]} |
| text quality | {s["by_text_quality"]} (`vague` = text too thin to classify; meant to trigger the photo fallback) |
| categories | {len(s["by_category"])} groups x 7 problem types |

## How it is built
* Text = hand-written Azerbaijani/Russian phrasings (`ml/data/taxonomy/phrasebank.json`) + random time / location /
  budget / urgency sentences + noise (diacritics stripped, typos, lower/UPPER case).
* **Train/test are split by phrasing**: test listings use phrasings the model never saw in training
  (so the test measures generalisation across wording, not memorisation).
* `photos` is empty everywhere: no real photos exist yet. Put photos in
  `ml/data/images/<category>/<problem_type>/` and run `python -m tapdix_ml.data.index_photos`.

## What this data is NOT
* Not evidence of real-world accuracy: real users write messier text. Always check the independent
  `ml/data/gold/gold.json` and, later, real listings.
* Prices, ratings and names of areas' demand are invented; do not use them for pricing decisions.
* Labels here are ground truth by construction; real labels will be noisy.
"""


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--out", type=Path, default=Path("ml/data/synthetic"))
    ap.add_argument("--n-per-type", type=int, default=80)
    ap.add_argument("--n-masters", type=int, default=400)
    ap.add_argument("--seed", type=int, default=20261023)
    a = ap.parse_args()
    print(
        json.dumps(
            write_dataset(a.out, a.n_per_type, a.n_masters, a.seed), indent=1, ensure_ascii=False
        )
    )


if __name__ == "__main__":
    main()
