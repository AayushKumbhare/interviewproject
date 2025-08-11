from openai import OpenAI
import os
from dotenv import load_dotenv
import wave
import sys
import pyaudio 
from pynput import keyboard
import threading
import time 
import hashlib
from database import *
from models import *

load_dotenv()

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
client = OpenAI(api_key=OPENAI_API_KEY)
db = Database()

CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1 if sys.platform == 'darwin' else 2
RATE = 44100
    
class Interviewer():
    def __init__(self, max_questions, job_title):
        self.conversation_history = []
        self.max_questions = max_questions
        self.question_count = 0
        self.job_title = job_title

    def interview_prompt(self):
        evaluation_prompt = f"""

        # Identity

        You are a professional mock interview coach specializing in behavioral and technical interviews across various industries. You simulate realistic interviews to help candidates prepare for actual job interviews.

        # Instructions

        * Conduct a mock interview for the job title {self.job_title}.
        * Begin by introducing the interview and setting expectations.
        * Ask {self.max_questions} questions relevant to the job title, mixing: behavioral questions (e.g., STAR format), role-specific technical or strategic questions, and situational or problem-solving questions.
        * Use a professional tone, like an experienced interviewer at a reputable company.

        """
        
        return evaluation_prompt
    
    def feedback_prompt(self):
        feedback_prompt = f"""
        Based on the interview conversation below for the {self.job_title} position, please provide comprehensive feedback:

        1. Overall Performance Summary
        2. Strengths demonstrated by the candidate
        3. Areas for improvement with specific examples
        4. Suggestions for better answers to specific questions
        5. General interview tips for future success
        6. Final recommendation

        Be honest and constructive, as a real interviewer would be.

        Interview Conversation:
        """

        return feedback_prompt
    
    def get_chat_history(self):
         return self.conversation_history
    
    def get_user_input(self):
        recording = False           # Current recording status
        should_stop = False        # Signal to end everything
        audio_data = []           # Collected audio chunks
        last_toggle_time = 0      # Prevent accidental double-clicks
        
        def on_press(key):
            nonlocal recording, should_stop, last_toggle_time
            
            if key == keyboard.Key.space:
                # Prevent accidental double-clicks
                current_time = time.time()
                if current_time - last_toggle_time < 0.3:
                    return
                last_toggle_time = current_time
                
                # Toggle recording state
                recording = not recording
                
                if recording:
                    print("🔴 Recording... (Press SPACEBAR again to stop)")
                    # Clear any previous audio data
                    audio_data.clear()
                else:
                    print("⏹️ Recording stopped. Processing...")
                    
            elif key == keyboard.Key.esc:
                print("❌ Exiting...")
                should_stop = True
                recording = False
                return False  # Stop the keyboard listener
        def record_continuously():
            nonlocal audio_data, recording, should_stop
            
            p = pyaudio.PyAudio()
            stream = p.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                frames_per_buffer=CHUNK
            )
            
            try:
                while not should_stop:
                    if recording:
                        # Capture audio chunk
                        try:
                            data = stream.read(CHUNK, exception_on_overflow=False)
                            audio_data.append(data)
                        except Exception as e:
                            print(f"Audio read error: {e}")
                            break
                    else:
                        # Small sleep to prevent busy waiting
                        time.sleep(0.01)
                        
            except Exception as e:
                print(f"Recording error: {e}")
            finally:
                stream.close()
                p.terminate()
        def save_audio_file(audio_chunks, filename='user_response.wav'):
            if not audio_chunks:
                return False
                
            try:
                with wave.open(filename, 'wb') as wf:
                    p = pyaudio.PyAudio()
                    wf.setnchannels(CHANNELS)
                    wf.setsampwidth(p.get_sample_size(FORMAT))
                    wf.setframerate(RATE)
                    
                    # Write all collected audio chunks
                    for chunk in audio_chunks:
                        wf.writeframes(chunk)
                    
                    p.terminate()
                return True
            except Exception as e:
                print(f"Error saving audio: {e}")
                return False

        print("\n🎤 Audio Input Mode")
        print("Press SPACEBAR to start/stop recording")
        print("Press ESC to exit or Enter for text input")
        
        # Check if user wants text input instead
        print("Press Enter now for text input, or any other key to continue with audio...")
        # You might want to add a quick check here
        
        # Start audio recording thread
        audio_thread = threading.Thread(target=record_continuously, daemon=True)
        audio_thread.start()
        
        # Start keyboard listener and wait for completion
        try:
            with keyboard.Listener(on_press=on_press) as listener:
                # Wait until recording is complete or user exits
                while not should_stop and (recording or len(audio_data) == 0):
                    time.sleep(0.1)
                    
            # If we have audio data, save and transcribe
            if audio_data:
                print("💾 Saving audio file...")
                if save_audio_file(audio_data):
                    return self.transcribe_audio('user_response.wav')
                else:
                    print("❌ Failed to save audio, falling back to text input")
                    return input("Please type your response: ")
            else:
                print("ℹ️ No audio recorded, using text input")
                return input("Please type your response: ")
                
        except KeyboardInterrupt:
            print("\n⚠️ Interrupted by user")
            should_stop = True
            return input("Please type your response: ")   
        
        pass
    
    def transcribe_audio(self, filename):
        # This is where you'll integrate with OpenAI Whisper
        print("🔄 Transcribing audio...")
        
        try:
            with open(filename, 'rb') as audio_file:
                transcript = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file
                )
            print(f"📝 You said: {transcript.text}")
            return transcript.text
        except Exception as e:
            print(f"❌ Transcription error: {e}")
            return input("Transcription failed. Please type your response: ") 
        
    """def get_user_input(self):
        user_response = input("Response: ")
        return user_response"""

    def store_bot_response(self, system_response):
        self.conversation_history.append({'role': 'assistant', 'content': system_response})

    def store_user_response(self, user_response):
        self.conversation_history.append({'role' : 'user', 'content': user_response})

    def interview_question(self):
        try:
            messages = []
            history = self.get_chat_history()
            messages.append({"role": "system", "content": self.interview_prompt()})
            
            for msg in history:
                if msg['role'] in ['user', 'assistant']:
                    messages.append(msg)
            
            if self.question_count == 0:
                messages.append({"role": "user", "content": "Please start the interview with your introduction and first question."})

            completion = client.chat.completions.create(
                model='gpt-4.1',
                messages = messages,
            temperature=0.7
            )
            return completion.choices[0].message.content
        except Exception as e:
            print(f"Error: {e}")
            return None
        
    def get_feedback(self):
        try:
            messages = []
            messages.append({'role': 'system', 'content': 'You are an expert interviewer providing detailed feedback on a completed interview.'})
            conversation_summary = self.feedback_prompt()

            history = self.get_chat_history()
            for msg in history:
                if msg['role'] == 'assistant':
                    conversation_summary += f"\nInterviewer: {msg['content']}"
                elif msg['role'] == 'user':
                    conversation_summary += f"\nCandidate: {msg['content']}"

            messages.append({'role': 'user', 'content':conversation_summary})
            completion = client.chat.completions.create(
                model='gpt-4.1',
                messages = messages,
                temperature=0.7
            )
            return completion.choices[0].message.content
        except Exception as e:
            print(f"Error getting feedback: {e}")
            return None
        
    def message_database(self, interview_id):
        try:
            history = self.get_chat_history()
            for item in history:
                role = item['role']
                message = item['content']
                
                message_db = Message(
                    interview_id=interview_id,
                    role=role,
                    message=message)
                
                db.add_message(message_db)
        except Exception as e:
            print(f"Error: {e}")
    
    def feedback_database(self, interview_id, feedback):
        try:
            feedback_db = Feedback(
                interview_id=interview_id,
                feedback_text=feedback
            )

            db.add_feedback(feedback_db)
        except Exception as e:
            print(f"Error: {e}")
                
        
            
    def run_interview(self):
        print("=" * 60)
        print(f"🎯 MOCK INTERVIEW - {self.job_title.upper()}")
        print("=" * 60)
        print("Instructions:")
        print("- Answer each question thoughtfully")
        print("- Type 'quit' at any time to end and get feedback")
        print("-" * 60)
        
        try:
            user_name = input("Enter your name: ")
            user_email = input("Enter your email: ")
            user_password = input("Enter your password: ")
            
            user_result = db.get_user(user_email)
            if not user_result:
                user = User(
                    name=user_name,
                    email=user_email,
                    password_hash=hashlib.sha256(user_password.encode()).hexdigest())
                db.add_user(user)
                user_result = db.get_user(user_email)
            
            user_id = user_result['user_id']
            
            interview_name = input("Name of interview you want to access (type in new name if you want to make a new interview): ")
            interview = db.get_interview(interview_name)
            if not interview:
                interview = Interview(
                    user_id=user_id,
                    name=interview_name,
                    job_title=self.job_title,
                    total_questions=self.max_questions,
                    questions_answered=self.question_count
                )
                db.add_interview(interview)
                interview = db.get_interview(interview_name)
            
            interview_id = interview['interview_id']

            while self.question_count < self.max_questions:
                print(f"\n Question {self.question_count + 1} of {self.max_questions}")
                
                # Get interviewer question
                response = self.interview_question()
                if response is None:
                    print(" Error generating question. Ending interview.")
                    break
                
                print(f"\n Interviewer: {response}")
                self.store_bot_response(response)

                # Get user input
                user_input = self.get_user_input()
                
                # Handle quit command
                if user_input.lower() == 'quit':
                    print("\n Interviewer: Thank you for your time!")
                    print("\n Storing history to database...")
                    self.message_database(interview_id)
                    print("\n Generating feedback...")
                    print("\n Storing feedback to database...")
                    self.feedback_database(interview_id, self.get_feedback())
                    return self.get_feedback()
                
                if not user_input:
                    print("Please provide a response or type 'quit' to exit.")
                    continue
                
                # Store user response and increment counter
                self.store_user_response(user_input)
                self.question_count += 1
                db.supabase.table('interviews').update({'questions_answered': self.question_count}).eq('interview_id', interview_id).execute()
            
            # Interview completed naturally
            print(f"\n Interview completed! You answered {self.question_count} questions.")

            print(f"Storing history to database...")
            self.message_database(interview_id)
            print("\n Generating final feedback...")
            print("\n Storing feedback to database...")
            self.feedback_database(interview_id, self.get_feedback())
            return self.get_feedback()
            
        except KeyboardInterrupt:
            print("\n\n Interview interrupted by user.")
            return self.get_feedback()
        except Exception as e:
            print(f" Error running interview: {e}")
            return None

def main():
    """Main function to run the interview"""
    print("🎯 Welcome to Interview Practice!")
    
    # Get job title
    job_title = input("\nEnter the job title you're interviewing for: ").strip()
    if not job_title:
        job_title = "Software Engineer"
        print(f"Using default: {job_title}")
    
    # Get number of questions
    try:
        max_questions = int(input("How many questions would you like (default 5): ").strip() or "5")
        if max_questions < 1:
            max_questions = 5
    except ValueError:
        max_questions = 5
        print("Using default: 5 questions")
    
    print(f"\n Starting {max_questions}-question interview for: {job_title}")
    
    # Create and run interviewer
    interviewer = Interviewer(max_questions, job_title)
    
    try:
        final_feedback = interviewer.run_interview()
        
        if final_feedback:
            print("\n" + "=" * 60)
            print(" FINAL INTERVIEW FEEDBACK")
            print("=" * 60)
            print(final_feedback)
        
        print("\n Thank you for practicing! Good luck with your real interviews!")
        
    except Exception as e:
        print(f" An error occurred: {e}")

if __name__ == '__main__':
    main()
            