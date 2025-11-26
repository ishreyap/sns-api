from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from helpers.auth_helper import  authenticate_user_ldap, create_access_token

router = APIRouter(
    prefix="/auth/login",
    tags=["Authorization Controller"]
)

@router.post("/token")
async def login(response: Response, form_data: OAuth2PasswordRequestForm = Depends()):
    try:
        username = form_data.username
        password = form_data.password

        if not username or not password:
            raise HTTPException(status_code=400, detail="Username and password are required.")

        if authenticate_user_ldap(username, password):
            access_token = create_access_token(data={"sub": username})
            
            response.set_cookie(
                key="access_token",
                value=access_token,
                httponly=True,
                max_age=3600,
                secure=True,
                samesite="None"
            )

            return {
                "message": f"User {username} authenticated successfully."
            }
        else:
            raise HTTPException(status_code=401, detail="Authentication failed.")
        
    except Exception as e:
        print(f"Error in login API: {e}")
        raise HTTPException(status_code=500, detail="An error occurred while processing the request.")

@router.post("/", status_code=status.HTTP_200_OK)
async def logout(response: Response):

    response.delete_cookie(
        key="access_token", 
        httponly=True,
        secure=True,         
        samesite="None"   
    )
    return {"message": "Logout successful"}
