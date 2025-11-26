import os
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    "host": "localhost or Your port",
    "user": "postgres",
    "password": "password",
    "database": "database name "
}
GCP_PROJECT_ID = "Your Project ID"
PUBSUB_TOPIC = "Topic Name"
GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")



