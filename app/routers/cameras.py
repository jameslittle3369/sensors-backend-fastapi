from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, col, select

from app.deps.db import get_session
from app.models.camera import Camera
from app.schemas.camera import CameraRead, CameraUpdateRequest

router = APIRouter(tags=["cameras"])


@router.get("/cameras", response_model=list[CameraRead])
def list_cameras(session: Session = Depends(get_session)) -> list[Camera]:
    return session.exec(select(Camera).order_by(col(Camera.name))).all()


@router.get("/cameras/{camera_id}", response_model=CameraRead)
def get_camera(camera_id: int, session: Session = Depends(get_session)) -> Camera:
    camera = session.get(Camera, camera_id)
    if camera is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return camera


@router.patch("/cameras/{camera_id}", response_model=CameraRead)
@router.put("/cameras/{camera_id}", response_model=CameraRead)
def update_camera(
    camera_id: int,
    payload: CameraUpdateRequest,
    session: Session = Depends(get_session),
) -> Camera:
    camera = session.get(Camera, camera_id)
    if camera is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    if payload.name is not None:
        camera.name = payload.name
    if payload.current_picture is not None:
        camera.current_picture = payload.current_picture
    session.add(camera)
    session.commit()
    session.refresh(camera)
    return camera
