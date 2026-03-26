
import streamlit as st
import google.generativeai as genai
import io
import base64
import time
import json
import requests
import re
from PIL import Image, ImageDraw, ImageOps
from datetime import datetime
import random

# --- HELPER: ROBUST JSON EXTRACTION ---
def extract_json(text):
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass
    start = text.find('{')
    end = text.rfind('}')
    if start != -1 and end != -1:
        try:
            return json.loads(text[start:end+1])
        except json.JSONDecodeError:
            pass
    return None

def validate_mc_questions(data, expected_count):
    if not data:
        return []
    if isinstance(data, list):
        questions = data
    elif isinstance(data, dict) and 'questions' in data:
        questions = data['questions']
    else:
        return []
    if not isinstance(questions, list):
        return []
    valid_q = []
    for q in questions:
        if isinstance(q, dict) and 'question' in q:
            opts = q.get('options', [])
            if isinstance(opts, list) and len(opts) > 0:
                valid_q.append(q)
    return valid_q[:expected_count]

def format_faq_to_python_string(faq_list):
    if not faq_list:
        return "[]"
    if isinstance(faq_list, str):
        if faq_list.strip().startswith('['):
            return faq_list
        return "[]"
    if not isinstance(faq_list, list):
        return "[]"
    formatted_pairs = []
    for qa_pair in faq_list:
        if not isinstance(qa_pair, dict):
            continue
        keys = list(qa_pair.keys())
        if len(keys) < 2:
            continue
        q_key = keys[0]
        a_key = keys[1]
        question = str(qa_pair[q_key]).replace("\\", "\\\\").replace("\'", "\\'")
        answer = str(qa_pair[a_key]).replace("\\", "\\\\").replace("\'", "\\'")
        formatted_pairs.append(f"{{ \'{q_key}\' : \'{question}\' , \'{a_key}\' : \'{answer}\' }}")
    return f'[' + ', '.join(formatted_pairs) + ']'

# --- 1. 核心配置 ---
SHEET_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbz2k7ZZ0shtl5wnhqB5J2wBcxnP7D08cRupRbz3hyi53G25mKYuz6qn5YqkTbPiYjIY/exec"
SLIDE_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbyUsYLxjxDn1PjQHDzFXyYQ4yyt2XJW-131GCCxZ-kJ7VBOb1RVgSEfa5kzS7wKb_cam/exec"
STABLE_MODEL_ID = "gemini-1.5-flash-latest"
APP_VERSION = "v5.2"
MC_QUESTION_COUNT = 10

WHO_WE_HELP_OPTIONS = ["GOVERNMENT & PUBLIC SECTOR", "LIFESTYLE & CONSUMER", "F&B & HOSPITALITY", "MALLS & VENUES"]
WHAT_WE_DO_OPTIONS = ["ROVING EXHIBITIONS", "SOCIAL & CONTENT", "INTERACTIVE & TECH", "PR & MEDIA", "EVENTS & CEREMONIES"]
SOW_OPTIONS = ["Event Planning", "Event Coordination", "Event Production", "Theme Design", "Concept Development", "Social Media Management", "KOL / MI Line up", "Artist Endorsement", "Media Pitching", "PR Consulting", "Souvenir Sourcing"]

CURRENT_YEAR = datetime.now().year
YEAR_OPTIONS = [str(y) for y in range(CURRENT_YEAR, 2011, -1)]
MONTH_OPTIONS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]

FIREBEAN_SYSTEM_PROMPT = '''
You are a Lead PR Strategist and Chief Editor for a premium B2B/B2C communications agency.
Task: Transform diagnostic data into a professional PR strategy JSON.
Always return a valid JSON object with keys: challenge_summary, solution_summary, 1_google_slide, 2_facebook_post, 3_threads_post, 4_instagram_post, 5_linkedin_post, 6_website, 7_faq.

**ABSOLUTE RULE 1 — POST-EVENT RETROSPECTIVE MODE**:
This tool is EXCLUSIVELY used AFTER an event has already taken place. All content you generate MUST be written as a retrospective case showcase.

**ABSOLUTE RULE 2 — INTERNAL TERMINOLOGY PROHIBITION**:
NEVER use "Firebean Brain", "Firebean Brain Team", or similar internal terminology. Use professional alternatives like "Our strategic approach", "Our creative concept", "Our team's expertise".

**ABSOLUTE RULE 3 — NO PROMOTIONAL LANGUAGE**:
NEVER include:
- Event invitations or calls-to-action (CTA) like "Join us", "Register now", "Book your tickets"
- Specific event dates, times, or promotional details
- Phrases like "即將舉行" (coming soon), "歡迎報名" (welcome to register)
- Any language suggesting future participation

**ABSOLUTE RULE 4 — CONTENT STRUCTURE**:
Return ONLY valid JSON with these keys:
- challenge_summary: Brief overview of the challenge
- solution_summary: How the challenge was addressed
- 1_google_slide: Title, subtitle, and 2-3 bullet points for Google Slide
- 2_facebook_post: Engaging retrospective post (max 300 chars)
- 3_threads_post: Industry insight or reflection (max 280 chars)
- 4_instagram_post: Visual storytelling angle (max 150 chars)
- 5_linkedin_post: Professional case study angle (max 300 chars)
- 6_website: Full case study narrative (800-1200 words)
- 7_faq: Array of Q&A pairs in Traditional Chinese

All content MUST be in Traditional Chinese unless otherwise specified.
'''

def call_gemini_sdk(prompt, is_json=False, max_retries=2):
    api_key = st.session_state.get("GEMINI_API_KEY", "")
    if not api_key:
        st.error("GEMINI_API_KEY is not set. Please add it in the sidebar.")
        return None
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(STABLE_MODEL_ID)
    for attempt in range(max_retries):
        try:
            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.7 if not is_json else 0.3,
                    max_output_tokens=8192 if is_json else 2000,
                    response_mime_type="application/json" if is_json else "text/plain"
                )
            )
            return response.text
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(1)
            else:
                st.error(f"Failed to call Gemini API after {max_retries} attempts: {e}")
                return None

def apply_styles(is_dark):
    bg_color = "#1E2128" if is_dark else "#E0E5EC"
    text_color = "#E0E5EC" if is_dark else "#1E2128"
    st.markdown(f'''
        <style>
        body {{ background-color: {bg_color}; color: {text_color}; }}
        .progress-circle-container {{ 
            position: relative; width: 150px; height: 150px; border-radius: 50%;
            display: flex; justify-content: center; align-items: center;
            background: conic-gradient(transparent 0% 0%, #FF0000 0% 0%);
            box-shadow: 0 0 20px #FF0000, inset 0 0 15px #FF0000;
            transition: background 0.5s ease-in-out;
        }}
        .progress-circle-inner {{ 
            position: absolute; width: 80%; height: 80%; border-radius: 50%;
            background: {bg_color}; display: flex; flex-direction: column;
            justify-content: center; align-items: center; font-size: 2.5em;
            font-weight: bold; color: #FF0000; text-shadow: 0 0 8px #FF0000;
            box-shadow: inset 4px 4px 8px rgba(0,0,0,0.2), inset -4px -4px 8px rgba(255,255,255,0.05);
        }}
        .progress-version {{ font-size: 0.4em; color: #FF0000; margin-top: 5px; }}
        </style>
    ''', unsafe_allow_html=True)

def main():
    st.set_page_config(page_title="FIREBEAN BRAIN", layout="wide")
    
    # Initialize session state
    if "client_name" not in st.session_state: st.session_state.client_name = ""
    if "project_name" not in st.session_state: st.session_state.project_name = ""
    if "venue" not in st.session_state: st.session_state.venue = ""
    if "event_year" not in st.session_state: st.session_state.event_year = str(datetime.now().year)
    if "event_month" not in st.session_state: st.session_state.event_month = MONTH_OPTIONS[datetime.now().month - 1]
    if "youtube" not in st.session_state: st.session_state.youtube = ""
    if "category" not in st.session_state: st.session_state.category = []
    if "what_we_do" not in st.session_state: st.session_state.what_we_do = []
    if "scope" not in st.session_state: st.session_state.scope = []
    if "project_photos" not in st.session_state: st.session_state.project_photos = []
    if "open_question_ans" not in st.session_state: st.session_state.open_question_ans = ""
    if "mc_questions" not in st.session_state: st.session_state.mc_questions = []
    if "logo_black" not in st.session_state: st.session_state.logo_black = None
    if "logo_white" not in st.session_state: st.session_state.logo_white = None
    if "ai_content" not in st.session_state: st.session_state.ai_content = None

    apply_styles(True)

    with st.sidebar:
        st.markdown("### 🧪 Testing Tools")
        if st.button("🚀 BOSS MODE (Auto-Fill)", type="primary"):
            st.session_state.client_name = "Dummy Client Inc."
            st.session_state.project_name = "Project Alpha Launch"
            st.session_state.venue = "Virtual Event Hall"
            st.session_state.event_year = str(CURRENT_YEAR)
            st.session_state.event_month = "JAN"
            st.session_state.youtube = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
            st.session_state.category = random.sample(WHO_WE_HELP_OPTIONS, k=1)
            st.session_state.what_we_do = random.sample(WHAT_WE_DO_OPTIONS, k=2)
            st.session_state.scope = random.sample(SOW_OPTIONS, k=3)
            st.session_state.open_question_ans = "This is a comprehensive set of dummy notes for testing."
            st.session_state.logo_black = "https://i.imgur.com/9J9a4oG.png"
            st.session_state.logo_white = "https://i.imgur.com/J4zL5aM.png"
            st.session_state.project_photos = [
                "https://i.imgur.com/9J9a4oG.png",
                "https://i.imgur.com/J4zL5aM.png",
                "https://i.imgur.com/9J9a4oG.png",
                "https://i.imgur.com/J4zL5aM.png"
            ]
            dummy_mc_questions = []
            for i in range(MC_QUESTION_COUNT):
                opts = [f"Dummy Option {chr(65+j)}" for j in range(4)]
                dummy_mc_questions.append({
                    "id": i + 1,
                    "question": f"This is dummy question {i+1}?",
                    "options": opts
                })
                st.session_state[f"ans_{i+1}"] = [random.choice(opts)]
            st.session_state.mc_questions = dummy_mc_questions
            st.rerun()

    col_logo, col_version_progress = st.columns([3, 1])
    with col_logo:
        st.image("https://raw.githubusercontent.com/dickson-crypto/Firebean-app/main/Firebeanlogo2026.png", width=300)
    with col_version_progress:
        progress_items = [
            ("Logo Black/White", st.session_state.logo_black is not None and st.session_state.logo_white is not None),
            ("Category", len(st.session_state.category) > 0),
            ("What We Do", len(st.session_state.what_we_do) > 0),
            ("Scope of Work", len(st.session_state.scope) > 0),
            ("Client Name", st.session_state.client_name != ""),
            ("Project Name", st.session_state.project_name != ""),
            ("Venue", st.session_state.venue != ""),
            ("Event Year/Month", st.session_state.event_year != "" and st.session_state.event_month != ""),
            ("Project Photos", len(st.session_state.project_photos) >= 4),
            (f"{MC_QUESTION_COUNT} MC Questions", len(st.session_state.mc_questions) == MC_QUESTION_COUNT and all(st.session_state.get(f"ans_{q.get('id', i+1)}", []) for i, q in enumerate(st.session_state.mc_questions)))
        ]
        completed = sum(1 for _, done in progress_items if done)
        total = len(progress_items)
        progress_pct = (completed / total) * 100 if total > 0 else 0
        st.markdown(f'''
            <div style="text-align: right; padding-top: 10px;">
                <div class="progress-circle-container" style="background: conic-gradient(#FF0000 {progress_pct}%, transparent {progress_pct}% 100%);">
                    <div class="progress-circle-inner">
                        {int(progress_pct)}%
                        <div class="progress-version">{APP_VERSION}</div>
                    </div>
                </div>
            </div>
        ''', unsafe_allow_html=True)

    st.text_input("Client Name", value=st.session_state.client_name, key="client_name")
    st.text_input("Project Name", value=st.session_state.project_name, key="project_name")
    st.text_input("Venue", value=st.session_state.venue, key="venue")
    st.selectbox("Event Year", YEAR_OPTIONS, index=YEAR_OPTIONS.index(st.session_state.event_year) if st.session_state.event_year in YEAR_OPTIONS else 0, key="event_year")
    st.selectbox("Event Month", MONTH_OPTIONS, index=MONTH_OPTIONS.index(st.session_state.event_month) if st.session_state.event_month in MONTH_OPTIONS else 0, key="event_month")
    st.text_input("YouTube Link (Optional)", value=st.session_state.youtube, key="youtube")
    st.multiselect("Category", WHO_WE_HELP_OPTIONS, default=st.session_state.category, key="category")
    st.multiselect("What We Do", WHAT_WE_DO_OPTIONS, default=st.session_state.what_we_do, key="what_we_do")
    st.multiselect("Scope of Work", SOW_OPTIONS, default=st.session_state.scope, key="scope")
    st.text_area("Additional Notes", value=st.session_state.open_question_ans, key="open_question_ans")

    st.markdown("### Project Photos")
    if isinstance(st.session_state.project_photos, list) and len(st.session_state.project_photos) > 0 and isinstance(st.session_state.project_photos[0], str):
        st.write("Dummy Photos Loaded:")
        cols = st.columns(4)
        for i, photo_url in enumerate(st.session_state.project_photos):
            with cols[i % 4]:
                st.image(photo_url, width=150)
    else:
        st.file_uploader("Upload Project Photos (Up to 8)", accept_multiple_files=True, key="project_photos")

    st.markdown("### Logos")
    c1, c2 = st.columns(2)
    with c1:
        if isinstance(st.session_state.logo_black, str):
            st.write("Dummy Black Logo:")
            st.image(st.session_state.logo_black, width=150)
        else:
            st.file_uploader("Logo Black", key="logo_black")
    with c2:
        if isinstance(st.session_state.logo_white, str):
            st.write("Dummy White Logo:")
            st.image(st.session_state.logo_white, width=150)
        else:
            st.file_uploader("Logo White", key="logo_white")

    st.markdown("### 10 Diagnostic Questions (MC)")
    for i, q in enumerate(st.session_state.mc_questions):
        st.multiselect(q['question'], q['options'], default=st.session_state.get(f"ans_{q['id']}", []), key=f"ans_{q['id']}")

    if progress_pct == 100:
        if st.button("🚀 FIREBEAN BRAIN!", type="primary"):
            st.session_state.ai_content = "Dummy AI Content"
            st.rerun()

    if st.session_state.ai_content:
        st.switch_page("pages/review.py")

if __name__ == "__main__":
    main()
