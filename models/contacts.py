from typing import Optional
from pydantic import BaseModel, EmailStr

class CreateContactRequest(BaseModel):
    username: str
    email: EmailStr
    Division: str 
    
class Contact(BaseModel):
    username: str
    email: EmailStr
    Division: str
    device_id: Optional[str] = None
    device_type: Optional[str] = None

class UpdateContactRequest(BaseModel):
    device_id: str

class EmailRequest(BaseModel):
    email: str