from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.deps.db import get_session
from app.models.ring import RingDevice, RingDeviceLog
from app.schemas.ring import RingDeviceLogRequest, RingDeviceLogResponse

router = APIRouter(tags=["ring"])


@router.post("/ring-devices/{external_id}/log", response_model=RingDeviceLogResponse)
def log_ring_device(
    external_id: str,
    payload: RingDeviceLogRequest,
    session: Session = Depends(get_session),
) -> RingDevice:
    device = session.exec(
        select(RingDevice).where(RingDevice.external_id == external_id)
    ).first()
    if device is None:
        device = RingDevice(external_id=external_id, name=payload.name)

    device.name = payload.name
    device.battery_life = payload.battery_life
    if payload.last_motion_at is not None:
        device.last_motion_at = payload.last_motion_at

    session.add(device)
    session.commit()
    session.refresh(device)

    session.add(
        RingDeviceLog(
            device_id=device.id,
            battery_life=payload.battery_life,
            last_motion_at=payload.last_motion_at,
        )
    )
    session.commit()

    return device
