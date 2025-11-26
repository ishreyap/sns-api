from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from helpers.auth_helper import create_user
from models.auth_model import CreateUserRequest

router = APIRouter(
    prefix="/auth/signup",
    tags=["Signup Controller"]
)
@router.post("/create-user")
async def create_user_ldap(request: CreateUserRequest):
    try:
        username = request.username
        password = request.password

        if not username or not password:
            raise HTTPException(status_code=400, detail="Username and password are required.")

        if create_user(username, password):
            return JSONResponse(content={"message": f"User {username} created successfully."}, status_code=201)
        else:
            raise HTTPException(status_code=500, detail="User creation failed.")
    except Exception as e:
        print(f"Error in create-user API: {e}")
        raise HTTPException(status_code=500, detail="An error occurred while processing the request.")
