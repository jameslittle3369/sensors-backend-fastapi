from sqlmodel import select

from app.models.energy import EnergyCircuit, EnergyCircuitLog


def test_creates_circuit_and_log_on_first_post(client):
    response = client.post(
        "/v1/energy-circuits/kasa/plug-1/log",
        json={"name": "Living Room Lamp", "watts": "42.50", "kwh_today": "1.234"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "kasa"
    assert body["external_id"] == "plug-1"
    assert body["current_watts"] == "42.50"
    assert body["kwh_today"] == "1.234"


def test_second_post_updates_snapshot_and_appends_log(client, session):
    client.post(
        "/v1/energy-circuits/emporia/circuit-9/log",
        json={"name": "Fridge", "watts": "100.00"},
    )
    client.post(
        "/v1/energy-circuits/emporia/circuit-9/log",
        json={"name": "Fridge", "watts": "120.00"},
    )

    circuit = session.exec(
        select(EnergyCircuit).where(
            EnergyCircuit.source == "emporia", EnergyCircuit.external_id == "circuit-9"
        )
    ).first()
    assert circuit is not None
    assert circuit.current_watts == 120

    logs = session.exec(
        select(EnergyCircuitLog).where(EnergyCircuitLog.circuit_id == circuit.id)
    ).all()
    assert len(logs) == 2
    assert [float(log.watts) for log in logs] == [100.0, 120.0]


def test_same_external_id_different_source_are_distinct(client, session):
    client.post("/v1/energy-circuits/kasa/1/log", json={"name": "Kasa Device", "watts": "1"})
    client.post(
        "/v1/energy-circuits/emporia/1/log", json={"name": "Emporia Circuit", "watts": "2"}
    )

    circuits = session.exec(select(EnergyCircuit).where(EnergyCircuit.external_id == "1")).all()
    assert len(circuits) == 2
    assert {c.source for c in circuits} == {"kasa", "emporia"}
