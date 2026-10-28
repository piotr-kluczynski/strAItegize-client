from pydantic import BaseModel

class RegionData(BaseModel):
    region_id: str 
    owner: str | None
    command_center: tuple[int, int, int]
    upkeep: int