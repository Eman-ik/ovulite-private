"""Integration tests for embryo grading/similarity API endpoints.

/grade/embryo and /grade/embryo-with-heatmap were removed in an earlier
version of this API (the classifier had never been trained on real labels)
and /grade/similar-cases was added as an honest replacement (nearest-
neighbor visual similarity, no labels required). Real grade labels for
these exact 482 images were subsequently sourced from a published dataset
(Rocha et al. 2017, see docs/dataset/external/rocha2017_bovine_blastocyst/
DATASET_CARD.md) and a classifier trained on them
(ml/grading/train_real_grading.py) — /grade/embryo and
/grade/embryo-with-heatmap are tested here again, now backed by that real
model. /grade/similar-cases remains available as a complementary tool.
"""

import io
import os
from pathlib import Path

import pytest


REQUIRES_POSTGRES = os.getenv("TEST_DATABASE_URL") is None


@pytest.mark.integration
def test_grading_model_info(client, auth_headers):
    """Test GET /grade/model-info endpoint."""
    response = client.get("/grade/model-info", headers=auth_headers)

    assert response.status_code == 200, response.text
    body = response.json()
    assert "model_type" in body
    assert "backbone" in body
    assert "trained" in body
    assert body["backbone"] == "efficientnet_b0"
    # No grade-classifier fields should be present anymore.
    assert "n_grades" not in body
    assert "grade_labels" not in body


@pytest.mark.integration
def test_grade_embryo_with_real_image(client, auth_headers):
    """Test POST /grade/embryo against a real embryo image."""
    image_dir = Path(__file__).resolve().parents[3] / "docs" / "Blastocystimages" / "Blastocyst images"

    if not image_dir.exists():
        pytest.skip(f"Embryo images not found at {image_dir}")

    images = list(image_dir.glob("*.jpg"))
    if not images:
        pytest.skip("No JPEG images found in Blastocyst images directory")

    test_image = images[0]

    with open(test_image, "rb") as f:
        files = {"image": (test_image.name, f, "image/jpeg")}
        response = client.post("/grade/embryo", files=files, headers=auth_headers)

    # 200: classifier artifact available and prediction succeeded
    # 503: classifier not trained/available in this environment
    assert response.status_code in (200, 503), response.text

    if response.status_code == 200:
        body = response.json()
        assert body["predicted_grade"] in (1, 2, 3)
        assert 0.0 <= body["confidence"] <= 1.0
        assert len(body["probabilities"]) == 3
        assert abs(sum(p["probability"] for p in body["probabilities"]) - 1.0) < 1e-3
        assert body["heatmap_available"] is True
        assert len(body["caveats"]) > 0


@pytest.mark.integration
def test_grade_embryo_rejects_invalid_image(client, auth_headers):
    """Reject malformed bytes even if MIME type claims JPEG."""
    malformed = b"not-a-real-jpeg"
    files = {"image": ("fake.jpg", io.BytesIO(malformed), "image/jpeg")}

    response = client.post("/grade/embryo", files=files, headers=auth_headers)
    assert response.status_code == 400
    assert "invalid image" in response.text.lower()


@pytest.mark.integration
def test_grade_embryo_with_heatmap(client, auth_headers):
    """Test POST /grade/embryo-with-heatmap returns a Grad-CAM overlay image."""
    image_dir = Path(__file__).resolve().parents[3] / "docs" / "Blastocystimages" / "Blastocyst images"

    if not image_dir.exists():
        pytest.skip(f"Embryo images not found at {image_dir}")

    images = list(image_dir.glob("*.jpg"))
    if not images:
        pytest.skip("No JPEG images found in Blastocyst images directory")

    test_image = images[0]

    with open(test_image, "rb") as f:
        files = {"image": (test_image.name, f, "image/jpeg")}
        response = client.post("/grade/embryo-with-heatmap", files=files, headers=auth_headers)

    assert response.status_code in (200, 503), response.text

    if response.status_code == 200:
        import base64

        body = response.json()
        assert body["predicted_grade"] in (1, 2, 3)
        heatmap_bytes = base64.b64decode(body["heatmap_image_base64"])
        # JPEG magic bytes
        assert heatmap_bytes[:2] == b"\xff\xd8"
        assert len(heatmap_bytes) > 100


@pytest.mark.integration
def test_similar_cases_requires_image(client, auth_headers):
    """Test that /grade/similar-cases rejects requests without an image."""
    response = client.post("/grade/similar-cases", headers=auth_headers)
    assert response.status_code == 422  # FastAPI validation error


@pytest.mark.integration
def test_similar_cases_rejects_invalid_content_type(client, auth_headers):
    """Test that /grade/similar-cases rejects non-image files."""
    fake_text = b"This is not an image"
    files = {"image": ("test.txt", io.BytesIO(fake_text), "text/plain")}

    response = client.post("/grade/similar-cases", files=files, headers=auth_headers)
    assert response.status_code == 400
    assert "invalid image" in response.text.lower()


@pytest.mark.integration
def test_similar_cases_rejects_invalid_image_bytes(client, auth_headers):
    """Reject malformed bytes even if the MIME type claims JPEG."""
    malformed = b"not-a-real-jpeg"
    files = {"image": ("fake.jpg", io.BytesIO(malformed), "image/jpeg")}

    response = client.post("/grade/similar-cases", files=files, headers=auth_headers)
    assert response.status_code == 400
    assert "invalid image" in response.text.lower()


@pytest.mark.integration
def test_similar_cases_rejects_empty_image(client, auth_headers):
    """Test that /grade/similar-cases rejects empty image files."""
    files = {"image": ("empty.jpg", io.BytesIO(b""), "image/jpeg")}

    response = client.post("/grade/similar-cases", files=files, headers=auth_headers)
    assert response.status_code == 400
    assert "empty" in response.text.lower()


@pytest.mark.integration
def test_similar_cases_with_real_image(client, auth_headers):
    """Test similarity search against a real embryo image."""
    image_dir = Path(__file__).resolve().parents[3] / "docs" / "Blastocystimages" / "Blastocyst images"

    if not image_dir.exists():
        pytest.skip(f"Embryo images not found at {image_dir}")

    images = list(image_dir.glob("*.jpg"))
    if not images:
        pytest.skip("No JPEG images found in Blastocyst images directory")

    test_image = images[0]

    with open(test_image, "rb") as f:
        files = {"image": (test_image.name, f, "image/jpeg")}
        data = {"k": "5"}

        response = client.post("/grade/similar-cases", files=files, data=data, headers=auth_headers)

    # 200: similarity index available and search succeeded
    # 503: similarity index/backbone not built yet in this environment
    assert response.status_code in (200, 503), response.text

    if response.status_code == 200:
        body = response.json()
        assert "matches" in body
        assert "n_index_cases" in body
        assert "model_type" in body
        assert isinstance(body["matches"], list)
        assert len(body["matches"]) <= 5

        for match in body["matches"]:
            assert "rank" in match
            assert "filename" in match
            assert "similarity" in match
            assert "metadata" in match
            assert -1.0 <= match["similarity"] <= 1.0


@pytest.mark.integration
@pytest.mark.skipif(REQUIRES_POSTGRES, reason="Requires PostgreSQL TEST_DATABASE_URL")
def test_upload_embryo_image(client, auth_headers):
    """Test /grade/upload endpoint for image storage."""
    image_dir = Path(__file__).resolve().parents[3] / "docs" / "Blastocystimages" / "Blastocyst images"

    if not image_dir.exists():
        pytest.skip(f"Embryo images not found at {image_dir}")

    images = list(image_dir.glob("*.jpg"))
    if not images:
        pytest.skip("No JPEG images found")

    test_image = images[0]

    with open(test_image, "rb") as f:
        files = {"image": (test_image.name, f, "image/jpeg")}
        data = {"notes": "Integration test upload"}
        response = client.post("/grade/upload", files=files, data=data, headers=auth_headers)

    assert response.status_code == 200, response.text

    body = response.json()
    assert "image_id" in body
    assert "file_path" in body
    assert body["image_id"] > 0
    assert "uploads/embryo_images" in body["file_path"]

    # Check file was actually created
    project_root = Path(__file__).resolve().parents[3]
    uploaded_file = project_root / body["file_path"]
    assert uploaded_file.exists(), f"Uploaded file not found at {uploaded_file}"


@pytest.mark.integration
def test_upload_rejects_oversized_image(client, auth_headers):
    """Test that upload endpoint rejects images over 10MB."""
    # Create a fake 11MB file
    fake_large = io.BytesIO(b"x" * (11 * 1024 * 1024))
    files = {"image": ("large.jpg", fake_large, "image/jpeg")}

    response = client.post("/grade/upload", files=files, headers=auth_headers)
    assert response.status_code in (400, 413)


@pytest.mark.integration
def test_upload_rejects_invalid_image_bytes(client, auth_headers):
    """Reject malformed bytes even if MIME type is image/jpeg."""
    malformed = b"not-a-real-jpeg"
    files = {"image": ("fake.jpg", io.BytesIO(malformed), "image/jpeg")}

    response = client.post("/grade/upload", files=files, headers=auth_headers)
    assert response.status_code == 400
    assert "invalid image" in response.text.lower()


@pytest.mark.integration
def test_similar_cases_size_limit(client, auth_headers):
    """Test that the similarity endpoint rejects oversized images."""
    fake_large = io.BytesIO(b"x" * (11 * 1024 * 1024))
    files = {"image": ("large.jpg", fake_large, "image/jpeg")}

    response = client.post("/grade/similar-cases", files=files, headers=auth_headers)
    assert response.status_code in (400, 413, 422)
