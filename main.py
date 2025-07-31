from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
client = OpenAI(api_key=OPENAI_API_KEY)
    
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
        * At the end, summarize the candidate's performance, provide constructie feedback on each answer, and suggest improvements. Be completely honest, as a real interviewer would be.

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
        user_response = input("Response: ")
        return user_response

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
        
            
    def run_interview(self):
        print("=" * 60)
        print(f"🎯 MOCK INTERVIEW - {self.job_title.upper()}")
        print("=" * 60)
        print("Instructions:")
        print("- Answer each question thoughtfully")
        print("- Type 'quit' at any time to end and get feedback")
        print("-" * 60)
        
        try:
            while self.question_count < self.max_questions:
                print(f"\n📝 Question {self.question_count + 1} of {self.max_questions}")
                
                # Get interviewer question
                response = self.interview_question()
                if response is None:
                    print("❌ Error generating question. Ending interview.")
                    break
                
                print(f"\n🤵 Interviewer: {response}")
                self.store_bot_response(response)

                # Get user input
                user_input = self.get_user_input()
                
                # Handle quit command
                if user_input.lower() == 'quit':
                    print("\n🤵 Interviewer: Thank you for your time!")
                    print("\n📋 Generating feedback...")
                    return self.get_feedback()
                
                if not user_input:
                    print("Please provide a response or type 'quit' to exit.")
                    continue
                
                # Store user response and increment counter
                self.store_user_response(user_input)
                self.question_count += 1
            
            # Interview completed naturally
            print(f"\n🎉 Interview completed! You answered {self.question_count} questions.")
            print("\n📋 Generating final feedback...")
            return self.get_feedback()
            
        except KeyboardInterrupt:
            print("\n\n⚠️ Interview interrupted by user.")
            return self.get_feedback()
        except Exception as e:
            print(f"❌ Error running interview: {e}")
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
    
    print(f"\n✅ Starting {max_questions}-question interview for: {job_title}")
    
    # Create and run interviewer
    interviewer = Interviewer(max_questions, job_title)
    
    try:
        final_feedback = interviewer.run_interview()
        
        if final_feedback:
            print("\n" + "=" * 60)
            print("📝 FINAL INTERVIEW FEEDBACK")
            print("=" * 60)
            print(final_feedback)
        
        print("\n🎉 Thank you for practicing! Good luck with your real interviews!")
        
    except Exception as e:
        print(f"❌ An error occurred: {e}")

if __name__ == '__main__':
    main()
            