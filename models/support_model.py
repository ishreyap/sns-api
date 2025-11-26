from pydantic import BaseModel, EmailStr
from typing import Optional

class SupportRequest(BaseModel):
    """Pydantic model for support request form."""
    first_name: str
    last_name: str
    email: EmailStr  # Ensures valid email format
    company: Optional[str] = None
    position: Optional[str] = None
    message: str
