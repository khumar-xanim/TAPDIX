from tapdix_ml.text.normalize import az_lower, fold_diacritics, normalize, redact_pii


def test_az_lower_uses_azerbaijani_rules() -> None:
    assert az_lower("BAKI") == "bakı"  # I -> ı (plain lower() gives 'baki')
    assert az_lower("İstanbul") == "istanbul"  # İ -> i (plain lower() leaves a combining dot)


def test_diacritic_spellings_become_identical() -> None:
    assert normalize("Paltaryuyan sıxmır, çox səs salır") == normalize(
        "paltaryuyan sixmir, cox ses salir"
    )


def test_fold_maps_all_azerbaijani_letters() -> None:
    assert fold_diacritics("əıöüçşğ") == "eioucsg"


def test_pii_is_redacted_but_budgets_and_sizes_survive() -> None:
    text = "Zəng edin +994 50 123 45 67 və ya 050-123-45-67, mail: ali@example.com. Büdcə 20-80 AZN, 12 kv.m"
    out = redact_pii(text)
    assert "123" not in out and "@" not in out
    assert "20-80 AZN" in out and "12 kv.m" in out


def test_repeated_letters_are_collapsed() -> None:
    assert normalize("təcilııııı lazımdır") == "tecilii lazimdir"
