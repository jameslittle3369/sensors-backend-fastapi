from pydantic import BaseModel


class CameraRead(BaseModel):
    id: int
    name: str | None = None
    current_picture: str | None = None


class CameraUpdateRequest(BaseModel):
    name: str | None = None
    current_picture: str | None = None
