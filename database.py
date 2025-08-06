from supabase import create_client, Client
import os
from dotenv import load_dotenv
from models import *

load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

class Database:
    def __init__(self):
        self.supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

    def add_user(self, user: User):
        self.supabase.table("users").insert(user.model_dump()).execute()

    def get_user(self, email: str):
        result = self.supabase.table("users").select("*").eq("email", email).execute()
        return result.data[0] if result.data else None

    def add_interview(self, interview: Interview):
        self.supabase.table("interviews").insert(interview.model_dump()).execute()

    def get_interview(self, name: str):
        result = self.supabase.table("interviews").select("*").eq("name", name).execute()
        return result.data[0] if result.data else None
    
    def add_message(self, message: Message):
        self.supabase.table("messages").insert(message.model_dump()).execute()

    def get_message(self, message_id: str):
        result = self.supabase.table("messages").select("*").eq("id", message_id).execute()
        return result.data[0] if result.data else None
    
    def add_feedback(self, feedback: Feedback):
        self.supabase.table("feedback").insert(feedback.model_dump()).execute()
    
    def get_feedback(self, feedback_id: str):
        result = self.supabase.table("feedback").select("*").eq("id", feedback_id).execute()
        return result.data[0] if result.data else None
    
    def update_feedback(self, feedback_id: str, feedback: Feedback):
        self.supabase.table("feedback").update(feedback.model_dump()).eq("id", feedback_id).execute()
    
    def delete_feedback(self, feedback_id: str):
        self.supabase.table("feedback").delete().eq("id", feedback_id).execute()
    