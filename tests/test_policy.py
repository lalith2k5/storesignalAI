from storesignal.config import load_risk_policy


def test_policy_has_mandatory_categories():
    policy = load_risk_policy()
    cats = [r.category for r in policy.rules]
    assert "allergen_risk" in cats
    assert "hygiene" in cats
    assert "staff_misconduct" in cats
