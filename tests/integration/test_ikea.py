def test_creates_device_and_updates_battery(client):
    response = client.post(
        "/v1/ikea-devices/tradfri-1/log",
        json={"name": "Bedroom Bulb", "battery_pct": 80},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["external_id"] == "tradfri-1"
    assert body["battery_pct"] == 80

    response = client.post(
        "/v1/ikea-devices/tradfri-1/log",
        json={"name": "Bedroom Bulb", "battery_pct": 75},
    )
    assert response.status_code == 200
    assert response.json()["battery_pct"] == 75
