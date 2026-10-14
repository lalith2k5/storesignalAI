from storesignal.ingestion.pipeline import normalize_text, parse_timestamp


def test_emoji_preserved_as_token():
    out = normalize_text("bad food 😡", True)
    assert "angry_face" in out


def test_negation_preserved():
    out = normalize_text("not good at all", True)
    assert "not" in out


def test_pii_redacted():
    out = normalize_text("call me at 9876543210", True)
    assert "[PHONE]" in out


def test_malformed_timestamp_flagged():
    _, bad = parse_timestamp("not-a-date")
    assert bad is True
