from decimal import Decimal

from sqlmodel import select

from app.models.raingauge import RainGauge, RainGaugeLog


def test_log_creates_raingauge_and_log_when_new(client, session):
    response = client.post(
        "/v1/raingauges/119/log",
        json={"name": "Atlas 119", "rain_in": "1.23"},
    )
    assert response.status_code == 200
    assert response.json() == {"external_id": "119", "created": True}

    device = session.get(RainGauge, "119")
    assert device is not None
    assert device.current_rain_in == Decimal("1.23")

    logs = session.exec(
        select(RainGaugeLog).where(RainGaugeLog.raingauge_id == "119")
    ).all()
    assert len(logs) == 1


def test_log_dedups_unchanged_reading(client, session):
    session.add(RainGauge(external_id="zone-2", name="Test"))
    session.commit()

    payload = {"name": "Test", "rain_in": "0.50"}
    first = client.post("/v1/raingauges/zone-2/log", json=payload)
    second = client.post("/v1/raingauges/zone-2/log", json=payload)

    assert first.json()["created"] is True
    assert second.json()["created"] is False

    logs = session.exec(
        select(RainGaugeLog).where(RainGaugeLog.raingauge_id == "zone-2")
    ).all()
    assert len(logs) == 1


def test_log_inserts_when_value_changes(client, session):
    session.add(RainGauge(external_id="zone-3", name="Test"))
    session.commit()

    client.post("/v1/raingauges/zone-3/log", json={"name": "Test", "rain_in": "0.50"})
    client.post("/v1/raingauges/zone-3/log", json={"name": "Test", "rain_in": "0.51"})

    logs = session.exec(
        select(RainGaugeLog).where(RainGaugeLog.raingauge_id == "zone-3")
    ).all()
    assert len(logs) == 2
