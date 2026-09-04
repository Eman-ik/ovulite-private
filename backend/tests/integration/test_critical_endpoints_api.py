"""Integration tests for critical backend endpoints currently lacking coverage.

These tests are intended to run against a PostgreSQL test database.
Set TEST_DATABASE_URL to a PostgreSQL DSN before running.
"""

from pathlib import Path
import os

import pytest


REQUIRES_POSTGRES = not (os.getenv("TEST_DATABASE_URL", "").startswith("postgresql"))


@pytest.mark.integration
@pytest.mark.skipif(REQUIRES_POSTGRES, reason="Requires PostgreSQL TEST_DATABASE_URL")
def test_donors_crud(client, auth_headers):
    create_payload = {
        "tag_id": "DONOR-AUDIT-001",
        "breed": "Angus",
        "birth_weight_epd": 2.1,
        "notes": "integration audit",
    }

    created = client.post("/donors/", json=create_payload, headers=auth_headers)
    assert created.status_code == 201, created.text
    donor_id = created.json()["donor_id"]

    fetched = client.get(f"/donors/{donor_id}", headers=auth_headers)
    assert fetched.status_code == 200
    assert fetched.json()["tag_id"] == create_payload["tag_id"]

    listed = client.get("/donors/?search=AUDIT-001", headers=auth_headers)
    assert listed.status_code == 200
    assert listed.json()["total"] >= 1

    updated = client.put(
        f"/donors/{donor_id}",
        json={"breed": "Brahman"},
        headers=auth_headers,
    )
    assert updated.status_code == 200
    assert updated.json()["breed"] == "Brahman"

    deleted = client.delete(f"/donors/{donor_id}", headers=auth_headers)
    assert deleted.status_code == 204


@pytest.mark.integration
@pytest.mark.skipif(REQUIRES_POSTGRES, reason="Requires PostgreSQL TEST_DATABASE_URL")
def test_sires_crud(client, auth_headers):
    create_payload = {
        "name": "SIRE-AUDIT-001",
        "breed": "Angus",
        "birth_weight_epd": 1.7,
        "semen_type": "Conventional",
        "notes": "integration audit",
    }

    created = client.post("/sires/", json=create_payload, headers=auth_headers)
    assert created.status_code == 201, created.text
    sire_id = created.json()["sire_id"]

    fetched = client.get(f"/sires/{sire_id}", headers=auth_headers)
    assert fetched.status_code == 200
    assert fetched.json()["name"] == create_payload["name"]

    listed = client.get("/sires/?search=SIRE-AUDIT-001", headers=auth_headers)
    assert listed.status_code == 200
    assert listed.json()["total"] >= 1

    updated = client.put(
        f"/sires/{sire_id}",
        json={"semen_type": "Sexed"},
        headers=auth_headers,
    )
    assert updated.status_code == 200
    assert updated.json()["semen_type"] == "Sexed"

    deleted = client.delete(f"/sires/{sire_id}", headers=auth_headers)
    assert deleted.status_code == 204


@pytest.mark.integration
@pytest.mark.skipif(REQUIRES_POSTGRES, reason="Requires PostgreSQL TEST_DATABASE_URL")
def test_recipients_crud(client, auth_headers):
    create_payload = {
        "tag_id": "RECIP-AUDIT-001",
        "farm_location": "Audit Farm",
        "cow_or_heifer": "Cow",
        "notes": "integration audit",
    }

    created = client.post("/recipients/", json=create_payload, headers=auth_headers)
    assert created.status_code == 201, created.text
    recipient_id = created.json()["recipient_id"]

    fetched = client.get(f"/recipients/{recipient_id}", headers=auth_headers)
    assert fetched.status_code == 200
    assert fetched.json()["tag_id"] == create_payload["tag_id"]

    listed = client.get("/recipients/?search=RECIP-AUDIT-001", headers=auth_headers)
    assert listed.status_code == 200
    assert listed.json()["total"] >= 1

    updated = client.put(
        f"/recipients/{recipient_id}",
        json={"cow_or_heifer": "Heifer"},
        headers=auth_headers,
    )
    assert updated.status_code == 200
    assert updated.json()["cow_or_heifer"] == "Heifer"

    deleted = client.delete(f"/recipients/{recipient_id}", headers=auth_headers)
    assert deleted.status_code == 204


@pytest.mark.integration
@pytest.mark.skipif(REQUIRES_POSTGRES, reason="Requires PostgreSQL TEST_DATABASE_URL")
def test_embryos_crud(client, auth_headers):
    create_payload = {
        "stage": 7,
        "grade": 1,
        "fresh_or_frozen": "Fresh",
        "notes": "integration audit",
    }

    created = client.post("/embryos/", json=create_payload, headers=auth_headers)
    assert created.status_code == 201, created.text
    embryo_id = created.json()["embryo_id"]

    fetched = client.get(f"/embryos/{embryo_id}", headers=auth_headers)
    assert fetched.status_code == 200
    assert fetched.json()["stage"] == 7

    listed = client.get("/embryos/?fresh_or_frozen=Fresh", headers=auth_headers)
    assert listed.status_code == 200
    assert listed.json()["total"] >= 1

    updated = client.put(
        f"/embryos/{embryo_id}",
        json={"grade": 2},
        headers=auth_headers,
    )
    assert updated.status_code == 200
    assert updated.json()["grade"] == 2

    deleted = client.delete(f"/embryos/{embryo_id}", headers=auth_headers)
    assert deleted.status_code == 204


@pytest.mark.integration
@pytest.mark.skipif(REQUIRES_POSTGRES, reason="Requires PostgreSQL TEST_DATABASE_URL")
def test_transfers_crud(client, auth_headers):
    create_payload = {
        "et_date": "2026-03-06",
        "cl_side": "Left",
        "cl_measure_mm": 23.4,
        "pc1_result": "Open",
    }

    created = client.post("/transfers/", json=create_payload, headers=auth_headers)
    assert created.status_code == 201, created.text
    transfer_id = created.json()["transfer_id"]

    fetched = client.get(f"/transfers/{transfer_id}", headers=auth_headers)
    assert fetched.status_code == 200
    assert fetched.json()["cl_side"] == "Left"

    listed = client.get("/transfers/?pc1_result=Open", headers=auth_headers)
    assert listed.status_code == 200
    assert listed.json()["total"] >= 1

    updated = client.put(
        f"/transfers/{transfer_id}",
        json={"pc1_result": "Pregnant"},
        headers=auth_headers,
    )
    assert updated.status_code == 200
    assert updated.json()["pc1_result"] == "Pregnant"

    deleted = client.delete(f"/transfers/{transfer_id}", headers=auth_headers)
    assert deleted.status_code == 204


@pytest.mark.integration
@pytest.mark.skipif(REQUIRES_POSTGRES, reason="Requires PostgreSQL TEST_DATABASE_URL")
def test_import_csv_and_seed_from_disk(client, auth_headers):
    csv_path = Path(__file__).resolve().parents[3] / "docs" / "dataset" / "ET Summary - ET Data.csv"
    assert csv_path.exists(), f"Expected dataset at {csv_path}"

    with open(csv_path, "rb") as f:
        imported = client.post(
            "/import/csv",
            files={"file": ("ET Summary - ET Data.csv", f, "text/csv")},
            headers=auth_headers,
        )

    assert imported.status_code == 200, imported.text
    body = imported.json()
    assert body["rows_ingested"] > 0


@pytest.mark.integration
@pytest.mark.skipif(REQUIRES_POSTGRES, reason="Requires PostgreSQL TEST_DATABASE_URL")
def test_predict_with_real_et_record_payload(client, auth_headers, db_session):
    from sqlalchemy.orm import joinedload

    from app.models.embryo import Embryo
    from app.models.et_transfer import ETTransfer

    transfer = (
        db_session.query(ETTransfer)
        .options(
            joinedload(ETTransfer.embryo).joinedload(Embryo.donor),
            joinedload(ETTransfer.embryo).joinedload(Embryo.sire),
            joinedload(ETTransfer.protocol),
            joinedload(ETTransfer.technician),
        )
        .filter(ETTransfer.embryo_id.isnot(None))
        .first()
    )

    if transfer is None:
        csv_path = Path(__file__).resolve().parents[3] / "docs" / "dataset" / "ET Summary - ET Data.csv"
        assert csv_path.exists(), f"Expected dataset at {csv_path}"
        with open(csv_path, "rb") as f:
            imported = client.post(
                "/import/csv",
                files={"file": ("ET Summary - ET Data.csv", f, "text/csv")},
                headers=auth_headers,
            )
        assert imported.status_code in (200, 409), imported.text

        transfer = (
            db_session.query(ETTransfer)
            .options(
                joinedload(ETTransfer.embryo).joinedload(Embryo.donor),
                joinedload(ETTransfer.embryo).joinedload(Embryo.sire),
                joinedload(ETTransfer.protocol),
                joinedload(ETTransfer.technician),
            )
            .filter(ETTransfer.embryo_id.isnot(None))
            .first()
        )

    assert transfer is not None, "Expected imported ET transfers to exist"

    embryo = transfer.embryo
    donor = embryo.donor if embryo else None
    sire = embryo.sire if embryo else None

    payload = {
        "transfer_id": transfer.transfer_id,
        "cl_measure_mm": float(transfer.cl_measure_mm) if transfer.cl_measure_mm is not None else None,
        "embryo_stage": embryo.stage if embryo else None,
        "embryo_grade": embryo.grade if embryo else None,
        "heat_day": transfer.heat_day,
        "donor_bw_epd": float(donor.birth_weight_epd) if donor and donor.birth_weight_epd is not None else None,
        "sire_bw_epd": float(sire.birth_weight_epd) if sire and sire.birth_weight_epd is not None else None,
        "days_opu_to_et": (transfer.et_date - embryo.opu_date).days if embryo and embryo.opu_date and transfer.et_date else None,
        "bc_score": float(transfer.bc_score) if transfer.bc_score is not None else None,
        "cl_side": transfer.cl_side,
        "protocol_name": transfer.protocol.name if transfer.protocol else None,
        "fresh_or_frozen": embryo.fresh_or_frozen if embryo else None,
        "technician_name": transfer.technician.name if transfer.technician else None,
        "donor_breed": donor.breed if donor else None,
        "semen_type": sire.semen_type if sire else None,
        "customer_id": transfer.customer_id,
    }

    response = client.post("/predict/pregnancy", json=payload, headers=auth_headers)
    assert response.status_code in (200, 503), response.text

    if response.status_code == 200:
        body = response.json()
        assert "probability" in body
        assert "confidence_lower" in body
        assert "confidence_upper" in body
        assert "risk_band" in body
        assert "shap_explanation" in body


@pytest.mark.integration
@pytest.mark.skipif(REQUIRES_POSTGRES, reason="Requires PostgreSQL TEST_DATABASE_URL")
def test_analytics_and_qc_endpoints_smoke(client, auth_headers):
    run_analytics = client.post("/analytics/run", headers=auth_headers)
    assert run_analytics.status_code == 200, run_analytics.text

    for endpoint in [
        "/analytics/kpis",
        "/analytics/trends",
        "/analytics/funnel",
        "/analytics/protocols",
        "/analytics/donors",
        "/analytics/breeds",
        "/analytics/biomarkers",
    ]:
        resp = client.get(endpoint, headers=auth_headers)
        assert resp.status_code == 200, f"{endpoint} failed: {resp.text}"

    run_qc = client.post("/qc/run", headers=auth_headers)
    assert run_qc.status_code == 200, run_qc.text

    anomalies = client.get("/qc/anomalies", headers=auth_headers)
    charts = client.get("/qc/charts", headers=auth_headers)
    assert anomalies.status_code == 200, anomalies.text
    assert charts.status_code == 200, charts.text


@pytest.mark.integration
@pytest.mark.skipif(REQUIRES_POSTGRES, reason="Requires PostgreSQL TEST_DATABASE_URL")
def test_predict_pregnancy_endpoint(client, auth_headers):
    payload = {
        "cl_measure_mm": 22.5,
        "embryo_stage": 7,
        "embryo_grade": 1,
        "protocol_name": "CIDR",
        "fresh_or_frozen": "Fresh",
    }

    response = client.post("/predict/pregnancy", json=payload, headers=auth_headers)

    # 200: model available and prediction succeeded
    # 503: model artifacts missing in environment (expected on fresh setup)
    assert response.status_code in (200, 503), response.text
    if response.status_code == 503:
        assert "model" in response.text.lower()


@pytest.mark.integration
def test_grade_similar_cases_rejects_invalid_content_type(client, auth_headers):
    # This covers /grade/similar-cases (SimCLR embedding nearest-neighbor
    # search); /grade/embryo (Grade 1/2/3 classifier) is covered separately
    # in test_grading_api.py — see backend/app/api/grading.py's module
    # docstring for the history of both endpoints.
    response = client.post(
        "/grade/similar-cases",
        files={"image": ("not-image.txt", b"hello", "text/plain")},
        headers=auth_headers,
    )
    assert response.status_code == 400
