from typing import List, Optional
from pydantic import BaseModel


class ScreenshotTimerRequest(BaseModel):
    device_ids: Optional[List[str]]
    division_names: Optional[List[str]]
    interval_minutes: int  
    type: str

class StopTimerRequest(BaseModel):
    device_ids: Optional[List[str]]
    division_names: Optional[List[str]]
    stop_all: Optional[bool]