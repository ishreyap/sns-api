from datetime import datetime, timedelta
import bcrypt
from fastapi import APIRouter, HTTPException, Request, status
from helpers.auth_helper import authenticate_user, extract_token_from_cookies, verify_jwt
from helpers.notification_helper import get_db_connection
from helpers.user_helper import get_user_info
from models.user_model import ChangePasswordRequest, UpdatePasswordRequest

router = APIRouter(
    prefix="/auth/pass",
    tags=["Password Controller"]
)

@router.post("/change-password")
def change_password(changepass: ChangePasswordRequest, request: Request):
    token = extract_token_from_cookies(request)
    verify_jwt(token)
    user_info = get_user_info(request)
    if not user_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="User not found"
        )

    connection = get_db_connection()
    cursor = connection.cursor()

    if not authenticate_user(user_info.username, changepass.old_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Incorrect old password"
        )

    cursor.execute(
        "SELECT password_last_updated FROM users WHERE username = %s;",
        (user_info.username,)
    )
    result = cursor.fetchone()
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="User not found in the database"
        )

    last_updated = result[0]  
    current_time = datetime.utcnow()

    if current_time < last_updated + timedelta(days=1):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password cannot be changed within 1 day of the last update"
        )

    cursor.execute(
        """
        SELECT hashed_password FROM password_history
        WHERE username = %s
        ORDER BY created_at DESC
        LIMIT 12;
        """,
        (user_info.username,)
    )
    password_history = cursor.fetchall()

    for old_password in password_history:
        if bcrypt.checkpw(
            changepass.new_password.encode("utf-8"),
            old_password[0].encode("utf-8")
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New password must not match the last 12 passwords"
            )

    new_hashed_password = bcrypt.hashpw(
        changepass.new_password.encode("utf-8"), bcrypt.gensalt()
    ).decode("utf-8")

    cursor.execute(
        """
        UPDATE users
        SET password = %s, password_last_updated = %s
        WHERE username = %s;
        """,
        (new_hashed_password, current_time, user_info.username)
    )

    cursor.execute(
        """
        INSERT INTO password_history (username, hashed_password, created_at)
        VALUES (%s, %s, %s);
        """,
        (user_info.username, new_hashed_password, current_time)
    )

    connection.commit()

    cursor.close()
    connection.close()

    return {"message": "Password changed successfully"}


@router.post("/update-password")
def update_password(update_password_request: UpdatePasswordRequest, request: Request):
    token = extract_token_from_cookies(request)
    verify_jwt(token)
    user_info = get_user_info(request)
    if not user_info:
        raise HTTPException(status_code=404, detail="User not found")
    
    connection = get_db_connection()
    cursor = connection.cursor()

    new_hashed_password = bcrypt.hashpw(update_password_request.newPassword.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    history_query = """
    INSERT INTO password_history (username, hashed_password)
    VALUES (%s, %s);
    """
    cursor.execute(history_query, (user_info.username, new_hashed_password))

    update_query = """
    UPDATE users 
    SET password = %s, password_last_updated = CURRENT_TIMESTAMP, password_changed = TRUE
    WHERE username = %s;
    """
    cursor.execute(update_query, (new_hashed_password, user_info.username))

    connection.commit()

    cursor.close()
    connection.close()

    return {"message": "Password updated successfully"}
