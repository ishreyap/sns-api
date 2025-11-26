from fastapi import APIRouter, HTTPException, Request
from helpers.auth_helper import extract_token_from_cookies, verify_jwt
from helpers.notification_helper import get_db_connection

router = APIRouter(
    prefix="/api/devices",
    tags=["Devices Controller"]
)

@router.get("/")
def get_all_devices(request: Request):
    try:
        token = extract_token_from_cookies(request)
        verify_jwt(token)
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT device_id, OS_type , device_type FROM devices")
        devices = cursor.fetchall()

        if not devices:
            raise HTTPException(status_code=404, detail="No devices found")

        device_list = [
            {
                "device_id": device[0], 
                "device_name": f"{device[1]} {device[0]}",
                "device_type": device[2]
            } 
            for device in devices
        ]
        
        return {"devices": device_list}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
