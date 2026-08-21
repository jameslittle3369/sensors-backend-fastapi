from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.deps.db import get_session
from app.models.ikea import IkeaDevice, IkeaDeviceLog
from app.schemas.ikea import IkeaDeviceLogRequest, IkeaDeviceLogResponse

router = APIRouter(tags=["ikea"])


@router.post("/ikea-devices/{external_id}/log", response_model=IkeaDeviceLogResponse)
def log_ikea_device(
    external_id: str,
    payload: IkeaDeviceLogRequest,
    session: Session = Depends(get_session),
) -> IkeaDevice:
    device = session.exec(
        select(IkeaDevice).where(IkeaDevice.external_id == external_id)
    ).first()
    if device is None:
        device = IkeaDevice(external_id=external_id, name=payload.name)

    device.name = payload.name
    device.battery_pct = payload.battery_pct
    device.last_seen_at = payload.last_seen_at

    session.add(device)
    session.commit()
    session.refresh(device)

    session.add(IkeaDeviceLog(device_id=device.id, battery_pct=payload.battery_pct))
    session.commit()

    return device
