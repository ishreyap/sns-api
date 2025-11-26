import uuid
import os
from fastapi import APIRouter, HTTPException, Request
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from helpers.auth_helper import extract_token_from_cookies, verify_jwt
from helpers.notification_helper import get_db_connection
from models.faq_model import FAQCreateRequest, FAQSearchRequest

router = APIRouter(
    prefix="/api/faqs",
    tags=["FAQs Controller"]
)

@router.get("/")
def get_all_faqs(request: Request):
    try:
        token = extract_token_from_cookies(request)
        verify_jwt(token)
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, question, answer, search_count FROM faqs ORDER BY search_count DESC")
        faqs = cursor.fetchall()
        
        if not faqs:
            raise HTTPException(status_code=404, detail="No FAQs found")
        
        faq_list = [
            {"id": faq[0], "question": faq[1], "answer": faq[2], "search_count": faq[3]} 
            for faq in faqs
        ]
        
        return {"faqs": faq_list}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        cursor.close()
        conn.close()

@router.get("/{faq_id}")
def get_faq_by_id(faq_id: int, request: Request):
    try:
        token = extract_token_from_cookies(request)
        verify_jwt(token)
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, question, answer, search_count FROM faqs WHERE id = %s", (faq_id,))
        faq = cursor.fetchone()
        
        if not faq:
            raise HTTPException(status_code=404, detail="FAQ not found")
        
        # Update search count
        cursor.execute("UPDATE faqs SET search_count = search_count + 1 WHERE id = %s", (faq_id,))
        conn.commit()
        
        return {"id": faq[0], "question": faq[1], "answer": faq[2], "search_count": faq[3] + 1}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        cursor.close()
        conn.close()

@router.post("/search")
def search_faqs(query: FAQSearchRequest, request: Request):
    try:
        token = extract_token_from_cookies(request)
        verify_jwt(token)
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if not query.query:
            return get_all_faqs(request)
        
        search_query = f"%{query.query.lower()}%"
        cursor.execute(
            "SELECT id, question, answer, search_count FROM faqs WHERE LOWER(question) LIKE %s OR LOWER(answer) LIKE %s ORDER BY search_count DESC",
            (search_query, search_query)
        )
        faqs = cursor.fetchall()
        
        if not faqs:
            raise HTTPException(status_code=404, detail="No matching FAQs found")
        
        faq_list = [
            {"id": faq[0], "question": faq[1], "answer": faq[2], "search_count": faq[3]} 
            for faq in faqs
        ]
        
        # Update search count
        for faq in faqs:
            cursor.execute("UPDATE faqs SET search_count = search_count + 1 WHERE id = %s", (faq[0],))
        conn.commit()
        
        return {"results": faq_list}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        cursor.close()
        conn.close()

@router.post("/submit")
def submit_question(data: FAQCreateRequest, request: Request):
    try:
        token = extract_token_from_cookies(request)
        verify_jwt(token)
        
        # Send email notification
        send_email_notification(data.question)
        
        return {"message": "Question submitted successfully"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def send_email_notification(question):
    sender_email = os.getenv("SMTP_SENDER_EMAIL", "iamabjunior@gmail.com")
    receiver_email = "aditya.b@cybotronics.com"
    smtp_server = os.getenv("SMTP_SERVER", "smtp.example.com")
    smtp_port = int(os.getenv("SMTP_PORT", 587))
    smtp_username = os.getenv("SMTP_USERNAME")
    smtp_password = os.getenv("SMTP_PASSWORD")
    
    subject = "New FAQ Submission"
    body = f"A new FAQ has been submitted:\n\nQuestion: {question}\n\nPlease review and respond."
    
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))
    
    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_username, smtp_password)
            server.sendmail(sender_email, receiver_email, msg.as_string())
    except Exception as e:
        print(f"Failed to send email: {e}")
