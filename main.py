from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from controllers.notifications.notification_controller import router as notification_router
from controllers.divisions.divisions_controller import router as divisions_router
from controllers.devices.devices_controller import router as devices_router
from controllers.auth_controller.auth import router as auth_router
#from controllers.auth_controller.password_controller import router as password_router
from controllers.user_controller.user import router as user_router
from controllers.dashboard.dashboard_controller import router as dashboard_router
from controllers.contacts.contact_controller import router as contact_router
from controllers.screenshot.screenshot_api import router as screenshots
from controllers.FAQs.FAQs_controller import router as FAQs
from controllers.Help_Support.help_support_controller import router as help_support

import threading
from helpers.notification_helper import process_scheduled_notifications
from helpers.screenshot_helper import monitor_screenshots

app = FastAPI()

allowed_origins = [
    "https://sns-api-498807929429.us-central1.run.app",
    "http://localhost:5173",
    "http://127.0.0.1:8000",
    "https://api.sns.mdm.studio",
    "https://sns-frontend-498807929429.us-central1.run.app",
    "https://sns.mdm.studio"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True, 
    allow_methods=["*"], 
    allow_headers=["*"],  
)

app.include_router(auth_router)
#app.include_router(password_router)
app.include_router(notification_router)
app.include_router(divisions_router)
app.include_router(devices_router)
app.include_router(user_router)
app.include_router(dashboard_router)
app.include_router(contact_router)
app.include_router(screenshots)
app.include_router(FAQs)
app.include_router(help_support)

@app.get("/")
def read_root():
    return {"message": "API is running."}

threading.Thread(target=process_scheduled_notifications, daemon=True).start()
threading.Thread(target=monitor_screenshots, daemon=True).start()
