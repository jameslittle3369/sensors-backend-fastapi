from fastapi import APIRouter, Depends
from sqlmodel import Session, col, select

from app.deps.db import get_session
from app.models.photo_uvmeter import PhotoUvmeter, PhotoUvmeterLog
from app.schemas.photo_uvmeter import PhotoUvmeterLogRequest, PhotoUvmeterLogResponse

router = APIRouter(tags=["photo-uvmeters"])


@router.post("/photo-uvmeters/{external_id}/log", response_model=PhotoUvmeterLogResponse)
def log_photo_uvmeter(
    external_id: str,
    payload: PhotoUvmeterLogRequest,
    session: Session = Depends(get_session),
) -> PhotoUvmeterLogResponse:
    device = session.get(PhotoUvmeter, external_id)
    if device is None:
        device = PhotoUvmeter(external_id=external_id, name=payload.name)
        session.add(device)
        session.commit()

    last_log = session.exec(
        select(PhotoUvmeterLog)
        .where(PhotoUvmeterLog.photo_uvmeter_id == external_id)
        .order_by(col(PhotoUvmeterLog.id).desc())
    ).first()
    if (
        last_log is not None
        and last_log.lumens == payload.lumens
        and last_log.uv_index == payload.uv_index
    ):
        return PhotoUvmeterLogResponse(external_id=external_id, created=False)

    device.name = payload.name
    device.current_lumens = payload.lumens
    device.current_uv_index = payload.uv_index
    session.add(device)

    session.add(
        PhotoUvmeterLog(
            photo_uvmeter_id=external_id,
            lumens=payload.lumens,
            uv_index=payload.uv_index,
        )
    )
    session.commit()
    return PhotoUvmeterLogResponse(external_id=external_id, created=True)
