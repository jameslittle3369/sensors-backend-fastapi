from datetime import UTC, datetime, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, col, func, select

from app.deps.db import get_session
from app.models.tstat import Thermometer, TstatLog
from app.schemas.tstat import ThermometerListItem, ThermometerRetrieveOut, TstatLogRepr

router = APIRouter(tags=["thermometers"])


def _to_fahrenheit(primary_value: Decimal) -> Decimal:
    return (primary_value * 9) / 5 + 32


@router.get("/thermometers", response_model=list[ThermometerListItem])
def list_thermometers(session: Session = Depends(get_session)) -> list[ThermometerListItem]:
    thermometers = session.exec(
        select(Thermometer).order_by(col(Thermometer.pretty_name))
    ).all()
    items = []
    for t in thermometers:
        try:
            last_log = session.exec(
                select(TstatLog).where(TstatLog.romid_id == t.romid).order_by(col(TstatLog.id).desc())
            ).first()
            last = _to_fahrenheit(last_log.primary_value)
        except Exception:
            last = None
        # url is hardcoded to '' in Django (get_thermometer_url always
        # returns '') -- ported verbatim.
        items.append(ThermometerListItem(url="", pretty_name=t.pretty_name, last=last))
    return items


@router.get("/thermometers/{romid}", response_model=ThermometerRetrieveOut)
def retrieve_thermometer(
    romid: str, session: Session = Depends(get_session)
) -> ThermometerRetrieveOut:
    thermometer = session.get(Thermometer, romid)
    if thermometer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    # No try/except here, matching ThermometerRetrieveSerializer -- if
    # there's no log data at all this raises and the request 500s, same
    # as Django would (unlike the list view, which does catch it).
    last_log = session.exec(
        select(TstatLog).where(TstatLog.romid_id == romid).order_by(col(TstatLog.id).desc())
    ).first()
    last = TstatLogRepr(at=last_log.created_at, f=_to_fahrenheit(last_log.primary_value))

    cutoff = datetime.now(UTC) - timedelta(days=1)

    def _extremum_log(agg_func) -> TstatLogRepr:
        target_value = session.exec(
            select(agg_func(TstatLog.primary_value)).where(
                TstatLog.romid_id == romid, TstatLog.created_at > cutoff
            )
        ).one()
        matching_id = session.exec(
            select(func.min(TstatLog.id)).where(
                TstatLog.romid_id == romid,
                TstatLog.created_at > cutoff,
                TstatLog.primary_value == target_value,
            )
        ).one()
        row = session.get(TstatLog, matching_id)
        return TstatLogRepr(at=row.created_at, f=_to_fahrenheit(row.primary_value))

    high_last24 = _extremum_log(func.max)
    low_last24 = _extremum_log(func.min)

    return ThermometerRetrieveOut(
        romid=thermometer.romid,
        pretty_name=thermometer.pretty_name,
        last=last,
        high_last24=high_last24,
        low_last24=low_last24,
    )
