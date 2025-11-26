import uuid
from fastapi import APIRouter, HTTPException, Request
from helpers.auth_helper import extract_token_from_cookies, verify_jwt
from helpers.notification_helper import get_db_connection
from models.notification_model import DivisionCreateRequest
router = APIRouter(
    prefix="/api/divisions",
    tags=["divisions Controller"]
)

@router.post("/create")
def create_division(division: DivisionCreateRequest, request: Request):
    try:
        token = extract_token_from_cookies(request)
        verify_jwt(token)
        divisions_id = str(uuid.uuid4())
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO divisions (division_id, division_name) 
            VALUES (%s, %s) RETURNING division_id
            """,
            (divisions_id, division.Division_name)
        )
        division_id = cursor.fetchone()[0]

        for device_id in division.device_ids:
            cursor.execute(
                """
                INSERT INTO division_devices (division_id, device_id) 
                VALUES (%s, %s)
                """,
                (division_id, device_id)
            )

        conn.commit()

        return {"message": "Division created successfully", "division_id": division_id}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@router.get("/")
def get_all_divisions(request: Request):
    try:
        token = extract_token_from_cookies(request)
        verify_jwt(token)
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT division_id, division_name FROM divisions")
        divisions = cursor.fetchall()

        if not divisions:
            raise HTTPException(status_code=404, detail="No divisions found")

        division_list = [{"division_id": division[0], "division_name": division[1]} for division in divisions]
                
        return {"divisions": division_list}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        cursor.close()
        conn.close()

@router.get("/unassigned-devices")
def get_unassigned_users(request: Request):
    try:
        token = extract_token_from_cookies(request)
        verify_jwt(token)
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
        SELECT d.device_id, d.OS_type
        FROM devices d
        LEFT JOIN division_devices gd ON d.device_id = gd.device_id
        WHERE gd.device_id IS NULL
        """)
        devices = cursor.fetchall()

        if not devices:
            raise HTTPException(status_code=404, detail="No unassigned devices found")

        device_list = [{"user_id": device[0], "user_name": f"{device[1]} {device[0]}"} for device in devices]

        return {"unassigned_users": device_list}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        cursor.close()
        conn.close()
