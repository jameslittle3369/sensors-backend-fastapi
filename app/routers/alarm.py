from fastapi import APIRouter, Depends
from sqlmodel import Session, col, select

from app.deps.db import get_session
from app.models.alarm import (
    AlarmPartition,
    AlarmPartitionLog,
    AlarmTroubleLog,
    AlarmZone,
    AlarmZoneLog,
)
from app.schemas.alarm import (
    AlarmPartitionLogRequest,
    AlarmPartitionLogResponse,
    AlarmTroubleLogRequest,
    AlarmTroubleLogResponse,
    AlarmZoneLogRequest,
    AlarmZoneLogResponse,
)

router = APIRouter(tags=["alarm"])

_ZONE_EVENT_FIELDS = {
    "open": ("current_open", "open"),
    "restored": ("current_open", "restored"),
    "fault": ("current_fault", "fault"),
    "fault_restore": ("current_fault", "fault"),
    "alarm": ("current_alarm", "alarm"),
    "alarm_restore": ("current_alarm", "alarm"),
    "tamper": ("current_tamper", "tamper"),
    "tamper_restore": ("current_tamper", "tamper"),
    "low_battery": ("current_low_battery", "low_battery"),
    "low_battery_restore": ("current_low_battery", "low_battery"),
}


@router.post("/alarm-zones/{external_id}/log", response_model=AlarmZoneLogResponse)
def log_alarm_zone(
    external_id: str,
    payload: AlarmZoneLogRequest,
    session: Session = Depends(get_session),
) -> AlarmZoneLogResponse:
    zone = session.get(AlarmZone, external_id)
    if zone is None:
        zone = AlarmZone(external_id=external_id, name=payload.name, zone_type=payload.zone_type)
        session.add(zone)
        session.commit()

    last_log = session.exec(
        select(AlarmZoneLog)
        .where(AlarmZoneLog.zone_id == external_id)
        .order_by(col(AlarmZoneLog.id).desc())
    ).first()
    if last_log is not None and last_log.event == payload.event:
        return AlarmZoneLogResponse(external_id=external_id, created=False)

    zone.name = payload.name
    zone.zone_type = payload.zone_type
    field_name, active_value = _ZONE_EVENT_FIELDS.get(payload.event, (None, None))
    if field_name is not None:
        setattr(zone, field_name, payload.event == active_value)
    session.add(zone)

    session.add(AlarmZoneLog(zone_id=external_id, event=payload.event))
    session.commit()
    return AlarmZoneLogResponse(external_id=external_id, created=True)


@router.post("/alarm-partitions/{external_id}/log", response_model=AlarmPartitionLogResponse)
def log_alarm_partition(
    external_id: str,
    payload: AlarmPartitionLogRequest,
    session: Session = Depends(get_session),
) -> AlarmPartitionLogResponse:
    partition = session.get(AlarmPartition, external_id)
    if partition is None:
        partition = AlarmPartition(external_id=external_id, name=payload.name)
        session.add(partition)
        session.commit()

    last_log = session.exec(
        select(AlarmPartitionLog)
        .where(AlarmPartitionLog.partition_id == external_id)
        .order_by(col(AlarmPartitionLog.id).desc())
    ).first()
    if last_log is not None and last_log.status == payload.status:
        return AlarmPartitionLogResponse(external_id=external_id, created=False)

    partition.name = payload.name
    partition.current_status = payload.status
    session.add(partition)

    session.add(AlarmPartitionLog(partition_id=external_id, status=payload.status))
    session.commit()
    return AlarmPartitionLogResponse(external_id=external_id, created=True)


@router.post("/alarm-trouble/log", response_model=AlarmTroubleLogResponse)
def log_alarm_trouble(
    payload: AlarmTroubleLogRequest,
    session: Session = Depends(get_session),
) -> AlarmTroubleLogResponse:
    last_log = session.exec(
        select(AlarmTroubleLog).order_by(col(AlarmTroubleLog.id).desc())
    ).first()
    if last_log is not None and last_log.condition == payload.condition:
        return AlarmTroubleLogResponse(created=False)

    session.add(AlarmTroubleLog(condition=payload.condition))
    session.commit()
    return AlarmTroubleLogResponse(created=True)
