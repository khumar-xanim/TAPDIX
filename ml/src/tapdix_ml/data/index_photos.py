"""Scan ml/data/images/<category>/<problem_type>/ and write a photo manifest (links for the tabular data).

Folder names MUST be taxonomy codes; unknown folders are reported, never silently indexed.
Run:  python -m tapdix_ml.data.index_photos
"""

from __future__ import annotations

import argparse
import csv
import hashlib
from pathlib import Path

from .taxonomy import DATA_DIR, category_of, problem_codes

EXTS = {".jpg", ".jpeg", ".png", ".webp"}


def index_photos(images_dir: Path) -> tuple[list[dict[str, str]], list[str]]:
    rows, problems, seen = [], [], {}
    valid = set(problem_codes())
    for path in sorted(p for p in images_dir.rglob("*") if p.suffix.lower() in EXTS):
        rel = path.relative_to(images_dir)
        if len(rel.parts) != 3:
            problems.append(f"{rel.as_posix()}: expected <category>/<problem_type>/<file>")
            continue
        cat, code = rel.parts[0], rel.parts[1]
        if code not in valid or category_of(code) != cat:
            problems.append(
                f"{rel.as_posix()}: '{cat}/{code}' is not a valid category/problem_type"
            )
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest in seen:
            problems.append(f"{rel.as_posix()}: duplicate of {seen[digest]}")
            continue
        seen[digest] = rel.as_posix()
        rows.append(
            {
                "photo_id": digest[:16],
                "path": f"images/{rel.as_posix()}",
                "category": cat,
                "problem_type": code,
                "sha256": digest,
                "size_bytes": str(path.stat().st_size),
            }
        )
    return rows, problems


def init_folders(images_dir: Path) -> int:
    """Create images/<category>/<problem_type>/ (+ .gitkeep) for every problem type."""
    n = 0
    for code in problem_codes():
        d = images_dir / category_of(code) / code
        d.mkdir(parents=True, exist_ok=True)
        (d / ".gitkeep").touch()
        n += 1
    return n


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--init", action="store_true", help="create the empty folder skeleton and exit")
    ap.add_argument("--images", type=Path, default=DATA_DIR / "images")
    ap.add_argument("--out", type=Path, default=DATA_DIR / "photos_index.csv")
    a = ap.parse_args()
    a.images.mkdir(parents=True, exist_ok=True)
    if a.init:
        print(f"created {init_folders(a.images)} problem-type folders under {a.images}")
        return
    rows, problems = index_photos(a.images)
    cols = ["photo_id", "path", "category", "problem_type", "sha256", "size_bytes"]
    with a.out.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    print(f"indexed {len(rows)} photos -> {a.out}")
    for p in problems:
        print("  WARN", p)


if __name__ == "__main__":
    main()
