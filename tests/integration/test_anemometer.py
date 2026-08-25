from decimal import Decimal

from sqlmodel import select

from app.models.anemometer import Anemometer, AnemometerLog


def test_log_creates_anemometer_and_log_when_new(client, session):
    response = client.post(
        "/v1/anemometers/119/log",
        json={"name": "Atlas 119", "speed_mph": "12.3", "direction_deg": "270.0"},
    )
    assert response.status_code == 200
    assert response.json() == {"external_id": "119", "created": True}

    device = session.get(Anemometer, "119")
    assert device is not None
    assert device.name == "Atlas 119"
    assert device.current_speed_mph == Decimal("12.3")
    assert device.current_direction_deg == Decimal("270.0")

    logs = session.exec(
        select(AnemometerLog).where(AnemometerLog.anemometer_id == "119")
    ).all()
    assert len(logs) == 1


def test_log_dedups_unchanged_reading(client, session):
    session.add(Anemometer(external_id="zone-2", name="Test"))
    session.commit()

    payload = {"name": "Test", "speed_mph": "5.0", "direction_deg": "90.0"}
    first = client.post("/v1/anemometers/zone-2/log", json=payload)
    second = client.post("/v1/anemometers/zone-2/log", json=payload)

    assert first.json()["created"] is True
    assert second.json()["created"] is False

    logs = session.exec(
        select(AnemometerLog).where(AnemometerLog.anemometer_id == "zone-2")
    ).all()
    assert len(logs) == 1


def test_log_inserts_when_value_changes(client, session):
    session.add(Anemometer(external_id="zone-3", name="Test"))
    session.commit()

    client.post(
        "/v1/anemometers/zone-3/log",
        json={"name": "Test", "speed_mph": "5.0", "direction_deg": "90.0"},
    )
    client.post(
        "/v1/anemometers/zone-3/log",
        json={"name": "Test", "speed_mph": "6.0", "direction_deg": "90.0"},
    )

    logs = session.exec(
        select(AnemometerLog).where(AnemometerLog.anemometer_id == "zone-3")
    ).all()
    assert len(logs) == 2
