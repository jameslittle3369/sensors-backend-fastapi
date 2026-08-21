from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.deps.db import get_session
from app.models.energy import EnergyCircuit, EnergyCircuitLog
from app.schemas.energy import EnergyCircuitLogRequest, EnergyCircuitLogResponse

router = APIRouter(tags=["energy"])


@router.post(
    "/energy-circuits/{source}/{external_id}/log",
    response_model=EnergyCircuitLogResponse,
)
def log_energy_circuit(
    source: str,
    external_id: str,
    payload: EnergyCircuitLogRequest,
    session: Session = Depends(get_session),
) -> EnergyCircuit:
    circuit = session.exec(
        select(EnergyCircuit).where(
            EnergyCircuit.source == source, EnergyCircuit.external_id == external_id
        )
    ).first()
    if circuit is None:
        circuit = EnergyCircuit(source=source, external_id=external_id, name=payload.name)

    circuit.name = payload.name
    circuit.current_watts = payload.watts
    if payload.kwh_today is not None:
        circuit.kwh_today = payload.kwh_today
    if payload.kwh_7d is not None:
        circuit.kwh_7d = payload.kwh_7d
    if payload.kwh_30d is not None:
        circuit.kwh_30d = payload.kwh_30d
    if payload.kwh_mtd is not None:
        circuit.kwh_mtd = payload.kwh_mtd

    session.add(circuit)
    session.commit()
    session.refresh(circuit)

    session.add(EnergyCircuitLog(circuit_id=circuit.id, watts=payload.watts))
    session.commit()

    return circuit
