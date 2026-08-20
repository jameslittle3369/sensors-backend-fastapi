import pytest

from app.models.thermohygrometer import ThermoHygrometer
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
