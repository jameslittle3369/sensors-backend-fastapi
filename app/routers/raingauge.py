from fastapi import APIRouter, Depends
from sqlmodel import Session, col, select

from app.deps.db import get_session
from app.models.raingauge import RainGauge, RainGaugeLog
from app.schemas.raingauge import RainGaugeLogRequest, RainGaugeLogResponse

router = APIRouter(tags=["raingauges"])


@router.post("/raingauges/{external_id}/log", response_model=RainGaugeLogResponse)
def log_raingauge(
    external_id: str,
    payload: RainGaugeLogRequest,
    session: Session = Depends(get_session),
) -> RainGaugeLogResponse:
    device = session.get(RainGauge, external_id)
    if device is None:
        device = RainGauge(external_id=external_id, name=payload.name)
        session.add(device)
        session.commit()

    last_log = session.exec(
        select(RainGaugeLog)
        .where(RainGaugeLog.raingauge_id == external_id)
        .order_by(col(RainGaugeLog.id).desc())
    ).first()
    if last_log is not None and last_log.rain_in == payload.rain_in:
        return RainGaugeLogResponse(external_id=external_id, created=False)

    device.name = payload.name
    device.current_rain_in = payload.rain_in
    session.add(device)

    session.add(RainGaugeLog(raingauge_id=external_id, rain_in=payload.rain_in))
    session.commit()
    return RainGaugeLogResponse(external_id=external_id, created=True)
