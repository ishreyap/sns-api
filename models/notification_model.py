from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional
from enum import Enum

class Notification_type(str, Enum):
    SELECT = "User"
    GROUP = "Division"
    ALL = "All"

class Workflow(BaseModel):
    body: str
    name: str
    priority: int
    ids: Optional[list[str]] = None
    status: Optional[str] = None
    WorkflowType: str
    NotificationType: Notification_type
    timestamp: Optional[datetime] = None

class DivisionCreateRequest(BaseModel):
    Division_name: str
    device_ids: list[str]

class WorkflowUpdate(BaseModel):
    name: Optional[str] = None
    body: Optional[str] = None
    priority: Optional[int] = None  
    status: Optional[str] = None
    WorkflowType: Optional[str] = None
    NotificationType: Optional[Notification_type] = None
    ids: Optional[List[str]] = None
    timestamp: Optional[datetime] = None
