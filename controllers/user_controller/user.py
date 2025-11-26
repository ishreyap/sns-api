from helpers.auth_helper import extract_token_from_cookies, verify_jwt
from fastapi import APIRouter, HTTPException, Request

router = APIRouter(
    prefix="/auth",
    tags=["user Controller"]
)

@router.get("/validate")
def validate_user(request: Request):
    try:
        token = extract_token_from_cookies(request)
        verify_jwt(token)
        return {"message": "User is valid"}
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid or missing token")