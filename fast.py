from fasthtml.common import *
from uuid import uuid4
from main import Interviewer
from pathlib import Path

import re

hdrs = (picolink,
    Script(src="https://cdn.tailwindcss.com"),
    Link(rel="stylesheet", href="https://cdn.jsdelivr.net/npm/daisyui@4.11.1/dist/full.min.css"),
    MarkdownJS(),
)
app = FastHTML(hdrs=hdrs, cls="p-4 w-full h-screen")

INTERVIEWERS = {}

def get_interviewer(uid):
  return INTERVIEWERS.get(uid)

def ChatMessage(msg, user):
    bubble_class = "chat-bubble-primary" if user else "chat-bubble-secondary"
    chat_class = "chat-end" if user else "chat-start"
    return Div(cls=f"chat {chat_class}")(
        Div("You" if user else "AI", cls="chat-header"),
        Div(msg, cls=f"chat-bubble {bubble_class}")
    )
    
def parse_numbered_sections(text: str):
    txt = text.strip()

    # Pattern A: Markdown headings "### 1. Title Body..."
    pat_head = re.compile(
        r'(?ms)^\s*#{1,6}\s*(\d+)\.\s*([^\n]+?)\s+(.*?)(?=^\s*#{1,6}\s*\d+\.\s|^\s*---\s*$|\Z)'
    )
    # Pattern B: Bold headings "**1. Title** Body..."
    pat_bold = re.compile(
        r'(?ms)^\s*\*\*\s*(\d+)\.\s*([^\*]+?)\s*\*\*\s*(.*?)(?=^\s*\*\*\s*\d+\.\s|^\s*---\s*$|\Z)'
    )

    sections = [(int(n), t.strip(), b.strip()) for n, t, b in pat_head.findall(txt)]
    if not sections:
        sections = [(int(n), t.strip(), b.strip()) for n, t, b in pat_bold.findall(txt)]

    # If nothing matched, return a single blob
    if not sections:
        return [("Feedback", txt)]

    # Sort by the captured number, just in case
    sections.sort(key=lambda x: x[0])
    # Return (title, body) pairs
    return [(title, body) for _, title, body in sections]


def CardMD(title, body_md):
    # body_md is markdown; make sure MarkdownJS() is in your hdrs so .marked renders
    return Div(cls="card bg-base-200 shadow-md")(
        Div(cls="card-body space-y-2")(
            H3(title, cls="card-title"),
            Div(body_md, cls="marked")
        )
    )

@app.route
def index():
    return Titled("Start Interview",
        Form(action="/start", method="post")(
            Label("Job Title: "), Input(name="job_title", cls="input"),
            Label("Number of Questions: "), Input(name="num_questions", type="number", value=5, cls="input"),
            Button("Start Interview", type="submit", cls="btn btn-primary")
        )
    )

@app.route("/start", methods=["POST"])
def start(job_title: str, num_questions: int):
    uid = str(uuid4())
    interviewer = Interviewer(int(num_questions), job_title)
    INTERVIEWERS[uid] = interviewer
    return Redirect(f"/chat?uid={uid}")

@app.route("/chat")
def chat(uid: str):
    interviewer = get_interviewer(uid)
    if not interviewer:
        return Redirect("/")
    bubbles = []
    # show all chat so far
    for msg in interviewer.get_chat_history():
        is_user = msg['role'] == 'user'
        bubbles.append(ChatMessage(msg['content'], is_user))

    # If last message is NOT from 'assistant', generate next question
    if not interviewer.get_chat_history() or interviewer.get_chat_history()[-1]['role'] != 'assistant':
        question = interviewer.interview_question()
        interviewer.store_bot_response(question)
        bubbles.append(ChatMessage(question, False))
    return Titled("Mock Interview",
    Div(cls="flex flex-col h-screen")(
        Div(id="chatbox", cls="flex flex-col gap-2 flex-grow overflow-y-auto p-4")(*bubbles),
        Form(action=f"/chat_post?uid={uid}", method="post", cls="p-4 border-t border-gray-300")(
            Div(cls="flex items-center gap-2")(
                Input(name="msg", placeholder="Type your answer...",
                    cls="input input-bordered flex-1"),
                Button("Send", type="submit",
                    cls="btn btn-primary btn-sm px-3 !w-auto whitespace-nowrap")
    )
)


)
    )

@app.route("/chat_post", methods=["POST"])
def chat_post(uid: str, msg: str):
    interviewer = get_interviewer(uid)
    if not interviewer:
        return Redirect("/")
    if msg.strip().lower() == "quit":
        return Redirect(f"/feedback?uid={uid}")
    interviewer.store_user_response(msg)
    interviewer.question_count += 1
    if interviewer.question_count >= interviewer.max_questions:
        return Redirect(f"/feedback?uid={uid}")
    return Redirect(f"/chat?uid={uid}")
    
@app.route("/feedback")
def feedback(uid: str):
    interviewer = get_interviewer(uid)
    if not interviewer:
        return Redirect("/")

    raw = interviewer.get_feedback() or "No feedback generated."
    sections = parse_numbered_sections(raw)
    cards = [CardMD(title, body) for title, body in sections]

    return Titled("Interview Feedback",
        Div(cls="mx-auto max-w-3xl p-6 space-y-4")(*cards),
        Div(cls="mt-6 flex gap-2")(
            Button("Back to Chat", cls="btn", onclick=f"window.location='/chat?uid={uid}'"),
            Button("Restart", cls="btn btn-primary", onclick="window.location='/'")
        )
    )

serve()
