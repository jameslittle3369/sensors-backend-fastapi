from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, col, func, select

from app.deps.db import get_session
from app.models.thermohygrometer import ThermoHygrometer, ThermoHygrostatLog
from app.schemas.thermohygrometer import (
    ThermoHygrometerListItem,
    ThermoHygrometerLogRequest,
    ThermoHygrometerLogResponse,
)
from app.schemas.tstat import TstatLogRepr

router = APIRouter(tags=["thermohygrometers"])


@router.get("/thermohygrometers", response_model=list[ThermoHygrometerListItem])
def list_thermohygrometers(
    session: Session = Depends(get_session),
) -> list[ThermoHygrometerListItem]:
    rows = session.exec(
        select(ThermoHygrometer).order_by(col(ThermoHygrometer.pretty_name))
    ).all()
    return [
        ThermoHygrometerListItem(id_channel=r.id_channel, pretty_name=r.pretty_name)
        for r in rows
    ]


@router.get("/thermohygrometers/{id_channel}")
def retrieve_thermohygrometer(id_channel: str, session: Session = Depends(get_session)) -> dict:
    thermohygrometer = session.get(ThermoHygrometer, id_channel)
    if thermohygrometer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    # BUG PORTED AS-IS: Django's ThermoHygrometerRetrieveSerializer.get_last
    # orders by `-thermohygrometer` (the FK id, not time) AND wraps the
    # result in TstatLogSerializer instead of ThermoHygrostatLogSerializer
    # -- TstatLogSerializer.get_f reads `.primary_value`, a field that
    # doesn't exist on ThermoHygrostatLog (it has `.temp_f` instead). That
    # raises AttributeError in Django too, so GET .../thermohygrometers/{id}
    # currently always 500s in the original app whenever this field is
    # rendered (which is always -- it's not behind a try/except like the
    # list view's get_last is). Reproduced here verbatim by deliberately
    # reading the nonexistent attribute, rather than "fixing" it.
    last_row = session.exec(
        select(ThermoHygrostatLog)
        .where(ThermoHygrostatLog.thermohygrometer_id == id_channel)
        .order_by(col(ThermoHygrostatLog.thermohygrometer_id).desc())
    ).first()
    _ = last_row.primary_value  # type: ignore[attr-defined]  # intentional AttributeError

    # Unreachable while the bug above stands -- kept so that fixing the
    # bug later (a separate task, not this migration) only requires
    # deleting the two lines above.
    cutoff = datetime.now(UTC) - timedelta(days=1)

    def _extremum_log(agg_func) -> TstatLogRepr:
        target_value = session.exec(
            select(agg_func(ThermoHygrostatLog.temp_f)).where(
                ThermoHygrostatLog.thermohygrometer_id == id_channel,
                ThermoHygrostatLog.created_at > cutoff,
            )
        ).one()
        matching_id = session.exec(
            select(func.min(ThermoHygrostatLog.id)).where(
                ThermoHygrostatLog.thermohygrometer_id == id_channel,
                ThermoHygrostatLog.created_at > cutoff,
                ThermoHygrostatLog.temp_f == target_value,
            )
        ).one()
        row = session.get(ThermoHygrostatLog, matching_id)
        return TstatLogRepr(at=row.created_at, f=row.temp_f)

    high_last24 = _extremum_log(func.max)
    low_last24 = _extremum_log(func.min)

    return {
        "id_channel": thermohygrometer.id_channel,
        "pretty_name": thermohygrometer.pretty_name,
        "high_last24": high_last24,
        "low_last24": low_last24,
    }


@router.post("/thermohygrometers/{id_channel}/log", response_model=ThermoHygrometerLogResponse)
def log_thermohygrometer(
    id_channel: str,
    payload: ThermoHygrometerLogRequest,
    session: Session = Depends(get_session),
) -> ThermoHygrometerLogResponse:
    # New write path for a table that was previously read-only in this
    # app -- the old Django app and rtl_2_postgres.py both wrote directly
    # via raw SQL, never through an API. get-or-create the parent device
    # (id_channel is the natural PK; pretty_name is NOT NULL in the live
    # schema, so fall back to id_channel itself if not provided).
    device = session.get(ThermoHygrometer, id_channel)
    if device is None:
        device = ThermoHygrometer(
            id_channel=id_channel, pretty_name=payload.pretty_name or id_channel
        )
        session.add(device)
        session.commit()

    # Dedup: skip the insert if both temp_f and humidity match the most
    # recent log entry for this device.
    last_log = session.exec(
        select(ThermoHygrostatLog)
        .where(ThermoHygrostatLog.thermohygrometer_id == id_channel)
        .order_by(col(ThermoHygrostatLog.id).desc())
    ).first()
    if last_log is not None and last_log.temp_f == payload.temp_f and last_log.humidity == payload.humidity:
        return ThermoHygrometerLogResponse(id_channel=id_channel, created=False)

    session.add(
        ThermoHygrostatLog(
            thermohygrometer_id=id_channel,
            temp_f=payload.temp_f,
            humidity=payload.humidity,
        )
    )
    session.commit()
    return ThermoHygrometerLogResponse(id_channel=id_channel, created=True)
