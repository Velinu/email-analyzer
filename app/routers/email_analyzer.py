from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List
from app.services.ai_service import analyze_email_with_gemini
from app.services.gmail_service import get_gmail_service, get_unread_emails, mark_email_as_read

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
        # The AI service returns an empty dict if the email is not important
        if analysis_result:
            return EmailAnalysisResponse(
                subject=analysis_result.get("subject"),
                sender=analysis_result.get("sender"),
                reason=analysis_result.get("reason")
            )
        return None # Return an empty response if not important
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during AI analysis: {str(e)}")

@router.post("/analyze-unread-emails", response_model=List[EmailAnalysisResponse])
async def analyze_unread_emails(background_tasks: BackgroundTasks):
    gmail_service = get_gmail_service()
    if not gmail_service:
        raise HTTPException(status_code=500, detail="Failed to initialize Gmail service.")
    
    unread_emails = get_unread_emails(gmail_service)
    if not unread_emails:
        return []
    
    important_emails = []
    for email in unread_emails:
        try:
            analysis_result = await analyze_email_with_gemini(
                subject=email["subject"],
                sender=email["sender"],
                body=email["body"]
            )
            if analysis_result:
                important_emails.append(EmailAnalysisResponse(
                    subject=analysis_result.get("subject"),
                    sender=analysis_result.get("sender"),
                    reason=analysis_result.get("reason")
                ))
            
            # Mark email as read in the background
            background_tasks.add_task(mark_email_as_read, gmail_service, email["id"])

        except Exception as e:
            # Log the error but continue processing other emails
            print(f"Error analyzing email {email.get('id')}: {str(e)}")
            continue
            
    return important_emails
