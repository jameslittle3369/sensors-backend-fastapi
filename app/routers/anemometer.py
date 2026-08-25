from fastapi import APIRouter, Depends
from sqlmodel import Session, col, select

from app.deps.db import get_session
from app.models.anemometer import Anemometer, AnemometerLog
from app.schemas.anemometer import AnemometerLogRequest, AnemometerLogResponse

router = APIRouter(tags=["anemometers"])


@router.post("/anemometers/{external_id}/log", response_model=AnemometerLogResponse)
def log_anemometer(
    external_id: str,
    payload: AnemometerLogRequest,
    session: Session = Depends(get_session),
) -> AnemometerLogResponse:
    device = session.get(Anemometer, external_id)
    if device is None:
        device = Anemometer(external_id=external_id, name=payload.name)
        session.add(device)
        session.commit()

    last_log = session.exec(
        select(AnemometerLog)
        .where(AnemometerLog.anemometer_id == external_id)
        .order_by(col(AnemometerLog.id).desc())
    ).first()
    if (
        last_log is not None
        and last_log.speed_mph == payload.speed_mph
        and last_log.direction_deg == payload.direction_deg
    ):
        return AnemometerLogResponse(external_id=external_id, created=False)

    device.name = payload.name
    device.current_speed_mph = payload.speed_mph
    device.current_direction_deg = payload.direction_deg
    session.add(device)

    session.add(
        AnemometerLog(
            anemometer_id=external_id,
            speed_mph=payload.speed_mph,
            direction_deg=payload.direction_deg,
        )
    )
    session.commit()
    return AnemometerLogResponse(external_id=external_id, created=True)
