from fastapi import FastAPI
from app.routers import email_analyzer

app = FastAPI()

app.include_router(email_analyzer.router, prefix="/api")

@app.get("/")
async def root():
    return {"message": "Welcome to the Email Analyzer API. Navigate to /api/analyze_email to analyze emails."}
