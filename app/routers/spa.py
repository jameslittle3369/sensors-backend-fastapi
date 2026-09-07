from fastapi import APIRouter, Depends
from sqlmodel import Session, col, select

from app.deps.db import get_session
from app.models.spa import SPA_LOG_METRIC_FIELDS, Spa, SpaLog
from app.schemas.spa import SpaLogRequest, SpaLogResponse

router = APIRouter(tags=["spas"])


@router.post("/spas/{external_id}/log", response_model=SpaLogResponse)
def log_spa(
    external_id: str,
    payload: SpaLogRequest,
    session: Session = Depends(get_session),
) -> SpaLogResponse:
    spa = session.get(Spa, external_id)
    if spa is None:
        spa = Spa(external_id=external_id, name=payload.name)
        session.add(spa)
        session.commit()
    elif spa.name != payload.name:
        spa.name = payload.name
        session.add(spa)
        session.commit()

    # Dedup across every metric field -- insert only if at least one
    # differs from the most recent log for this spa.
    last_log = session.exec(
        select(SpaLog).where(SpaLog.spa_id == external_id).order_by(col(SpaLog.id).desc())
    ).first()
    if last_log is not None and all(
        getattr(last_log, field) == getattr(payload, field) for field in SPA_LOG_METRIC_FIELDS
    ):
        return SpaLogResponse(external_id=external_id, created=False)

    session.add(
        SpaLog(
            spa_id=external_id,
            **{field: getattr(payload, field) for field in SPA_LOG_METRIC_FIELDS},
        )
    )
    session.commit()
    return SpaLogResponse(external_id=external_id, created=True)
