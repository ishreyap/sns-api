from fastapi import APIRouter, HTTPException, Request
from models.support_model import SupportRequest
from helpers.email_helper import send_email
from helpers.auth_helper import extract_token_from_cookies, verify_jwt


router = APIRouter(
    prefix="/api/help_support",
    tags=["Help & Support"],
)

# Temporary in-memory storage (Replace with DB in production)
support_requests = []

@router.post("/submit", response_model=dict)
def submit_support_request(
    data: SupportRequest, request: Request
):
    """Submit a support request with authentication."""
    token = extract_token_from_cookies(request)
    verify_jwt(token)  # Ensure user is authenticated

    new_request = {
        "id": len(support_requests) + 1,
        "first_name": data.first_name,
        "last_name": data.last_name,
        "email": data.email,
        "company": data.company,
        "position": data.position,
        "message": data.message
    }
    support_requests.append(new_request)

    # Send email notification
    try:
        send_email(new_request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send email: {str(e)}")

    return {"message": "Support request submitted successfully", "request": new_request}

@router.get("/", response_model=list)
def get_all_support_requests(request: Request):
    """Retrieve all submitted support requests (Authenticated users only)."""
    token = extract_token_from_cookies(request)
    verify_jwt(token)  # Ensure user is authenticated

    return support_requests