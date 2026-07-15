from app.api.transfers import _clean_pregnancy_result


def test_transfer_result_normalization_accepts_known_statuses_only():
    assert _clean_pregnancy_result("Pregnant") == "Pregnant"
    assert _clean_pregnancy_result("positive") == "Pregnant"
    assert _clean_pregnancy_result("O") == "Open"
    assert _clean_pregnancy_result("Pending") == "Recheck"
    assert _clean_pregnancy_result("2025-12-17") is None
    assert _clean_pregnancy_result(None) is None
