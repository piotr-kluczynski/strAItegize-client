from pydantic import BaseModel
from typing import Optional

class TileData(BaseModel):
        q: int
        r: int
        s: int

        unit: Optional[str]
        region: str