from decimal import Decimal

from sqlmodel import select

from app.models.spa import Spa, SpaLog


def test_log_creates_spa_and_log_when_new(client, session):
    response = client.post(
        "/v1/spas/aa:bb:cc:dd:ee:ff/log",
        json={
            "name": "Backyard Spa",
            "water_temp_f": "101.5",
            "setpoint_f": "102.0",
            "heat_state": "HEATING",
            "heat_mode": "READY",
            "temperature_range": "HIGH",
            "pump1_state": "HIGH",
            "pump2_state": "OFF",
            "circulation_pump_state": "ON",
        },
    )
    assert response.status_code == 200
    assert response.json() == {"external_id": "aa:bb:cc:dd:ee:ff", "created": True}

    spa = session.get(Spa, "aa:bb:cc:dd:ee:ff")
    assert spa is not None
    assert spa.name == "Backyard Spa"

    logs = session.exec(
        select(SpaLog).where(SpaLog.spa_id == "aa:bb:cc:dd:ee:ff")
    ).all()
    assert len(logs) == 1
    assert logs[0].water_temp_f == Decimal("101.5")
    assert logs[0].setpoint_f == Decimal("102.0")
    assert logs[0].heat_state == "HEATING"
    assert logs[0].pump1_state == "HIGH"
    assert logs[0].pump2_state == "OFF"
    assert logs[0].circulation_pump_state == "ON"
    # Fields not present in the payload stay null rather than defaulting --
    # distinguishes "this spa has no 2nd blower" from "blower 2 is off".
    assert logs[0].blower2_state is None
    assert logs[0].pump3_state is None


def test_log_dedups_unchanged_reading(client, session):
    session.add(Spa(external_id="spa-2", name="Test"))
    session.commit()

    payload = {
        "name": "Test",
        "water_temp_f": "100.0",
        "setpoint_f": "100.0",
        "heat_state": "OFF",
        "pump1_state": "OFF",
    }
    first = client.post("/v1/spas/spa-2/log", json=payload)
    second = client.post("/v1/spas/spa-2/log", json=payload)

    assert first.json()["created"] is True
    assert second.json()["created"] is False

    logs = session.exec(select(SpaLog).where(SpaLog.spa_id == "spa-2")).all()
    assert len(logs) == 1


def test_log_inserts_when_a_single_field_changes(client, session):
    session.add(Spa(external_id="spa-3", name="Test"))
    session.commit()

    base_payload = {
        "name": "Test",
        "water_temp_f": "99.0",
        "setpoint_f": "100.0",
        "heat_state": "HEAT_WAITING",
        "pump1_state": "LOW",
    }
    client.post("/v1/spas/spa-3/log", json=base_payload)
    # Only pump1_state differs -- every other field identical -- still
    # counts as changed since dedup compares every metric field.
    client.post("/v1/spas/spa-3/log", json={**base_payload, "pump1_state": "HIGH"})

    logs = session.exec(select(SpaLog).where(SpaLog.spa_id == "spa-3")).all()
    assert len(logs) == 2


def test_log_updates_spa_name_when_changed(client, session):
    session.add(Spa(external_id="spa-4", name="Old Name"))
    session.commit()

    client.post(
        "/v1/spas/spa-4/log",
        json={"name": "New Name", "water_temp_f": "100.0"},
    )

    spa = session.get(Spa, "spa-4")
    assert spa.name == "New Name"
