from fastapi import APIRouter, HTTPException, Request, Query
from typing import Optional
from helpers.auth_helper import extract_token_from_cookies, verify_jwt
from helpers.notification_helper import get_db_connection
import logging

# Configure logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.ERROR)

router = APIRouter(
    prefix="/api/dashboard",
    tags=["Dashboard"]
)

def execute_query(cursor, query: str, params: Optional[tuple] = None):
    """Helper function to execute a SQL query and fetch results."""
    cursor.execute(query, params or ())
    return cursor.fetchone()

@router.get("/stats")
def get_summary(request: Request):
    try:
        # Extract and verify JWT token
        token = extract_token_from_cookies(request)
        verify_jwt(token)

        # Connect to the database
        conn = get_db_connection()
        cursor = conn.cursor()

        # Queries for different stats
        queries = {
            "all_time": "SELECT COUNT(*) FROM device_workflows;",
            "daily": """
                SELECT COUNT(*)
                FROM device_workflows dw
                JOIN workflow w ON dw.workflow_id = w.unique_id
                WHERE w.time >= CURRENT_DATE;
            """,
            "weekly": """
                SELECT COUNT(*)
                FROM device_workflows dw
                JOIN workflow w ON dw.workflow_id = w.unique_id
                WHERE DATE_TRUNC('week', w.time) = DATE_TRUNC('week', CURRENT_DATE);
            """,
            "monthly": """
                SELECT COUNT(*)
                FROM device_workflows dw
                JOIN workflow w ON dw.workflow_id = w.unique_id
                WHERE DATE_TRUNC('month', w.time) = DATE_TRUNC('month', CURRENT_DATE);
            """,
            "scheduled": """
                SELECT COUNT(*)
                FROM device_workflows dw
                JOIN workflow w ON dw.workflow_id = w.unique_id
                WHERE w.workflow_type = 'scheduled';
            """
        }

        # Execute queries and fetch results
        results = {key: execute_query(cursor, query)[0] for key, query in queries.items()}

        return {
            "sections": {
                "all_time": {"count": results["all_time"]},
                "daily": {"count": results["daily"]},
                "weekly": {"count": results["weekly"]},
                "monthly": {"count": results["monthly"]},
                "scheduled": {"count": results["scheduled"]},
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        cursor.close()
        conn.close()

@router.get("/stats/view")
def get_section_details(request: Request, section: str = Query(...)):
    try:
        # Extract and verify JWT token
        token = extract_token_from_cookies(request)
        verify_jwt(token)

        # Connect to the database
        conn = get_db_connection()
        cursor = conn.cursor()

        # Mapping section to filter conditions
        filter_conditions = {
            "all_time": "",
            "daily": "JOIN workflow w ON dw.workflow_id = w.unique_id WHERE w.time >= CURRENT_DATE",
            "weekly": "JOIN workflow w ON dw.workflow_id = w.unique_id WHERE DATE_TRUNC('week', w.time) = DATE_TRUNC('week', CURRENT_DATE)",
            "monthly": "JOIN workflow w ON dw.workflow_id = w.unique_id WHERE DATE_TRUNC('month', w.time) = DATE_TRUNC('month', CURRENT_DATE)",
            "scheduled": "JOIN workflow w ON dw.workflow_id = w.unique_id WHERE w.workflow_type = 'scheduled'",
        }

        if section not in filter_conditions:
            raise HTTPException(status_code=400, detail="Invalid section value")

        filter_condition = filter_conditions[section]

        # Total Acknowledgements
        total_ack_query = f"""
            SELECT COUNT(*)
            FROM device_workflows dw
            {filter_condition};
        """
        total_acknowledgements = execute_query(cursor, total_ack_query)[0] or 0

        # Failed Acknowledgements
        failed_query = f"""
            SELECT COUNT(*)
            FROM device_workflows dw
            {filter_condition} {"AND dw.ack = FALSE" if filter_condition else "WHERE dw.ack = FALSE"};
        """
        failed_count = execute_query(cursor, failed_query)[0] or 0

        # Compute rates
        failed_rate = (failed_count / total_acknowledgements) * 100 if total_acknowledgements > 0 else 0
        success_rate = 100 - failed_rate  # Success rate is the complement of the failed rate

        return {
            "section": section,
            "details": {
                "total_acknowledgements": total_acknowledgements,
                "failed_rate": round(failed_rate, 2),
                "success_rate": round(success_rate, 2),
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        cursor.close()
        conn.close()

@router.get("/engagement/response_time")
def get_average_response_time(request: Request):
    try:
        token = extract_token_from_cookies(request)
        verify_jwt(token)

        conn = get_db_connection()
        cursor = conn.cursor()

        # Query for average response time using workflow time and acknowledged time
        query = """
            SELECT AVG(EXTRACT(EPOCH FROM (dw.acknowledged_at - dw.created_at))) 
            FROM device_workflows dw
            WHERE dw.ack = TRUE;
        """
        avg_response_time = execute_query(cursor, query)[0] or 0

        # Convert response time to hours, minutes, and seconds
        hours = int(avg_response_time // 3600)
        minutes = int((avg_response_time % 3600) // 60)
        seconds = int(avg_response_time % 60)

        return {
            "average_response_time": f"{hours}h {minutes}m {seconds}s"
        }

    except Exception as e:
        logger.error(f"Error in get_average_response_time: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        cursor.close()
        conn.close()

@router.get("/engagement/acknowledgment_breakdown")
def get_acknowledgment_breakdown(request: Request, filter_by: str = Query(...)):
    try:
        token = extract_token_from_cookies(request)
        verify_jwt(token)

        conn = get_db_connection()
        cursor = conn.cursor()

        valid_filters = ["device_type", "division"]
        if filter_by not in valid_filters:
            raise HTTPException(status_code=400, detail="Invalid filter value")

        query = f"""
            SELECT d.{filter_by}, COUNT(*) AS total, 
            SUM(CASE WHEN dw.ack = FALSE THEN 1 ELSE 0 END) AS failed
            FROM device_workflows dw
            JOIN devices d ON dw.device_id = d.device_id
            GROUP BY d.{filter_by};
        """
        cursor.execute(query)
        results = cursor.fetchall()

        breakdown = []
        for row in results:
            filter_value, total, failed = row
            failed_rate = (failed / total) * 100 if total > 0 else 0
            success_rate = 100 - failed_rate
            breakdown.append({
                filter_by: filter_value,
                "total_acknowledgements": total,
                "failed_rate": round(failed_rate, 2),
                "success_rate": round(success_rate, 2),
            })

        return {"acknowledgment_breakdown": breakdown}

    except Exception as e:
        logger.error(f"Error in get_acknowledgment_breakdown: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        cursor.close()
        conn.close()

@router.get("/engagement/acknowledgment_breakdown/high_priority")
def get_high_priority_stats(request: Request):
    try:
        token = extract_token_from_cookies(request)
        verify_jwt(token)

        conn = get_db_connection()
        cursor = conn.cursor()

        query = """
            SELECT COUNT(*),
            SUM(CASE WHEN dw.ack = FALSE THEN 1 ELSE 0 END) AS failed
            FROM device_workflows dw
            JOIN workflow w ON dw.workflow_id = w.unique_id
            WHERE w.priority = 'high';
        """
        cursor.execute(query)
        result = cursor.fetchone()
        total_high_priority = result[0] or 0
        failed_high_priority = result[1] or 0

        failed_rate = (failed_high_priority / total_high_priority) * 100 if total_high_priority > 0 else 0
        success_rate = 100 - failed_rate

        return {
            "high_priority_stats": {
                "total_count": total_high_priority,
                "failed_rate": round(failed_rate, 2),
                "success_rate": round(success_rate, 2),
            }
        }

    except Exception as e:
        logger.error(f"Error in get_high_priority_stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        cursor.close()
        conn.close()
