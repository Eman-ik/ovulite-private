"""Integration tests for OPU Session CRUD endpoints, including org-scoping."""

import pytest


def _create_donor(client, auth_headers, tag_id="OPU-TEST-DONOR"):
    resp = client.post("/donors/", json={"tag_id": tag_id, "breed": "Holstein"}, headers=auth_headers)
    assert resp.status_code == 201, resp.text
    return resp.json()["donor_id"]


@pytest.mark.integration
def test_create_and_get_opu_session(client, auth_headers):
    donor_id = _create_donor(client, auth_headers)

    resp = client.post(
        "/opu-sessions/",
        json={
            "donor_id": donor_id,
            "opu_date": "2026-01-15",
            "total_follicles": 20,
            "oocytes_recovered": 16,
            "viable_oocytes": 12,
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["donor_id"] == donor_id
    assert body["recovery_rate"] == 0.8

    opu_id = body["opu_id"]
    get_resp = client.get(f"/opu-sessions/{opu_id}", headers=auth_headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["opu_id"] == opu_id


@pytest.mark.integration
def test_opu_session_recovery_rate_null_when_counts_missing(client, auth_headers):
    donor_id = _create_donor(client, auth_headers, "OPU-TEST-DONOR-2")
    resp = client.post(
        "/opu-sessions/", json={"donor_id": donor_id, "opu_date": "2026-01-16"}, headers=auth_headers
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["recovery_rate"] is None


@pytest.mark.integration
def test_opu_session_rejects_impossible_counts(client, auth_headers):
    donor_id = _create_donor(client, auth_headers, "OPU-TEST-DONOR-3")
    resp = client.post(
        "/opu-sessions/",
        json={"donor_id": donor_id, "opu_date": "2026-01-17", "total_follicles": 5, "oocytes_recovered": 10},
        headers=auth_headers,
    )
    assert resp.status_code == 422, resp.text


@pytest.mark.integration
def test_opu_session_list_filters_by_donor(client, auth_headers):
    donor_a = _create_donor(client, auth_headers, "OPU-TEST-DONOR-A")
    donor_b = _create_donor(client, auth_headers, "OPU-TEST-DONOR-B")
    client.post("/opu-sessions/", json={"donor_id": donor_a, "opu_date": "2026-02-01"}, headers=auth_headers)
    client.post("/opu-sessions/", json={"donor_id": donor_b, "opu_date": "2026-02-02"}, headers=auth_headers)

    resp = client.get("/opu-sessions/", params={"donor_id": donor_a}, headers=auth_headers)
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["donor_id"] == donor_a


@pytest.mark.integration
def test_update_and_delete_opu_session(client, auth_headers):
    donor_id = _create_donor(client, auth_headers, "OPU-TEST-DONOR-4")
    create_resp = client.post(
        "/opu-sessions/", json={"donor_id": donor_id, "opu_date": "2026-03-01"}, headers=auth_headers
    )
    opu_id = create_resp.json()["opu_id"]

    update_resp = client.put(
        f"/opu-sessions/{opu_id}", json={"total_follicles": 30}, headers=auth_headers
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["total_follicles"] == 30

    delete_resp = client.delete(f"/opu-sessions/{opu_id}", headers=auth_headers)
    assert delete_resp.status_code == 204

    get_resp = client.get(f"/opu-sessions/{opu_id}", headers=auth_headers)
    assert get_resp.status_code == 404


@pytest.mark.integration
def test_get_nonexistent_opu_session_404s(client, auth_headers):
    resp = client.get("/opu-sessions/999999", headers=auth_headers)
    assert resp.status_code == 404
