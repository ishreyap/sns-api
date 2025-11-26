import time
from fastapi import HTTPException
from google.cloud import pubsub_v1
from config import DB_CONFIG, GCP_PROJECT_ID, PUBSUB_TOPIC, GOOGLE_APPLICATION_CREDENTIALS
import psycopg2
import json
import os
from datetime import datetime


os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = GOOGLE_APPLICATION_CREDENTIALS

publisher = pubsub_v1.PublisherClient()
topic_name = f"projects/{GCP_PROJECT_ID}/topics/{PUBSUB_TOPIC}"

def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)

#publish messgage to pub/sub
def publish_message(notification_id,name , body, priority, device_id, timestamp):
    message = {
        "notification_id": notification_id,
        "name": name,
        "body": body,
        "priority": priority,
        "device_id": device_id,
        "timestamp": timestamp.isoformat()
    }
    try:
        future = publisher.publish(topic_name, json.dumps(message).encode("utf-8"))
        message_id = future.result()
        print(f"Published notification {notification_id} to device {device_id} with message ID: {message_id}")
    except Exception as e:
        print(f"Error publishing message: {e}")

#handle scheduled workflows
def process_scheduled_notifications():
    while True:
        try:
            current_time = datetime.now()
            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT 
                w.unique_id, 
                w.name,
                w.body, 
                w.priority, 
                w.time AS timestamp, 
                dw.device_id
                FROM 
                workflow w
                JOIN 
                device_workflows dw 
                ON w.unique_id = dw.workflow_id
                WHERE w.time <= %s AND w.published = FALSE AND w.status = 'live'
                """, (current_time,))

            notifications = cursor.fetchall()
            print(f"Found {len(notifications)} notifications to publish")
            for notif_id,name, body, priority, timestamp, device_id in notifications:
                publish_message(notif_id,name, body, priority, device_id, timestamp)

                cursor.execute("""
                    UPDATE workflow
                    SET published = TRUE
                    WHERE unique_id = %s
                """, (notif_id,))
            
            conn.commit()
            cursor.close()
            conn.close()
            time.sleep(5)
        except Exception as e:
            print(f"Error in background task: {e}")
            time.sleep(5)

#insert device workflows
def insert_device_workflows(cursor, workflow_id, target_devices):
    for device_info in target_devices:
        if isinstance(device_info, tuple):
            device, division_id = device_info
        else:
            device = device_info
            division_id = None

        if division_id is not None:
            cursor.execute(
                """
                INSERT INTO device_workflows (device_id, workflow_id, ack, division_id)
                VALUES (%s, %s, %s, %s)
                """,
                (device, workflow_id, False, division_id)
            )
        else:
            cursor.execute(
                """
                INSERT INTO device_workflows (device_id, workflow_id, ack)
                VALUES (%s, %s, %s)
                """,
                (device, workflow_id, False)
            )

#get target devices to create workflow
def get_target_devices(cursor, workflow):
    if workflow.NotificationType == "All":
        cursor.execute("SELECT device_id FROM devices")
        return [row[0] for row in cursor.fetchall()]

    elif workflow.NotificationType == "Division":
        if not workflow.ids or not isinstance(workflow.ids, list):
            raise HTTPException(status_code=400, detail="'ids' must be a list of division IDs for 'division' workflows.")

        target_devices = []
        for division_id in workflow.ids:
            cursor.execute(
                "SELECT device_id FROM division_devices WHERE division_id = %s;",
                (division_id,)
            )
            division_devices = [row[0] for row in cursor.fetchall()]
            target_devices.extend([(device, division_id) for device in division_devices])
        return target_devices

    elif workflow.NotificationType == "User":
        if not workflow.ids:
            raise HTTPException(status_code=400, detail="'ids' must be provided for 'select user' workflows.")
        return workflow.ids

    else:
        raise HTTPException(status_code=400, detail="Invalid NotificationType provided.")
    
#insert in workflow
def insert_workflow(cursor, workflow):
    timestamp = workflow.timestamp or datetime.now()
    status = workflow.status or 'live'

    if workflow.NotificationType == "User":
        notification_type = "Single" if len(workflow.ids) == 1 else "Multi Select"
    else:
        notification_type = workflow.NotificationType

    cursor.execute(
        """
        INSERT INTO workflow (unique_id, name, workflow_type, time, status, notification_type, ack, published, body, priority)
        VALUES (gen_random_uuid(), %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING unique_id
        """,
        (workflow.name, workflow.WorkflowType, timestamp, status, notification_type, False, False, workflow.body, workflow.priority)
    )
    return cursor.fetchone()[0]

#fetch workflows
def fetch_workflow_records(cursor):
    query = """
        SELECT unique_id AS workflow_id, workflow.name, workflow.workflow_type, workflow.time, workflow.status, workflow.body, workflow.priority,
        workflow.notification_type ,workflow.published , workflow.ack
        FROM workflow
        ORDER BY workflow.time DESC
    """
    cursor.execute(query)
    return cursor.fetchall()

def format_workflow_records(records):
    workflows = []
    for record in records:
        unique_id, name, workflow_type, schedule_time, status, body, priority, notification_type, published , ack = record
        workflow_details = {
            "workflow_id": unique_id,
            "name": name,
            "type": workflow_type,
            "schedule_time": schedule_time,
            "status": status,
            "body": body,
            "priority": priority,
            "notification_type": notification_type,
            "published": published,
            "ack": ack
        }
        workflows.append(workflow_details)
    return workflows