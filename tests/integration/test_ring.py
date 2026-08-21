def test_creates_device_and_updates_battery(client):
    response = client.post(
        "/v1/ring-devices/doorbell-1/log",
        json={"name": "Front Door", "battery_life": 90},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["external_id"] == "doorbell-1"
    assert body["battery_life"] == 90
    assert body["last_motion_at"] is None

    response = client.post(
        "/v1/ring-devices/doorbell-1/log",
        json={
            "name": "Front Door",
            "battery_life": 88,
            "last_motion_at": "2026-08-20T12:00:00Z",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["battery_life"] == 88
    assert body["last_motion_at"] is not None
