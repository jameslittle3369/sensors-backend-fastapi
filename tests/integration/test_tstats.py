import pytest

from sqlmodel import select

from app.models.thermohygrometer import ThermoHygrometer, ThermoHygrostatLog
from app.models.tstat import Thermometer, TstatLog


def test_tstats_list_always_returns_empty_object(client):
    # Ported bug: Django's TstatsViewSet.list() returns {} unconditionally.
    response = client.get("/v1/tstats")
    assert response.status_code == 200
    assert response.json() == {}


def test_thermometers_list(client, session):
    session.add(Thermometer(romid="28FF001", pretty_name="Living Room"))
    session.add(TstatLog(romid_id="28FF001", primary_value="20.0000"))
    session.commit()

    response = client.get("/v1/thermometers")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["pretty_name"] == "Living Room"
    assert body[0]["url"] == ""  # hardcoded empty url, ported as-is
    assert body[0]["last"] == "68.0000"  # 20C -> F, Decimal serialized as string


def test_thermometers_retrieve_not_found(client):
    response = client.get("/v1/thermometers/does-not-exist")
    assert response.status_code == 404


def test_thermohygrometers_list_last_always_null(client, session):
    # Ported bug: ThermoHygrometerListSerializer.get_last is hardcoded to
    # `return None` unconditionally in Django -- always null here too.
    session.add(ThermoHygrometer(id_channel="chan-1", pretty_name="Basement"))
    session.commit()

    response = client.get("/v1/thermohygrometers")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["last"] is None


def test_thermohygrometers_retrieve_always_crashes(client, session):
    # Ported bug: ThermoHygrometerRetrieveSerializer.get_last reads a
    # field that doesn't exist on ThermoHygrostatLog -- this endpoint
    # currently always 500s in Django too (an unhandled AttributeError
    # on a real deployment). Pinned here via the underlying exception
    # rather than a converted 500 status, since TestClient re-raises
    # server exceptions by default. Not "fixed" -- see the router
    # comment for why this is intentional.
    session.add(ThermoHygrometer(id_channel="chan-1", pretty_name="Basement"))
    session.commit()

    with pytest.raises(AttributeError):
        client.get("/v1/thermohygrometers/chan-1")


def test_log_creates_device_and_log_when_new(client, session):
    response = client.post(
        "/v1/thermohygrometers/new-chan/log",
        json={
            "pretty_name": "Attic",
            "temp_f": "70.5",
            "humidity": "45.0",
            "battery_ok": True,
        },
    )
    assert response.status_code == 200
    assert response.json() == {"id_channel": "new-chan", "created": True}

    device = session.get(ThermoHygrometer, "new-chan")
    assert device is not None
    assert device.pretty_name == "Attic"
    # current_f/current_h previously existed on the model but were never
    # written by this endpoint -- confirm the fix actually updates them.
    assert device.current_f == 70.5
    assert device.current_h == 45.0
    assert device.battery_ok is True

    logs = session.exec(
        select(ThermoHygrostatLog).where(ThermoHygrostatLog.thermohygrometer_id == "new-chan")
    ).all()
    assert len(logs) == 1


def test_log_dedups_unchanged_reading(client, session):
    session.add(ThermoHygrometer(id_channel="chan-2", pretty_name="Garage"))
    session.commit()

    payload = {"temp_f": "60.0", "humidity": "50.0"}
    first = client.post("/v1/thermohygrometers/chan-2/log", json=payload)
    second = client.post("/v1/thermohygrometers/chan-2/log", json=payload)

    assert first.json()["created"] is True
    assert second.json()["created"] is False

    logs = session.exec(
        select(ThermoHygrostatLog).where(ThermoHygrostatLog.thermohygrometer_id == "chan-2")
    ).all()
    assert len(logs) == 1


def test_log_inserts_when_value_changes(client, session):
    session.add(ThermoHygrometer(id_channel="chan-3", pretty_name="Shed"))
    session.commit()

    client.post(
        "/v1/thermohygrometers/chan-3/log", json={"temp_f": "60.0", "humidity": "50.0"}
    )
    client.post(
        "/v1/thermohygrometers/chan-3/log", json={"temp_f": "61.0", "humidity": "50.0"}
    )

    logs = session.exec(
        select(ThermoHygrostatLog).where(ThermoHygrostatLog.thermohygrometer_id == "chan-3")
    ).all()
    assert len(logs) == 2
