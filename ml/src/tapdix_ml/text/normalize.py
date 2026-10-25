"""Text normalisation for Azerbaijani / Russian listings.

Why this exists:
  * Python/JS ``lower()`` is NOT Azerbaijani-aware (``I`` -> ``i`` instead of ``ı``).
  * Many users type without diacritics (``kondisioner soyutmur`` / ``paltaryuyan sixmir``), so we fold
    ``ə ı ö ü ç ş ğ`` to ASCII on BOTH training and inference text - the two spellings then look identical.
  * Listings may contain phone numbers / e-mails; these are redacted before any text is used for ML.
"""

from __future__ import annotations

import re
import unicodedata

_FOLD = str.maketrans(
    {"ə": "e", "ı": "i", "ö": "o", "ü": "u", "ç": "c", "ş": "s", "ğ": "g", "ё": "е"}
)
_PHONE = re.compile(r"(?<![\w])\+?\d[\d\s().-]{6,}\d(?![\w])")
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_REPEAT = re.compile(r"(.)\1{2,}")
_SPACE = re.compile(r"\s+")


def az_lower(text: str) -> str:
    """Lower-case with Azerbaijani rules (İ -> i, I -> ı)."""
    return text.replace("İ", "i").replace("I", "ı").lower()


def fold_diacritics(text: str) -> str:
    return text.translate(_FOLD)


def redact_pii(text: str) -> str:
    text = _EMAIL.sub(" emailaddr ", text)
    return _PHONE.sub(" phonenum ", text)


def normalize(text: str, *, fold: bool = True, redact: bool = True) -> str:
    text = unicodedata.normalize("NFKC", text)
    if redact:
        text = redact_pii(text)
    text = az_lower(text)
    if fold:
        text = fold_diacritics(text)
    text = _REPEAT.sub(r"\1\1", text)  # "təciliiiii" -> "təcilii"
    return _SPACE.sub(" ", text).strip()
