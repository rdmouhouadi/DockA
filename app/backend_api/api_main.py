
from fastapi import FastAPI

app = FastAPI(
    title="DocKA API",
    description="Document Knowledge Access API",
    version="0.1.0",
)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/")
def root():
    return {"message": "DocKA API is running"}
