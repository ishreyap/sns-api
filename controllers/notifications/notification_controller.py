from fastapi import APIRouter, HTTPException, Request
from helpers.auth_helper import extract_token_from_cookies, verify_jwt
from helpers.notification_helper import fetch_workflow_records, format_workflow_records, get_db_connection, get_target_devices, insert_device_workflows, insert_workflow
from models.notification_model import Notification_type, Workflow, WorkflowUpdate

router = APIRouter(
    prefix="/api/workflow",
    tags=["workflow Controller"]
)

@router.post("/send-workflows")
def create_workflow(workflow: Workflow, request: Request):
    try:
        token = extract_token_from_cookies(request)
        verify_jwt(token)
        conn = get_db_connection()
        cursor = conn.cursor()

        workflow_id = insert_workflow(cursor, workflow)

        target_devices = get_target_devices(cursor, workflow)

        insert_device_workflows(cursor, workflow_id, target_devices)

        conn.commit()
        return {"message": "workflow created successfully", "workflow_id": workflow_id}

    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        cursor.close()
        conn.close()

@router.get("/workflows/history")
def get_workflow_history(request: Request):
    try:
        token = extract_token_from_cookies(request)
        verify_jwt(token)
        conn = get_db_connection()
        cursor = conn.cursor()

        records = fetch_workflow_records(cursor)

        if not records:
            raise HTTPException(status_code=404, detail="No workflows found")

        workflows = format_workflow_records(records)

        return {"workflows": workflows}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()

@router.delete("/workflows/{workflow_id}")
def delete_workflow(workflow_id: str, request: Request):
    token = extract_token_from_cookies(request)
    verify_jwt(token)
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("DELETE FROM device_workflows WHERE workflow_id = %s", (workflow_id,))
        cursor.execute("DELETE FROM workflow WHERE unique_id = %s RETURNING unique_id", (workflow_id,))
        deleted_id = cursor.fetchone()

        if not deleted_id:
            raise HTTPException(status_code=404, detail="workflow not found")

        conn.commit()

        return {"message": "workflow deleted successfully", "workflow_id": workflow_id}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        cursor.close()
        conn.close()

@router.put("/workflows/{workflow_id}")
async def update_workflow(workflow_id: str, workflow_update: WorkflowUpdate, request: Request):
    try:
        token = extract_token_from_cookies(request)
        verify_jwt(token)
        
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT published, notification_type FROM workflow WHERE unique_id = %s",
            (workflow_id,)
        )
        result = cursor.fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail="Workflow not found")
            
        if result[0]:  
            raise HTTPException(
                status_code=400, 
                detail="Cannot update a workflow that has already been published"
            )

        update_fields = []
        update_values = []
        
        if workflow_update.name is not None:
            update_fields.append("name = %s")
            update_values.append(workflow_update.name)
            
        if workflow_update.body is not None:
            update_fields.append("body = %s")
            update_values.append(workflow_update.body)
            
        if workflow_update.priority is not None:
            update_fields.append("priority = %s")
            update_values.append(workflow_update.priority)
            
        if workflow_update.status is not None:
            if workflow_update.status not in ['live', 'draft', 'cancelled']:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid status. Must be one of: live, draft, cancelled"
                )
            update_fields.append("status = %s")
            update_values.append(workflow_update.status)

        if workflow_update.WorkflowType is not None:
            update_fields.append("workflow_type = %s")
            update_values.append(workflow_update.WorkflowType)
            
        if workflow_update.timestamp is not None:
            update_fields.append("time = %s")
            update_values.append(workflow_update.timestamp)

        if workflow_update.NotificationType is not None:
            new_notification_type = workflow_update.NotificationType
            current_notification_type = result[1]
            
            if new_notification_type != current_notification_type:
                cursor.execute(
                    "DELETE FROM device_workflows WHERE workflow_id = %s",
                    (workflow_id,)
                )
                
                if workflow_update.ids is None and new_notification_type in [Notification_type.SELECT, Notification_type.GROUP]:
                    raise HTTPException(
                        status_code=400,
                        detail=f"'ids' must be provided when notification type is {new_notification_type}"
                    )
                
                target_devices = get_target_devices(cursor, WorkflowUpdate(
                    NotificationType=new_notification_type,
                    ids=workflow_update.ids
                ))
                
                insert_device_workflows(cursor, workflow_id, target_devices)
                
                update_fields.append("notification_type = %s")
                update_values.append(
                    "Single" if new_notification_type == Notification_type.SELECT and len(workflow_update.ids or []) == 1
                    else "Multi Select" if new_notification_type == Notification_type.SELECT
                    else new_notification_type
                )

        if not update_fields:
            raise HTTPException(
                status_code=400,
                detail="No fields provided for update"
            )

        query = f"""
            UPDATE workflow 
            SET {", ".join(update_fields)}
            WHERE unique_id = %s
            RETURNING unique_id, name, workflow_type, time, status, body, priority, notification_type
        """
        
        update_values.append(workflow_id)
        cursor.execute(query, tuple(update_values))
        
        updated_workflow = cursor.fetchone()
        conn.commit()

        return {
            "message": "Workflow updated successfully",
            "workflow": {
                "workflow_id": updated_workflow[0],
                "name": updated_workflow[1],
                "type": updated_workflow[2],
                "schedule_time": updated_workflow[3],
                "status": updated_workflow[4],
                "body": updated_workflow[5],
                "priority": updated_workflow[6],
                "notification_type": updated_workflow[7]
            }
        }

    except Exception as e:
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@router.get("/workflows/{workflow_id}/acks")
def get_workflow_acks(workflow_id: str, request: Request):
    try:
        # token = extract_token_from_cookies(request)
        # verify_jwt(token)
        
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT dw.device_id, dw.ack, d.os_type
            FROM device_workflows dw
            JOIN devices d ON dw.device_id = d.device_id
            WHERE dw.workflow_id = %s
        """, (workflow_id,))
        
        acks = cursor.fetchall()
        
        if not acks:
            raise HTTPException(status_code=404, detail="No acknowledgements found for this workflow")

        return {
            "acks": [
                {
                    "device_id": ack[0],
                    "acknowledged": ack[1],
                    "device_name": f"{ack[2]} {ack[0]}"
                } for ack in acks
            ]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()