"""Listing text -> problem type (-> category), with confidence and word-level explanation.

Model: TF-IDF over character n-grams (robust to Azerbaijani suffixes + typos) and word 1-2grams, fed to a
multinomial logistic regression. Category probability = sum of its problem-type probabilities, so category
and problem type can never contradict each other.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from scipy.sparse import csr_matrix, hstack
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

from tapdix_ml.data.taxonomy import category_of
from tapdix_ml.text.normalize import normalize


def listing_text(title: str, description: str) -> str:
    return f"{title}. {description}"


@dataclass(frozen=True)
class TextPrediction:
    problem_type: str
    problem_prob: float
    category: str
    category_prob: float
    top_k: list[tuple[str, float]] = field(default_factory=list)
    category_probs: dict[str, float] = field(default_factory=dict)
    keywords: list[tuple[str, float]] = field(default_factory=list)


class ListingClassifier:
    def __init__(self, c: float = 20.0, normalize_fn: Callable[[str], str] = normalize) -> None:
        self.c = c
        self.normalize_fn = normalize_fn
        self.char_vec = TfidfVectorizer(
            analyzer="char_wb", ngram_range=(2, 5), sublinear_tf=True, min_df=2
        )
        self.word_vec = TfidfVectorizer(
            analyzer="word", ngram_range=(1, 2), sublinear_tf=True, token_pattern=r"(?u)\b\w\w+\b"
        )
        self.clf = LogisticRegression(C=c, max_iter=3000)
        self.classes_: list[str] = []

    # ------------------------------------------------------------------ training
    def _prep(self, texts: Sequence[str]) -> list[str]:
        return [self.normalize_fn(t) for t in texts]

    def fit(self, texts: Sequence[str], problem_types: Sequence[str]) -> ListingClassifier:
        x = self._prep(texts)
        feats = hstack([self.char_vec.fit_transform(x), self.word_vec.fit_transform(x)]).tocsr()
        self.clf.fit(feats, list(problem_types))
        self.classes_ = [str(c) for c in self.clf.classes_]
        self._cat_index = {
            c: [i for i, p in enumerate(self.classes_) if category_of(p) == c]
            for c in dict.fromkeys(category_of(p) for p in self.classes_)
        }
        return self

    # ------------------------------------------------------------------ inference
    def _features(self, texts: Sequence[str]) -> csr_matrix:
        x = self._prep(texts)
        return hstack([self.char_vec.transform(x), self.word_vec.transform(x)]).tocsr()

    def predict_proba(self, texts: Sequence[str]) -> np.ndarray:
        return self.clf.predict_proba(self._features(texts))

    def category_proba(self, proba: np.ndarray) -> dict[str, np.ndarray]:
        return {c: proba[:, idx].sum(axis=1) for c, idx in self._cat_index.items()}

    def predict(self, text: str, *, top_k: int = 3, n_keywords: int = 5) -> TextPrediction:
        feats = self._features([text])
        proba = self.clf.predict_proba(feats)[0]
        order = np.argsort(-proba)
        best = int(order[0])
        cat_p = {c: float(proba[idx].sum()) for c, idx in self._cat_index.items()}
        cat = max(cat_p, key=lambda k: cat_p[k])
        return TextPrediction(
            problem_type=self.classes_[best],
            problem_prob=float(proba[best]),
            category=cat,
            category_prob=cat_p[cat],
            top_k=[(self.classes_[i], float(proba[i])) for i in order[:top_k]],
            category_probs=dict(sorted(cat_p.items(), key=lambda kv: -kv[1])),
            keywords=self._explain(feats, best, n_keywords),
        )

    def _explain(self, feats: csr_matrix, class_idx: int, k: int) -> list[tuple[str, float]]:
        """Words (not char-grams) that pushed the score of the predicted problem type up."""
        offset = len(self.char_vec.vocabulary_)
        row = feats.getrow(0)
        names = self.word_vec.get_feature_names_out()
        coef = self.clf.coef_[class_idx]
        contrib = {
            int(j) - offset: float(v) * float(coef[int(j)])
            for j, v in zip(row.indices, row.data, strict=True)
            if int(j) >= offset
        }
        top = sorted(((names[j], w) for j, w in contrib.items() if w > 0), key=lambda t: -t[1])[:k]
        return [(w, round(s, 3)) for w, s in top]

    # ------------------------------------------------------------------ persistence
    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump({"model": self, "format": 1}, path)

    @staticmethod
    def load(path: Path) -> ListingClassifier:
        obj: dict[str, Any] = joblib.load(path)
        return obj["model"]
