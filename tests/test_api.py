import pytest
import httpx
from fastapi import status
from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def get_token():
    resp = client.post("/api/auth/token", data={"username": "demo", "password": "demo1234"})
    assert resp.status_code == status.HTTP_200_OK
    return resp.json()["access_token"]


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_auth_and_library_crud():
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}

    # list empty
    resp = client.get("/api/library/items", headers=headers)
    assert resp.status_code == 200
    assert resp.json() == []

    # add item
    payload = {"title": "Solo Leveling", "type": "manga", "source": "mangadex"}
    resp = client.post("/api/library/items", json=payload, headers=headers)
    assert resp.status_code == 200
    item = resp.json()
    assert item["id"] == 1

    # update progress
    resp = client.patch("/api/library/items/1", json={"progress": 10, "status": "reading"}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["progress"] == 10

    # get
    resp = client.get("/api/library/items/1", headers=headers)
    assert resp.status_code == 200

    # delete
    resp = client.delete("/api/library/items/1", headers=headers)
    assert resp.status_code == 200


def test_sources():
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.get("/api/sources/", headers=headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)

    resp = client.get("/api/sources/search", params={"q": "One"}, headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) >= 1
