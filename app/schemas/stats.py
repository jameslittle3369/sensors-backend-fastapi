from pydantic import BaseModel


class StatsResponse(BaseModel):
    labels: list[str]
    totals: list
    thermometers: dict[str, list]
