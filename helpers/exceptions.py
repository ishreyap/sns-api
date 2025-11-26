from fastapi import HTTPException

CREDENTIAL_EXCEPTION = HTTPException(
    status_code = 403,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"}
)