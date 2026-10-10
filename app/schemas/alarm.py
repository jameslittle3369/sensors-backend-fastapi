from pydantic import BaseModel


class AlarmZoneLogRequest(BaseModel):
    name: str
    zone_type: str
    event: str


class AlarmZoneLogResponse(BaseModel):
    external_id: str
    created: bool  # False when skipped due to dedup (unchanged event)


class AlarmPartitionLogRequest(BaseModel):
    name: str
    status: str


class AlarmPartitionLogResponse(BaseModel):
    external_id: str
    created: bool  # False when skipped due to dedup (unchanged status)


class AlarmTroubleLogRequest(BaseModel):
    condition: str


class AlarmTroubleLogResponse(BaseModel):
    created: bool  # False when skipped due to dedup (unchanged condition)
