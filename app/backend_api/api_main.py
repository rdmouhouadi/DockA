import os
from fastapi import FastAPI
import psycopg2
import requests

from app.backend_api.routers.search import router as search_router

app = FastAPI(
    title="DocKA API",
    description="Document Knowledge Access API",
    version="0.1.0",
)

# Routers
app.include_router(search_router, tags=["Search"])


@app.get("/health")
def health():
    status = {
        "api": "ok",
        "postgres": "unknown",
        "elasticsearch": "unknown"
    }

    # Check Postgres
    try:
        conn = psycopg2.connect(
            host=os.getenv("POSTGRES_HOST", "postgres"),
            dbname=os.getenv("POSTGRES_DB", "docka_app"),
            user=os.getenv("POSTGRES_USER", "docka"),
            password=os.getenv("POSTGRES_PASSWORD", "docka")
        )
        conn.close()
        status["postgres"] = "ok"

    except Exception:
        status["postgres"] = "down"

    # Check Elasticsearch
    try:
        req = requests.get("http://elasticsearch:9200")
        if req.status_code == 200:
            status["elasticsearch"] = "ok"

    except Exception:
        status["elasticsearch"] = "down"

    return status


@app.get("/")
def root():
    return {"message": "DocKA API is running"}