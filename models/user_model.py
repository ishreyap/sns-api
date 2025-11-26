from pydantic import BaseModel

class SignupRequest(BaseModel):
    username: str
    password: str

class UserResponseWithId(BaseModel):
    id: int
    username: str

class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str

class UpdatePasswordRequest(BaseModel):
    newPassword: str
