from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, col, select

from app.deps.db import get_session
from app.models.aqsensor import AQSensor
from app.schemas.aqsensor import AQSensorRead, AQSensorUpdateRequest

router = APIRouter(tags=["aqsensors"])


@router.get("/aqsensors", response_model=list[AQSensorRead])
def list_aqsensors(session: Session = Depends(get_session)) -> list[AQSensor]:
    return session.exec(select(AQSensor).order_by(col(AQSensor.name))).all()


@router.get("/aqsensors/{aqsensor_id}", response_model=AQSensorRead)
def get_aqsensor(aqsensor_id: int, session: Session = Depends(get_session)) -> AQSensor:
    sensor = session.get(AQSensor, aqsensor_id)
    if sensor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return sensor


@router.patch("/aqsensors/{aqsensor_id}", response_model=AQSensorRead)
@router.put("/aqsensors/{aqsensor_id}", response_model=AQSensorRead)
def update_aqsensor(
    aqsensor_id: int,
    payload: AQSensorUpdateRequest,
    session: Session = Depends(get_session),
) -> AQSensor:
    sensor = session.get(AQSensor, aqsensor_id)
    if sensor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    if payload.name is not None:
        sensor.name = payload.name
    session.add(sensor)
    session.commit()
    session.refresh(sensor)
    return sensor
