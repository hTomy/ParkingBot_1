import os

# DB and model config
POSTGRES_URI = os.getenv("POSTGRES_URI", "postgresql+psycopg2://user:password@localhost:5432/parking_db")
WEAVIATE_COLLECTION = os.getenv("WEAVIATE_COLLECTION", "ParkingDocs")
WEAVIATE_TEXT_KEY = os.getenv("WEAVIATE_TEXT_KEY", "text")
MODEL = os.getenv("MODEL", "gpt-4o-mini")

# Human-in-the-loop / admin API configuration
ADMIN_API_URL = os.getenv("ADMIN_API_URL", "http://127.0.0.1:8001")

# Polling configuration for waiting synchronously for admin decisions
ADMIN_POLL_INTERVAL = float(os.getenv("ADMIN_POLL_INTERVAL", "5"))  # seconds between polls
ADMIN_POLL_TIMEOUT = float(os.getenv("ADMIN_POLL_TIMEOUT", "600"))  # total seconds to wait before timing out
