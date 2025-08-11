from fasthtml.common import *
from uuid import uuid4
from main import Interviewer
from pathlib import Path
from starlette.requests import Request
from starlette.responses import JSONResponse
import os, tempfile
from dotenv import load_dotenv
from openai import OpenAI
import re

load_dotenv()
oa_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

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
    return Div(cls="card bg-base-200 shadow-md")(
        Div(cls="card-body space-y-2")(
            H3(title, cls="card-title w-full truncate whitespace-nowrap overflow-hidden text-ellipsis", **{"title": title}),
            Div(body_md, cls="marked break-words leading-relaxed")  # <- add these classes
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

    # 1) If we're done, go to feedback page
    if interviewer.question_count >= interviewer.max_questions:
        return Redirect(f"/feedback?uid={uid}")

    bubbles = []
    for msg in interviewer.get_chat_history():
        bubbles.append(ChatMessage(msg['content'], msg['role'] == 'user'))

    # 2) Only generate next Q if NOT done and last msg isn't assistant
    history = interviewer.get_chat_history()
    if not history or history[-1]['role'] != 'assistant':
        question = interviewer.interview_question()
        interviewer.store_bot_response(question)
        bubbles.append(ChatMessage(question, False))
        
    return Titled("Mock Interview",
        Div(cls="flex flex-col h-screen")(
            Div(id="chatbox", cls="flex flex-col gap-2 flex-grow overflow-y-auto p-4")(*bubbles),
            Form(action=f"/chat_post?uid={uid}", method="post", cls="p-4 border-t border-gray-300")(
                Div(cls="flex items-center gap-2")(
                    Input(name="msg", id="msgInput", placeholder="Type your answer...",
                        cls="input input-bordered flex-1"),
                    Button("🎙️", id="micBtn", type="button",
                        cls="btn btn-ghost btn-circle", **{"aria_label": "Record voice"}),
                    Span("", id="recStatus", cls="text-xs opacity-70 hidden"),
                    Button("Send", id="sendBtn", type="submit",
                        cls="btn btn-primary btn-sm px-3 !w-auto whitespace-nowrap"),
    
                )
            )
        ),
        Script("""
        (() => {
        const uid = new URLSearchParams(location.search).get('uid');
        const micBtn   = document.getElementById('micBtn');
        const recStatus= document.getElementById('recStatus');
        const msgInput = document.getElementById('msgInput');
        const sendBtn  = document.getElementById('sendBtn'); // if you added it
        
        const box = document.getElementById('chatbox');
        if (box) box.scrollTop = box.scrollHeight;

        if (!micBtn || !msgInput) return; // page safety

        let mediaRecorder = null;
        let recording = false;
        let chunks = [];
        let timerId = null;
        let startMs = 0;
        let autoStopTO = null;  // hard cap recordings

        function showStatus(t){ recStatus.textContent = t; recStatus.classList.remove('hidden'); }
        function hideStatus(){ recStatus.textContent = ''; recStatus.classList.add('hidden'); }
        function startTimer(){
            startMs = Date.now();
            timerId = setInterval(() => {
                const s = Math.floor((Date.now()-startMs)/1000);
                const mm = Math.floor(s/60), ss = String(s%60).padStart(2,'0');
                showStatus(`Recording… ${mm}:${ss}`);
            }, 1000);
        }
        function stopTimer(){ clearInterval(timerId); timerId = null; }
        
        micBtn.addEventListener('click', () => {
            if (!recording) startRecording();
            else            stopRecording();
        });
        
        async function startRecording(){
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

            // Create MediaRecorder with a safe fallback (Safari can be picky)
            try {
                mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm;codecs=opus' });
            } catch {
                mediaRecorder = new MediaRecorder(stream);
            }

            chunks = [];
            mediaRecorder.ondataavailable = (e) => {
                if (e.data && e.data.size) {
                    chunks.push(e.data);
                    // Debug while learning:
                    // console.log('chunk', e.data.size, 'bytes');
                }
            };

            mediaRecorder.onstop = async () => {
            // Stop the stream tracks so the mic indicator turns off
            stream.getTracks().forEach(t => t.stop());
            stopTimer();

            // Build one file from all chunks
            if (!chunks.length) {
                showStatus('No audio captured — try again.');
                recording = false;
                // keep inputs disabled for a beat; user can click mic again
                micBtn.classList.remove('btn-error');
                return;
            }

            const blob = new Blob(chunks, { type: 'audio/webm' });
            console.log('Recorded blob size:', blob.size, 'bytes');

            // Transcribe
            showStatus('Transcribing…');
            try {
                const fd = new FormData();
                fd.append('audio', blob, 'clip.webm');

                const res = await fetch(`/upload_audio?uid=${encodeURIComponent(uid)}`, {
                method: 'POST',
                body: fd
                });
                if (!res.ok) {
                showStatus('Transcription failed.');
                micBtn.classList.remove('btn-error');
                return;
                }

                const { text } = await res.json();
                const cleaned = (text || '').trim();
                if (!cleaned) {
                showStatus('Heard nothing. Try again.');
                micBtn.classList.remove('btn-error');
                return;
                }

                // Put it in the input so the user sees it
                msgInput.value = cleaned;

                // Re-enable just before submit (optional)
                msgInput.disabled = false;
                if (sendBtn) sendBtn.disabled = false;
                micBtn.classList.remove('btn-error');

                // Submit via REAL FORM so the browser follows redirects
                const form = document.createElement('form');
                form.method = 'POST';
                form.action = `/chat_post?uid=${encodeURIComponent(uid)}`;

                const hidden = document.createElement('input');
                hidden.type = 'hidden';
                hidden.name = 'msg';
                hidden.value = msgInput.value;

                form.appendChild(hidden);
                document.body.appendChild(form);
                form.submit();

            } catch (e) {
                console.error(e);
                showStatus('Transcription error.');
                micBtn.classList.remove('btn-error');
            }
            };

            mediaRecorder.start(250); // emit small chunks ~4x/sec
            autoStopTO = setTimeout(() => {
                if (recording) stopRecording();
            }, 120000); // 120s cap
            recording = true;
            msgInput.disabled = true;
            if (sendBtn) sendBtn.disabled = true;
            micBtn.classList.add('btn-error');
            showStatus('Recording… 0:00');
            startTimer();

        } catch (err) {
            console.error(err);
            alert('Mic blocked or unavailable. On prod, use HTTPS; on dev, use localhost.');
        }
    }
    function stopRecording(){
        if (autoStopTO) { clearTimeout(autoStopTO); autoStopTO = null; }
        if (!mediaRecorder || !recording) return;
        try { mediaRecorder.stop(); } catch {}
        recording = false;
    }

    
        })();
               """)
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

@app.route("/upload_audio", methods=["POST"])
async def upload_audio(request: Request, uid: str):
    try:
        form = await request.form()
        up = form.get("audio")
        if up is None:
            return JSONResponse({"error": "no file"}, status_code=400)

        data = await up.read()  # read once
        if len(data) > 10 * 1024 * 1024:  # 10 MB cap
            return JSONResponse({"error": "file too large"}, status_code=413)

        # Save to a temp file; Whisper can read webm directly
        with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as tmp:
            tmp.write(data)
            temp_path = tmp.name

        try:
            with open(temp_path, "rb") as f:
                tr = oa_client.audio.transcriptions.create(
                    model="whisper-1",
                    file=f
                )
            return JSONResponse({"text": tr.text or ""})
        finally:
            try: os.remove(temp_path)
            except: pass
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

    
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
