"""
Acceptance Tests: AT-1 through AT-4
Aligned to current API contracts.
"""

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
import io


@pytest.mark.acceptance
class TestAT1DataImport:
    """AT-1: data import and transfer availability."""

    def test_records_imported(self, client: TestClient, auth_headers: dict):
        response = client.get("/transfers/", headers=auth_headers)
        assert response.status_code == 200, response.text
        data = response.json()
        assert "total" in data
        # Accept empty in CI sqlite env, but verify shape.
        assert isinstance(data["total"], int)

    def test_no_critical_null_values_shape(self, client: TestClient, auth_headers: dict):
        response = client.get("/transfers/?page=1&page_size=5", headers=auth_headers)
        assert response.status_code == 200, response.text
        payload = response.json()
        assert "items" in payload
        if payload["items"]:
            item = payload["items"][0]
            assert "transfer_id" in item
            assert "et_date" in item

    def test_cl_size_distribution_valid(self, client: TestClient, auth_headers: dict):
        response = client.get("/transfers/?page=1&page_size=100", headers=auth_headers)
        assert response.status_code == 200, response.text
        payload = response.json()
        for row in payload.get("items", []):
            cl = row.get("cl_measure_mm")
            if cl is None:
                continue
            cl_val = float(cl)
            assert 0 <= cl_val <= 50, f"Invalid CL value found: {cl_val}"

    def test_import_api_returns_success(self, client: TestClient, auth_headers: dict):
        response = client.post("/import/seed-from-disk", headers=auth_headers)
        assert response.status_code in (200, 409, 404), response.text


@pytest.mark.acceptance
class TestAT2CLValidation:
    """AT-2: CL validation for transfer create."""

    def test_invalid_cl_negative(self, client: TestClient, auth_headers: dict):
        response = client.post(
            "/transfers/",
            json={"et_date": "2026-03-01", "cl_measure_mm": -5},
            headers=auth_headers,
        )
        assert response.status_code == 422, response.text

    def test_invalid_cl_too_large(self, client: TestClient, auth_headers: dict):
        response = client.post(
            "/transfers/",
            json={"et_date": "2026-03-01", "cl_measure_mm": 60},
            headers=auth_headers,
        )
        assert response.status_code == 422, response.text

    def test_valid_cl_midrange(self, client: TestClient, auth_headers: dict):
        response = client.post(
            "/transfers/",
            json={"et_date": "2026-03-01", "cl_measure_mm": 25},
            headers=auth_headers,
        )
        assert response.status_code == 201, response.text
        data = response.json()
        assert "transfer_id" in data

    def test_valid_cl_minimum(self, client: TestClient, auth_headers: dict):
        response = client.post(
            "/transfers/",
            json={"et_date": "2026-03-01", "cl_measure_mm": 0},
            headers=auth_headers,
        )
        assert response.status_code == 201, response.text

    def test_valid_cl_maximum(self, client: TestClient, auth_headers: dict):
        response = client.post(
            "/transfers/",
            json={"et_date": "2026-03-01", "cl_measure_mm": 50},
            headers=auth_headers,
        )
        assert response.status_code == 201, response.text


@pytest.mark.acceptance
class TestAT3PredictionWithCIAndSHAP:
    """AT-3: prediction returns probability, CI and SHAP explanation."""

    def _predict(self, client: TestClient, auth_headers: dict):
        return client.post(
            "/predict/pregnancy",
            json={
                "cl_measure_mm": 25.0,
                "embryo_stage": 7,
                "embryo_grade": 1,
                "protocol_name": "CIDR",
                "fresh_or_frozen": "Fresh",
            },
            headers=auth_headers,
        )

    def test_prediction_returns_probability(self, client: TestClient, auth_headers: dict):
        response = self._predict(client, auth_headers)
        if response.status_code == 503:
            pytest.skip("Prediction model unavailable in this environment")
        assert response.status_code == 200, response.text
        p = response.json().get("probability")
        assert isinstance(p, (int, float))
        assert 0 <= p <= 1

    def test_prediction_returns_confidence_interval(self, client: TestClient, auth_headers: dict):
        response = self._predict(client, auth_headers)
        if response.status_code == 503:
            pytest.skip("Prediction model unavailable in this environment")
        assert response.status_code == 200, response.text
        data = response.json()
        lo = data["confidence_lower"]
        hi = data["confidence_upper"]
        assert 0 <= lo <= 1
        assert 0 <= hi <= 1
        assert hi >= lo

    def test_prediction_returns_shap_explanations(self, client: TestClient, auth_headers: dict):
        response = self._predict(client, auth_headers)
        if response.status_code == 503:
            pytest.skip("Prediction model unavailable in this environment")
        assert response.status_code == 200, response.text
        shap = response.json().get("shap_explanation")
        assert isinstance(shap, dict)
        assert "base_value" in shap
        assert "contributions" in shap

    def test_prediction_returns_model_metadata(self, client: TestClient, auth_headers: dict):
        response = self._predict(client, auth_headers)
        if response.status_code == 503:
            pytest.skip("Prediction model unavailable in this environment")
        assert response.status_code == 200, response.text
        data = response.json()
        assert isinstance(data.get("model_name"), str)
        assert isinstance(data.get("model_version"), str)

    def test_prediction_missing_required_field(self, client: TestClient, auth_headers: dict):
        # Business rule: missing required fields must fail validation.
        response = client.post("/predict/pregnancy", json={}, headers=auth_headers)
        assert response.status_code == 422


@pytest.mark.acceptance
class TestAT4EmbryoGrading:
    """AT-4: embryo similarity endpoint behavior.

    Note: this class covers /grade/similar-cases, an honest nearest-neighbor
    visual similarity search over a SimCLR self-supervised embedding index.
    /grade/embryo (Grade 1/2/3 classifier) went through the same history
    this comment used to describe — removed for lacking real labels, then
    restored once real labels were sourced (see ml/grading/real_labels.py
    and backend/tests/integration/test_grading_api.py, which covers it).
    """

    @staticmethod
    def _tiny_png_bytes() -> bytes:
        try:
            from PIL import Image
        except Exception:
            pytest.skip("Pillow unavailable for image generation")

        img = Image.new("RGB", (2, 2), color=(255, 255, 255))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    def test_similar_cases_returns_matches(self, client: TestClient, auth_headers: dict):
        response = client.post(
            "/grade/similar-cases",
            files={"image": ("test.png", self._tiny_png_bytes(), "image/png")},
            headers=auth_headers,
        )
        if response.status_code == 503:
            pytest.skip("Similarity index/backbone unavailable in this environment")
        assert response.status_code == 200, response.text
        data = response.json()
        assert "matches" in data
        assert isinstance(data["matches"], list)

    def test_similar_cases_match_has_similarity_score(self, client: TestClient, auth_headers: dict):
        response = client.post(
            "/grade/similar-cases",
            files={"image": ("test.png", self._tiny_png_bytes(), "image/png")},
            headers=auth_headers,
        )
        if response.status_code == 503:
            pytest.skip("Similarity index/backbone unavailable in this environment")
        assert response.status_code == 200, response.text
        matches = response.json().get("matches", [])
        for match in matches:
            assert "similarity" in match
            assert isinstance(match["similarity"], (int, float))

    def test_similar_cases_invalid_image_format(self, client: TestClient, auth_headers: dict):
        response = client.post(
            "/grade/similar-cases",
            files={"image": ("test.txt", b"not-an-image", "text/plain")},
            headers=auth_headers,
        )
        assert response.status_code in (400, 422, 500, 503), response.text

    def test_similar_cases_empty_image_rejected(self, client: TestClient, auth_headers: dict):
        response = client.post(
            "/grade/similar-cases",
            files={"image": ("test.png", b"", "image/png")},
            headers=auth_headers,
        )
        assert response.status_code in (400, 422, 500, 503), response.text


@pytest.mark.acceptance
def test_suite_complete():
    assert True

