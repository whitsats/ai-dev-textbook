import pytest


def test_index(client):
    response = client.get("/api/")
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 200
