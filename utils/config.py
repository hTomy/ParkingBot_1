import os

POSTGRES_URI = os.getenv("POSTGRES_URI", "postgresql+psycopg2://user:password@localhost:5432/parking_db")
WEAVIATE_COLLECTION = os.getenv("WEAVIATE_COLLECTION", "ParkingDocs")
WEAVIATE_TEXT_KEY = os.getenv("WEAVIATE_TEXT_KEY", "text")
MODEL = os.getenv("MODEL", "gpt-4o-mini")