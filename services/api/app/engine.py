"""Loads the text model and the masters once and keeps them in memory."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from tapdix_ml.demo import DEFAULT_MASTERS, load_or_train
from tapdix_ml.matching import Master
from tapdix_ml.nlp.classifier import ListingClassifier
from tapdix_ml.pipeline import load_masters


@dataclass(frozen=True)
class Engine:
    model: ListingClassifier
    masters: list[Master]

    @property
    def by_id(self) -> dict[str, Master]:
        return {m.master_id: m for m in self.masters}


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    """Trains the model on first use (about 15 s) and caches it in ml/models/ for later runs."""
    return Engine(model=load_or_train(), masters=load_masters(DEFAULT_MASTERS))
