from datetime import datetime
from fastapi import FastAPI, HTTPException, APIRouter, Request
from helpers.notification_helper import get_db_connection
from google.cloud import pubsub_v1
from config import GCP_PROJECT_ID, PUBSUB_TOPIC
import logging
from typing import List
from helpers.screenshot_helper import get_device_name, get_devices_by_division_names, process_device_timer, publish_message_screenshot, store_screenshot_request_screenshots, update_screenshot,get_all_devices
from models.screenshot_model import ScreenshotTimerRequest, StopTimerRequest

publisher = pubsub_v1.PublisherClient()
topic_path = publisher.topic_path(GCP_PROJECT_ID, PUBSUB_TOPIC)

app = FastAPI()

router = APIRouter(
    prefix="/api/screenshots",
    tags=["screenshots(Under Development)"],
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@router.post("/screenshot")
async def screenshot_active_window(device_ids: List[str] = [], division_names: List[str] = [], request: Request = None):
    responses = []
    
    if division_names:
        division_devices = get_devices_by_division_names(division_names)
        device_ids.extend([device["device_id"] for device in division_devices])
    
    if not device_ids:
        raise HTTPException(status_code=404, detail="No valid devices found.")
    
    for device_id in set(device_ids):
        device_name = get_device_name(device_id)
        if not device_name:
            logger.error(f"Device ID {device_id} not found in the database.")
            continue
        
        screenshot_id = store_screenshot_request_screenshots(device_id)
        if screenshot_id is None:
            continue
        
        publish_response = publish_message_screenshot(device_name, screenshot_id)
        update = update_screenshot(screenshot_id)
        responses.append({
            "device_name": device_name,
            "screenshot_id": screenshot_id,
            "publish_response": publish_response
        })
    
    if not responses:
        raise HTTPException(status_code=404, detail="No valid devices processed.")
    
    return {"results": responses}

@router.get("/screenshots")
async def get_screenshot_details():
    try:
        with get_db_connection() as connection:
            with connection.cursor() as cursor:
                
                query = """
                SELECT s.id, s.device_id, d.os_type, s.file_name, s.storage_url, s.timestamp, 
                       COALESCE(a.interval_minutes, 0), COALESCE(a.is_enabled, false)
                FROM screenshots s
                JOIN devices d ON s.device_id = d.device_id
                LEFT JOIN auto_screenshot a ON s.device_id = a.device_id
                ORDER BY s.timestamp DESC;
                """
                cursor.execute(query)
                screenshots = cursor.fetchall()

                screenshot_details = [
                    {
                        "screenshot_id": row[0],
                        "device_id": row[1],
                        "device_info": f"{row[2]} {row[1]}", 
                        "file_name": row[3],
                        "storage_url": row[4],
                        "created_at": row[5],
                        "interval_minutes": row[6],
                        "is_enabled": row[7]
                    } 
                    for row in screenshots
                ]

        return {"screenshot_details": screenshot_details}

    except Exception as e:
        logger.error(f"Error fetching screenshot details: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch screenshot details.")

@router.post("/start-timer")
async def start_screenshot_timer(timer: ScreenshotTimerRequest):
    if timer.interval_minutes < 1:
        raise HTTPException(status_code=400, detail="Interval must be at least 1 minute")

    results = []
    try:
        if timer.type == "users":
            results = [process_device_timer(device_id, timer.interval_minutes) for device_id in timer.device_ids]

        elif timer.type == "divisions":
            division_devices = get_devices_by_division_names(timer.division_names)
            results = [process_device_timer(device["device_id"], timer.interval_minutes) for device in division_devices]

        elif timer.type == "all":
            with get_db_connection() as connection:
                with connection.cursor() as cursor:
                    query = """
                    UPDATE auto_screenshot 
                    SET interval_minutes = %s, is_enabled = TRUE, timestamp = %s
                    RETURNING device_id;
                    """
                    cursor.execute(query, (timer.interval_minutes, datetime.now()))
                    results = cursor.fetchall()


        else:
            raise HTTPException(status_code=400, detail="Invalid timer type")

        return {"results": results}

    except Exception as e:
        logger.error(f"Error starting timer: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.post("/stop-timer")
async def stop_screenshot_timer(stimer: StopTimerRequest):
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        
        if stimer.stop_all:
            query = """ UPDATE auto_screenshot SET is_enabled = FALSE RETURNING id, device_id; """
            cursor.execute(query)
        elif stimer.division_names:
            division_devices = get_devices_by_division_names(stimer.division_names)
            device_ids = [device["device_id"] for device in division_devices]
            query = """ UPDATE auto_screenshot SET is_enabled = FALSE WHERE device_id = ANY(%s) RETURNING id, device_id; """
            cursor.execute(query, (device_ids,))
        elif device_ids:
            query = """ UPDATE auto_screenshot SET is_enabled = FALSE WHERE device_id = ANY(%s) RETURNING id, device_id; """
            cursor.execute(query, (device_ids,))
        else:
            raise HTTPException(status_code=400, detail="No device IDs or division names provided")
        
        results = cursor.fetchall()
        connection.commit()
        
        if not results:
            raise HTTPException(status_code=404, detail="No active timers found for the provided devices or divisions")
        
        stopped_timers = [{"id": row[0], "device_id": row[1]} for row in results]
        
        return {"status": "Timers stopped", "stopped_timers": stopped_timers}
        
    except Exception as e:
        logger.error(f"Error stopping timers: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if connection:
            cursor.close()
            connection.close()
@router.post("/screenshot/all")
async def screenshot_all_devices():
    all_devices = get_all_devices()
    device_ids = [device["device_id"] for device in all_devices]
    
    if not device_ids:
        raise HTTPException(status_code=404, detail="No devices found.")
    
    return await screenshot_active_window(device_ids=device_ids)
