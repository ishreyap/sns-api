import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")

def send_email(support_request):
    """Sends an email notification when a support request is submitted."""
    try:
        sender_email = support_request["email"]
        receiver_email = SMTP_USERNAME  # Admin email
        msg = MIMEMultipart()
        msg["From"] = sender_email
        msg["To"] = receiver_email
        msg["Subject"] = "New Help & Support Request"
        msg["Reply-To"] = sender_email  # Replies go directly to the user

        body = f"""
        New support request received:

        Name: {support_request['first_name']} {support_request['last_name']}
        Email: {support_request['email']}
        Company: {support_request['company'] or 'N/A'}
        Position: {support_request['position'] or 'N/A'}
        
        Message:
        {support_request['message']}
        """

        msg.attach(MIMEText(body, "plain"))

        # Send email securely
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()  # Secure connection
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.sendmail(sender_email, receiver_email, msg.as_string())

    except Exception as e:
        print(f"Failed to send email: {e}")
