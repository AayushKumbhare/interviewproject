from pydantic import BaseModel
import hashlib
from uuid import UUID
from typing import Optional

class User(BaseModel):
    name: str
    email: str
    password_hash: str

class Interview(BaseModel):
    user_id: Optional[str] = None
    name: str
    job_title: str=None
    total_questions: int
    questions_answered: int

class Message(BaseModel):
    interview_id: Optional[str] = None
    role: str
    message: str

class Feedback(BaseModel):
    interview_id: Optional[str] = None
    feedback_text: str
    feedback_score: int=None