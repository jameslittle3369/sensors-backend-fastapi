from fastapi import APIRouter, Depends
from sqlmodel import Session, col, select

from app.deps.db import get_session
from app.models.hvac import HVAC_ZONE_LOG_METRIC_FIELDS, HvacZone, HvacZoneLog
from app.schemas.hvac import HvacZoneLogRequest, HvacZoneLogResponse

router = APIRouter(tags=["hvac"])


@router.post("/hvac-zones/{external_id}/log", response_model=HvacZoneLogResponse)
def log_hvac_zone(
    external_id: str,
    payload: HvacZoneLogRequest,
    session: Session = Depends(get_session),
) -> HvacZoneLogResponse:
    zone = session.get(HvacZone, external_id)
    if zone is None:
        zone = HvacZone(external_id=external_id, name=payload.name)
        session.add(zone)
        session.commit()
    elif zone.name != payload.name:
        zone.name = payload.name
        session.add(zone)
        session.commit()

    # Dedup across every metric field -- insert only if at least one
    # differs from the most recent log for this zone.
    last_log = session.exec(
        select(HvacZoneLog)
        .where(HvacZoneLog.hvac_zone_id == external_id)
        .order_by(col(HvacZoneLog.id).desc())
    ).first()
    if last_log is not None and all(
        getattr(last_log, field) == getattr(payload, field)
        for field in HVAC_ZONE_LOG_METRIC_FIELDS
    ):
        return HvacZoneLogResponse(external_id=external_id, created=False)

    session.add(
        HvacZoneLog(
            hvac_zone_id=external_id,
            **{field: getattr(payload, field) for field in HVAC_ZONE_LOG_METRIC_FIELDS},
        )
    )
    session.commit()
    return HvacZoneLogResponse(external_id=external_id, created=True)
