from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List
from app.services.ai_service import analyze_email_with_gemini
from app.services.gmail_service import get_gmail_service, get_first_unread_email, mark_email_as_read

router = APIRouter()

class EmailAnalysisRequest(BaseModel):
    subject: str
    sender: str
    body: str

class EmailAnalysisResponse(BaseModel):
    subject: str
    sender: str
    reason: str

@router.post("/analyze_email", response_model=Optional[EmailAnalysisResponse])
async def analyze_email(request: EmailAnalysisRequest):
    if not request.body or not request.body.strip():
        raise HTTPException(status_code=400, detail="Email body cannot be empty.")
    
    try:
        analysis_result = await analyze_email_with_gemini(
            subject=request.subject,
            sender=request.sender,
            body=request.body
        )

        if analysis_result:
            return EmailAnalysisResponse(
                subject=analysis_result.get("subject"),
                sender=analysis_result.get("sender"),
                reason=analysis_result.get("reason")
            )
        return None # Return an empty response if not important
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during AI analysis: {str(e)}")

@router.post("/analyze-unread-emails", response_model=Optional[EmailAnalysisResponse])
async def analyze_unread_emails(background_tasks: BackgroundTasks):
    gmail_service = get_gmail_service()
    if not gmail_service:
        raise HTTPException(status_code=500, detail="Failed to initialize Gmail service.")
    
    email_to_analyze = get_first_unread_email(gmail_service)
    if not email_to_analyze:
        return None
    
    try:
        analysis_result = await analyze_email_with_gemini(
            subject=email_to_analyze["subject"],
            sender=email_to_analyze["sender"],
            body=email_to_analyze["body"]
        )

        background_tasks.add_task(mark_email_as_read, gmail_service, email_to_analyze["id"])

        if analysis_result:
            return EmailAnalysisResponse(
                subject=analysis_result.get("subject"),
                sender=analysis_result.get("sender"),
                reason=analysis_result.get("reason")
            )
        return None # Return None if not important
    except Exception as e:
        print(f"Error analyzing email {email_to_analyze.get('id')}: {str(e)}")
        background_tasks.add_task(mark_email_as_read, gmail_service, email_to_analyze["id"])
        raise HTTPException(status_code=500, detail=f"Error analyzing email: {str(e)}")

