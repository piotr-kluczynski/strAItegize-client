from pydantic import BaseModel

class UnitData(BaseModel):
    unit_id: str
    owner: str
    tile: tuple[int, int, int]

    movement: int
    upkeep: int
    strength: int