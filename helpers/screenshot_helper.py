import json
import logging
from typing import List
from config import GCP_PROJECT_ID, PUBSUB_TOPIC
from helpers.notification_helper import get_db_connection
from google.cloud import pubsub_v1
from datetime import datetime, timedelta

publisher = pubsub_v1.PublisherClient()
topic_path = publisher.topic_path(GCP_PROJECT_ID, PUBSUB_TOPIC)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_device_name(device_id):
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        query = "SELECT device_name FROM devices WHERE device_id = %s"
        cursor.execute(query, (device_id,))
        
        result = cursor.fetchone()
        return result[0] if result else None
    except Exception as e:
        logger.error(f"Error fetching device name: {str(e)}")
        return None
    finally:
        if connection:
            cursor.close()
            connection.close()

def store_screenshot_request_screenshots(device_id):
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        
        query = "INSERT INTO screenshots (device_id) VALUES (%s) RETURNING id;"
        cursor.execute(query, (device_id,))
        screenshot_id = cursor.fetchone()[0]
        connection.commit()
        
        return screenshot_id
    except Exception as e:
        logger.error(f"Error storing screenshot request: {str(e)}")
        return None
    finally:
        if connection:
            cursor.close()
            connection.close()

def update_screenshot(screenshot_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        query = "UPDATE screenshots SET ispublished = TRUE WHERE id = %s RETURNING id;"
        cursor.execute(query, (screenshot_id,))
        result = cursor.fetchone()
        conn.commit()

        return result
    except Exception as e:
        logger.error(f"Error update screenshot request: {str(e)}")
        return None
    finally:
        if conn:
            cursor.close()
            conn.close()

def get_devices_by_division_names(division_names: List[str]):
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        
        query = """
        SELECT d.device_id, d.device_name FROM devices d
        JOIN division_devices dd ON d.device_id = dd.device_id
        JOIN divisions dv ON dd.division_id = dv.division_id
        WHERE dv.division_name = ANY(%s)
        """
        cursor.execute(query, (division_names,))
        
        devices = cursor.fetchall()
        return [{"device_id": row[0], "device_name": row[1]} for row in devices]
    except Exception as e:
        logger.error(f"Error fetching devices for divisions: {str(e)}")
        return []
    finally:
        if connection:
            cursor.close()
            connection.close()

def publish_message_screenshot(device_name: str, screenshot_id: str):
    data = {
        "device_name": device_name,
        "screenshot_id": screenshot_id
    }
    
    data_bytes = json.dumps(data).encode("utf-8")
    future = publisher.publish(topic_path, data_bytes)
    message_id = future.result()

    return {"status": "Message published", "message_id": message_id}

def store_screenshot_request(device_id, interval_minutes=None, is_enabled=False):
    try:
        with get_db_connection() as connection:
            with connection.cursor() as cursor:
                query = """
                INSERT INTO auto_screenshot (device_id, interval_minutes, is_enabled, timestamp)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (device_id) 
                DO UPDATE SET 
                    interval_minutes = EXCLUDED.interval_minutes, 
                    is_enabled = EXCLUDED.is_enabled,
                    timestamp = EXCLUDED.timestamp
                RETURNING id;
                """
                cursor.execute(query, (device_id, interval_minutes, is_enabled, datetime.now()))
                id = cursor.fetchone()[0]
                connection.commit()
                return id

    except Exception as e:
        logger.error(f"Error storing screenshot request: {str(e)}")
        return None

def process_device_timer(device_id: str, interval: int):
    device_name = get_device_name(device_id)
    if not device_name:
        return {"device_id": device_id, "status": "Device not found"}

    screenshot_id = store_screenshot_request(
        device_id=device_id,
        interval_minutes=interval,
        is_enabled=True
    )

    if not screenshot_id:
        return {"device_id": device_id, "device_name": device_name, "status": "Failed to store screenshot request"}

    return {"device_id": device_id, "device_name": device_name, "status": "Timer started", "interval_minutes": interval}

def monitor_screenshots():
    while True:
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            current_time = datetime.now()

            query = """
            SELECT device_id, interval_minutes, timestamp 
            FROM auto_screenshot 
            WHERE is_enabled = TRUE;
            """
            cursor.execute(query)
            records = cursor.fetchall()
            print(f"Found {len(records)} timed screenshot")

            for device_id, interval_minutes, timestamp in records:
                if timestamp is None:
                    continue

                next_screenshot_time = timestamp + timedelta(minutes=interval_minutes)
                if current_time >= next_screenshot_time:
                    screenshot_id = store_screenshot_request_screenshots(device_id)
                    if screenshot_id:
                        device_name = get_device_name(device_id)

                        if publish_message_screenshot(device_name, screenshot_id):
                            if update_timestamp(device_id):

                                if update_screenshot(screenshot_id):
                                    print("Screenshot updated")
                                else:
                                    print("Error updating screenshot")
                            else:
                                print("Error updating timestamp")

                        else:
                            print("Error publishing message")

            conn.commit()
        except Exception as e:
            print(f"Error in monitoring: {str(e)}")
        finally:
            if conn:
                cursor.close()
                conn.close()
        
def update_timestamp(device_id):
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        query = """UPDATE auto_screenshot SET timestamp = %s WHERE device_id = %s;"""
        cursor.execute(query, (datetime.now(),device_id,))
        conn.commit()
        
        return cursor.rowcount > 0 
    except Exception as e:
        logger.error(f"Error updating screenshot timestamp: {str(e)}", exc_info=True)
        return False
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def get_all_devices():
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        
        query = "SELECT device_id, device_name FROM devices;"
        cursor.execute(query)
        
        devices = cursor.fetchall()
        return [{"device_id": row[0], "device_name": row[1]} for row in devices]
    except Exception as e:
        logger.error(f"Error fetching all devices: {str(e)}")
        return []
    finally:
        if connection:
            cursor.close()
            connection.close()