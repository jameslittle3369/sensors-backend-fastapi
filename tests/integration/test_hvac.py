from sqlmodel import select

from app.models.hvac import HvacZone, HvacZoneLog


def test_log_creates_zone_and_log_when_new(client, session):
    response = client.post(
        "/v1/hvac-zones/12345/log",
        json={
            "name": "Downstairs",
            "disp_temperature": 72,
            "heat_setpoint": 68,
            "cool_setpoint": 75,
            "fan_mode": 0,
            "fan_is_running": True,
        },
    )
    assert response.status_code == 200
    assert response.json() == {"external_id": "12345", "created": True}

    zone = session.get(HvacZone, "12345")
    assert zone is not None
    assert zone.name == "Downstairs"

    logs = session.exec(
        select(HvacZoneLog).where(HvacZoneLog.hvac_zone_id == "12345")
    ).all()
    assert len(logs) == 1
    assert logs[0].disp_temperature == 72
    assert logs[0].fan_is_running is True
    # Fields not present in the payload stay null rather than defaulting
    # to 0/False -- distinguishes "unknown" from "actually off/zero".
    assert logs[0].outdoor_temperature is None


def test_log_dedups_unchanged_reading(client, session):
    session.add(HvacZone(external_id="zone-2", name="Upstairs"))
    session.commit()

    payload = {
        "name": "Upstairs",
        "disp_temperature": 70,
        "heat_setpoint": 68,
        "cool_setpoint": 74,
        "fan_mode": 1,
        "fan_is_running": False,
    }
    first = client.post("/v1/hvac-zones/zone-2/log", json=payload)
    second = client.post("/v1/hvac-zones/zone-2/log", json=payload)

    assert first.json()["created"] is True
    assert second.json()["created"] is False

    logs = session.exec(
        select(HvacZoneLog).where(HvacZoneLog.hvac_zone_id == "zone-2")
    ).all()
    assert len(logs) == 1


def test_log_inserts_when_a_single_field_changes(client, session):
    session.add(HvacZone(external_id="zone-3", name="Basement"))
    session.commit()

    base_payload = {
        "name": "Basement",
        "disp_temperature": 65,
        "heat_setpoint": 68,
        "cool_setpoint": 74,
        "fan_mode": 0,
        "fan_is_running": True,
    }
    client.post("/v1/hvac-zones/zone-3/log", json=base_payload)
    # Only fan_is_running differs -- every other field identical -- still
    # counts as changed since dedup compares every metric field.
    client.post(
        "/v1/hvac-zones/zone-3/log", json={**base_payload, "fan_is_running": False}
    )

    logs = session.exec(
        select(HvacZoneLog).where(HvacZoneLog.hvac_zone_id == "zone-3")
    ).all()
    assert len(logs) == 2


def test_log_updates_zone_name_when_changed(client, session):
    session.add(HvacZone(external_id="zone-4", name="Old Name"))
    session.commit()

    client.post(
        "/v1/hvac-zones/zone-4/log",
        json={"name": "New Name", "disp_temperature": 70},
    )

    zone = session.get(HvacZone, "zone-4")
    assert zone.name == "New Name"
