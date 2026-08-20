from pydantic import BaseModel


class AQSensorRead(BaseModel):
    id: int
    name: str | None = None


class AQSensorUpdateRequest(BaseModel):
    name: str | None = None
