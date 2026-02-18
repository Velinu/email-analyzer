from dotenv import load_dotenv
import os

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.runnables import RunnablePassthrough
from pydantic import BaseModel, Field
import logging

load_dotenv()

try:
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    if not GOOGLE_API_KEY:
        raise ValueError("GOOGLE_API_KEY environment variable not set.")
    
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=GOOGLE_API_KEY,
        temperature=0.7,
        # safety_settings=[
        #     {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_LOW_AND_ABOVE"},
        #     {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_LOW_AND_ABOVE"},
        #     {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_LOW_AND_ABOVE"},
        #     {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_LOW_AND_ABOVE"},
        # ]
    )
except ValueError as e:
    logging.error(f"Error initializing LLM: {e}")
    llm = None

class EmailAnalysisOutput(BaseModel):
    subject: str = Field(description="The subject of the email.")
    sender: str = Field(description="The sender of the email.")
    reason: str = Field(description="The reason why the email is considered important (e.g., 'bill/invoice', 'job opening', 'job application update').")

parser = JsonOutputParser(pydantic_object=EmailAnalysisOutput)

prompt_template = ChatPromptTemplate.from_messages(
    [
        ("system", """You are an AI assistant that analyzes emails.
    Your task is to determine if an email falls into one of the following important categories:
    - 'bill/invoice'
    - 'job opening'
    - 'job application update'
    
    If the email fits one of these categories, return a JSON object with 'subject', 'sender', and 'reason'.
    The 'reason' should be the identified category.
    If the email does not fit any of these categories, return an empty JSON object.
    {format_instructions}"""),
            ("user", "Subject: {subject}\nFrom: {sender}\nBody: {body}"),
        ]
    )

if llm:
    chain = (
        {
            "subject": RunnablePassthrough(), 
            "sender": RunnablePassthrough(), 
            "body": RunnablePassthrough(),
            "format_instructions": lambda x: parser.get_format_instructions()
        } 
        | prompt_template 
        | llm 
        | parser
    )
else:
    chain = None

async def analyze_email_with_gemini(subject: str, sender: str, body: str):
    if not chain:
        raise ValueError("AI model not initialized. Please ensure GOOGLE_API_KEY is set.")
    
    return await chain.ainvoke({"subject": subject, "sender": sender, "body": body})
