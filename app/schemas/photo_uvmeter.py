from pydantic import BaseModel


class PhotoUvmeterLogRequest(BaseModel):
    name: str
    lumens: int
    uv_index: int


class PhotoUvmeterLogResponse(BaseModel):
    external_id: str
    created: bool  # False when skipped due to dedup (unchanged reading)
