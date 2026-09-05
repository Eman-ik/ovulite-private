"""Integration tests for IVF Batch CRUD endpoints."""

import pytest


def _create_opu_session(client, auth_headers, tag_id="IVF-TEST-DONOR"):
    donor_resp = client.post("/donors/", json={"tag_id": tag_id, "breed": "Holstein"}, headers=auth_headers)
    assert donor_resp.status_code == 201, donor_resp.text
    donor_id = donor_resp.json()["donor_id"]

    opu_resp = client.post(
        "/opu-sessions/", json={"donor_id": donor_id, "opu_date": "2026-01-15"}, headers=auth_headers
    )
    assert opu_resp.status_code == 201, opu_resp.text
    return opu_resp.json()["opu_id"]


@pytest.mark.integration
def test_create_and_get_ivf_batch_with_computed_rates(client, auth_headers):
    opu_id = _create_opu_session(client, auth_headers)

    resp = client.post(
        "/ivf-batches/",
        json={
            "opu_id": opu_id,
            "oocytes_used": 16,
            "mature_oocytes": 14,
            "cleaved_embryos": 12,
            "blastocysts": 7,
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["opu_id"] == opu_id
    assert body["cleavage_rate"] == 0.75
    assert body["blastocyst_rate"] == round(7 / 16, 4)

    batch_id = body["ivf_batch_id"]
    get_resp = client.get(f"/ivf-batches/{batch_id}", headers=auth_headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["ivf_batch_id"] == batch_id


@pytest.mark.integration
def test_ivf_batch_rates_null_when_counts_missing(client, auth_headers):
    opu_id = _create_opu_session(client, auth_headers, "IVF-TEST-DONOR-2")
    resp = client.post("/ivf-batches/", json={"opu_id": opu_id}, headers=auth_headers)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["cleavage_rate"] is None
    assert body["blastocyst_rate"] is None


@pytest.mark.integration
def test_ivf_batch_rejects_impossible_counts(client, auth_headers):
    opu_id = _create_opu_session(client, auth_headers, "IVF-TEST-DONOR-3")
    resp = client.post(
        "/ivf-batches/",
        json={"opu_id": opu_id, "oocytes_used": 5, "cleaved_embryos": 10},
        headers=auth_headers,
    )
    assert resp.status_code == 422, resp.text


@pytest.mark.integration
def test_ivf_batch_list_filters_by_opu_id(client, auth_headers):
    opu_a = _create_opu_session(client, auth_headers, "IVF-TEST-DONOR-A")
    opu_b = _create_opu_session(client, auth_headers, "IVF-TEST-DONOR-B")
    client.post("/ivf-batches/", json={"opu_id": opu_a}, headers=auth_headers)
    client.post("/ivf-batches/", json={"opu_id": opu_b}, headers=auth_headers)

    resp = client.get("/ivf-batches/", params={"opu_id": opu_a}, headers=auth_headers)
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["opu_id"] == opu_a


@pytest.mark.integration
def test_update_and_delete_ivf_batch(client, auth_headers):
    opu_id = _create_opu_session(client, auth_headers, "IVF-TEST-DONOR-4")
    create_resp = client.post("/ivf-batches/", json={"opu_id": opu_id}, headers=auth_headers)
    batch_id = create_resp.json()["ivf_batch_id"]

    update_resp = client.put(
        f"/ivf-batches/{batch_id}", json={"oocytes_used": 20}, headers=auth_headers
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["oocytes_used"] == 20

    delete_resp = client.delete(f"/ivf-batches/{batch_id}", headers=auth_headers)
    assert delete_resp.status_code == 204

    get_resp = client.get(f"/ivf-batches/{batch_id}", headers=auth_headers)
    assert get_resp.status_code == 404


@pytest.mark.integration
def test_get_nonexistent_ivf_batch_404s(client, auth_headers):
    resp = client.get("/ivf-batches/999999", headers=auth_headers)
    assert resp.status_code == 404
