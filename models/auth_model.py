from pydantic import BaseModel, Field

class LoginRequest(BaseModel):
    username: str
    password: str = Field(..., min_length=8)

class Token(BaseModel):
    password_changed: bool
    isPasswordExpired: bool 

class CreateUserRequest(BaseModel):
    username: str
    password: str