"""Run a real-DB API audit for critical Ovulite endpoints.

Usage (PowerShell):
  cd backend
  python scripts/api_audit_runner.py
"""

from __future__ import annotations

import io
import os
import sys
from pathlib import Path
from typing import Any

import psycopg2
from fastapi.testclient import TestClient


AUDIT_DB = "ovulite_api_audit"
AUDIT_DB_URL = f"postgresql://ovulite:ovulite_dev_password@localhost:5432/{AUDIT_DB}"
BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATASET_PATH = PROJECT_ROOT / "docs" / "dataset" / "ET Summary - ET Data.csv"

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


def ensure_audit_database() -> None:
    conn = psycopg2.connect(
        host="localhost",
        port=5432,
        user="ovulite",
        password="ovulite_dev_password",
        dbname="postgres",
    )
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (AUDIT_DB,))
            exists = cur.fetchone() is not None
            if not exists:
                cur.execute(f'CREATE DATABASE "{AUDIT_DB}"')
    finally:
        conn.close()


def setup_schema() -> None:
    os.environ["DATABASE_URL"] = AUDIT_DB_URL

    from app.database import Base, engine
    import app.models.user
    import app.models.donor
    import app.models.sire
    import app.models.recipient
    import app.models.technician
    import app.models.protocol
    import app.models.embryo
    import app.models.et_transfer
    import app.models.prediction
    import app.models.protocol_log

    Base.metadata.create_all(bind=engine)


def call(client: TestClient, method: str, path: str, **kwargs: Any) -> tuple[int, Any]:
    response = client.request(method, path, **kwargs)
    try:
        body = response.json()
    except Exception:
        body = response.text
    return response.status_code, body


def main() -> None:
    ensure_audit_database()
    setup_schema()

    from app.main import app

    results: dict[str, tuple[int, str]] = {}

    with TestClient(app) as client:
        status, body = call(client, "POST", "/auth/seed")
        results["auth/seed"] = (status, "ok" if status in (200, 201, 409) else str(body))

        status, body = call(
            client,
            "POST",
            "/auth/login",
            data={"username": "admin", "password": "ovulite2026"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        token = body.get("access_token") if isinstance(body, dict) else None
        results["auth/login"] = (status, "ok" if status == 200 and token else str(body))

        headers = {"Authorization": f"Bearer {token}"} if token else {}

        status, body = call(client, "GET", "/auth/me", headers=headers)
        results["auth/me"] = (status, "ok" if status == 200 else str(body))

        if not DATASET_PATH.exists():
            results["import/csv"] = (0, f"dataset missing at {DATASET_PATH}")
        else:
            with open(DATASET_PATH, "rb") as f:
                status, body = call(
                    client,
                    "POST",
                    "/import/csv",
                    headers=headers,
                    files={"file": (DATASET_PATH.name, f, "text/csv")},
                )
            results["import/csv"] = (status, "ok" if status in (200, 409) else str(body))

        donor_payload = {
            "tag_id": "AUDIT-DONOR-001",
            "breed": "Angus",
            "birth_weight_epd": 2.2,
            "notes": "audit",
        }
        status, body = call(client, "POST", "/donors/", headers=headers, json=donor_payload)
        donor_id = body.get("donor_id") if isinstance(body, dict) else None
        results["donors/create"] = (status, "ok" if status in (201, 409) else str(body))
        if donor_id:
            status, body = call(client, "GET", f"/donors/{donor_id}", headers=headers)
            results["donors/get"] = (status, "ok" if status == 200 else str(body))
            status, body = call(client, "PUT", f"/donors/{donor_id}", headers=headers, json={"breed": "Brahman"})
            results["donors/update"] = (status, "ok" if status == 200 else str(body))
            status, body = call(client, "DELETE", f"/donors/{donor_id}", headers=headers)
            results["donors/delete"] = (status, "ok" if status == 204 else str(body))

        sire_payload = {
            "name": "AUDIT-SIRE-001",
            "breed": "Angus",
            "semen_type": "Conventional",
            "notes": "audit",
        }
        status, body = call(client, "POST", "/sires/", headers=headers, json=sire_payload)
        sire_id = body.get("sire_id") if isinstance(body, dict) else None
        results["sires/create"] = (status, "ok" if status == 201 else str(body))
        if sire_id:
            status, body = call(client, "GET", f"/sires/{sire_id}", headers=headers)
            results["sires/get"] = (status, "ok" if status == 200 else str(body))
            status, body = call(client, "PUT", f"/sires/{sire_id}", headers=headers, json={"semen_type": "Sexed"})
            results["sires/update"] = (status, "ok" if status == 200 else str(body))
            status, body = call(client, "DELETE", f"/sires/{sire_id}", headers=headers)
            results["sires/delete"] = (status, "ok" if status == 204 else str(body))

        recipient_payload = {
            "tag_id": "AUDIT-RECIP-001",
            "farm_location": "Audit Farm",
            "cow_or_heifer": "Cow",
            "notes": "audit",
        }
        status, body = call(client, "POST", "/recipients/", headers=headers, json=recipient_payload)
        recipient_id = body.get("recipient_id") if isinstance(body, dict) else None
        results["recipients/create"] = (status, "ok" if status == 201 else str(body))
        if recipient_id:
            status, body = call(client, "GET", f"/recipients/{recipient_id}", headers=headers)
            results["recipients/get"] = (status, "ok" if status == 200 else str(body))
            status, body = call(client, "PUT", f"/recipients/{recipient_id}", headers=headers, json={"cow_or_heifer": "Heifer"})
            results["recipients/update"] = (status, "ok" if status == 200 else str(body))
            status, body = call(client, "DELETE", f"/recipients/{recipient_id}", headers=headers)
            results["recipients/delete"] = (status, "ok" if status == 204 else str(body))

        embryo_payload = {"stage": 7, "grade": 1, "fresh_or_frozen": "Fresh", "notes": "audit"}
        status, body = call(client, "POST", "/embryos/", headers=headers, json=embryo_payload)
        embryo_id = body.get("embryo_id") if isinstance(body, dict) else None
        results["embryos/create"] = (status, "ok" if status == 201 else str(body))
        if embryo_id:
            status, body = call(client, "GET", f"/embryos/{embryo_id}", headers=headers)
            results["embryos/get"] = (status, "ok" if status == 200 else str(body))
            status, body = call(client, "PUT", f"/embryos/{embryo_id}", headers=headers, json={"grade": 2})
            results["embryos/update"] = (status, "ok" if status == 200 else str(body))
            status, body = call(client, "DELETE", f"/embryos/{embryo_id}", headers=headers)
            results["embryos/delete"] = (status, "ok" if status == 204 else str(body))

        transfer_payload = {
            "et_date": "2026-03-06",
            "cl_side": "Left",
            "cl_measure_mm": 23.1,
            "pc1_result": "Open",
        }
        status, body = call(client, "POST", "/transfers/", headers=headers, json=transfer_payload)
        transfer_id = body.get("transfer_id") if isinstance(body, dict) else None
        results["transfers/create"] = (status, "ok" if status == 201 else str(body))
        if transfer_id:
            status, body = call(client, "GET", f"/transfers/{transfer_id}", headers=headers)
            results["transfers/get"] = (status, "ok" if status == 200 else str(body))
            status, body = call(client, "PUT", f"/transfers/{transfer_id}", headers=headers, json={"pc1_result": "Pregnant"})
            results["transfers/update"] = (status, "ok" if status == 200 else str(body))
            status, body = call(client, "DELETE", f"/transfers/{transfer_id}", headers=headers)
            results["transfers/delete"] = (status, "ok" if status == 204 else str(body))

        status, body = call(client, "POST", "/qc/run", headers=headers)
        results["qc/run"] = (status, "ok" if status == 200 else str(body))
        for endpoint in ["/qc/anomalies", "/qc/charts"]:
            status, body = call(client, "GET", endpoint, headers=headers)
            results[endpoint.lstrip("/")] = (status, "ok" if status == 200 else str(body))

        status, body = call(client, "POST", "/analytics/run", headers=headers)
        results["analytics/run"] = (status, "ok" if status == 200 else str(body))
        for endpoint in [
            "/analytics/kpis",
            "/analytics/trends",
            "/analytics/funnel",
            "/analytics/protocols",
            "/analytics/donors",
            "/analytics/breeds",
            "/analytics/biomarkers",
        ]:
            status, body = call(client, "GET", endpoint, headers=headers)
            results[endpoint.lstrip("/")] = (status, "ok" if status == 200 else str(body))

        predict_payload = {
            "cl_measure_mm": 22.5,
            "embryo_stage": 7,
            "embryo_grade": 1,
            "protocol_name": "CIDR",
            "fresh_or_frozen": "Fresh",
        }
        status, body = call(client, "POST", "/predict/pregnancy", headers=headers, json=predict_payload)
        results["predict/pregnancy"] = (status, "ok" if status in (200, 503) else str(body))

        bad_file = io.BytesIO(b"hello")
        status, body = call(
            client,
            "POST",
            "/grade/similar-cases",
            files={"image": ("not-image.txt", bad_file, "text/plain")},
        )
        results["grade/similar-cases"] = (status, "ok" if status == 400 else str(body))

    ordered = sorted(results.items(), key=lambda item: item[0])
    failures = [(k, v) for k, v in ordered if v[1] != "ok"]

    print("\n=== API AUDIT RESULTS ===")
    for key, (status, detail) in ordered:
        print(f"{key:24} status={status:>3}  result={detail}")

    print("\nSummary:")
    print(f"  Total checks: {len(ordered)}")
    print(f"  Passed:       {len(ordered) - len(failures)}")
    print(f"  Failed:       {len(failures)}")

    if failures:
        print("\nFailures:")
        for key, (status, detail) in failures:
            print(f"  - {key}: status={status}, detail={detail}")


if __name__ == "__main__":
    main()
