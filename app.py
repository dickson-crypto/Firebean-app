import streamlit as st
from google import genai
import io
import base64
import time
import json
import requests
import re
from PIL import Image, ImageDraw, ImageOps
from datetime import datetime

# --- HELPER: ROBUST JSON EXTRACTION ---
def extract_json(text):
    """
    Robustly extracts JSON from a string that might contain markdown, preamble, or other text.
    """
    if not text:
        return None
    
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    json_match = re.search(r\'```(?:json)?\\s*(\{.*?\})\\s*```\', text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass

    start = text.find(\'{\')
    end = text.rfind(\'}\')
    if start != -1 and end != -1:
        try:
            return json.loads(text[start:end+1])
        except json.JSONDecodeError:
            pass
            
    return None

def validate_mc_questions(data, expected_count):
    """
    Validates and extracts MC questions from various response structures.
    Handles: direct list, nested \'questions\' key, or other variations.
    """
    if not data:
        return []
    
    # If it\'s a list directly, use it
    if isinstance(data, list):
        questions = data
    # If it\'s a dict with \'questions\' key, extract it
    elif isinstance(data, dict) and \'questions\' in data:
        questions = data[\'questions\']
    else:
        return []
    
    if not isinstance(questions, list):
        return []
    
    valid_q = []
    for q in questions:
        if isinstance(q, dict) and \'question\' in q:
            opts = q.get(\'options\', [])
            if isinstance(opts, list) and len(opts) > 0:
                valid_q.append(q)
    
    return valid_q[:expected_count] # Ensure we only return the expected count

def format_faq_to_python_string(faq_list):
    """
    Safely converts a list of Q&A dicts into a standardized Python-style string for the Master DB.
    """
    if not faq_list:
        return \"[]\"
    
    if isinstance(faq_list, str):
        if faq_list.strip().startswith(\'[\'):
            return faq_list
        return \"[]\"

    if not isinstance(faq_list, list):
        return \"[]\"

    formatted_pairs = []
    for qa_pair in faq_list:
        if not isinstance(qa_pair, dict): 
            continue
        
        keys = list(qa_pair.keys())
        if len(keys) < 2: 
            continue
        q_key = keys[0]
        a_key = keys[1]
        
        question = str(qa_pair[q_key]).replace("\\", "\\\\").replace("\\'", "\\\\' ")
        answer = str(qa_pair[a_key]).replace("\\", "\\\\").replace("\\'", "\\\\' ")
        
        formatted_pairs.append(f"{{\\'\\\\\'{q_key}\\\\\\' : \\\\\'{question}\\\\\\' , \\\\\'{a_key}\\\\\\' : \\\\\'{answer}\\\\\\'}}")
    
    return f"[" + ", ".join(formatted_pairs) + "]"

# --- 1. 核心配置 ---
SHEET_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbz2k7ZZ0shtl5wnhqB5J2wBcxnP7D08cRupRbz3hyi53G25mKYuz6qn5YqkTbPiYjIY/exec"
SLIDE_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbyUsYLxjxDn1PjQHDzFXyQ4yyt2XJW-131GCCxZ-kJ7VBOb1RVgSEfa5kzS7wKb_cam/exec"
STABLE_MODEL_ID = "gemini-2.5-flash"
APP_VERSION = "v4.4" # Updated version
MC_QUESTION_COUNT = 10 # Reduced MC question count

WHO_WE_HELP_OPTIONS = ["GOVERNMENT & PUBLIC SECTOR", "LIFESTYLE & CONSUMER", "F&B & HOSPITALITY", "MALLS & VENUES"]
WHAT_WE_DO_OPTIONS = ["ROVING EXHIBITIONS", "SOCIAL & CONTENT", "INTERACTIVE & TECH", "PR & MEDIA", "EVENTS & CEREMONIES"]
SOW_OPTIONS = ["Event Planning", "Event Coordination", "Event Production", "Theme Design", "Concept Development", "Social Media Management", "KOL / MI Line up", "Artist Endorsement", "Media Pitching", "PR Consulting", "Souvenir Sourcing"]

CURRENT_YEAR = datetime.now().year
YEAR_OPTIONS = [str(y) for y in range(CURRENT_YEAR, 2011, -1)]
MONTH_OPTIONS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]

def generate_system_metadata():
    """
    自動生成大寫無符號 Project_id 與標準化 Sort_date
    """
    month_map = {m: str(i+1).zfill(2) for i, m in enumerate(MONTH_OPTIONS)}
    m_num = month_map.get(st.session_state.event_month, "01")
    sort_date = f"{st.session_state.event_year}-{m_num}-01"

    if st.session_state.get("draft_project_id"):
        return st.session_state.draft_project_id, sort_date

    try:
        count_res = requests.get(SHEET_SCRIPT_URL + "?action=get_row_count", timeout=10)
        if count_res.status_code == 200 and count_res.text.isdigit():
            next_index = int(count_res.text) + 1
        else:
            import random
            next_index = random.randint(100, 999)
    except Exception as e:
        import random
        next_index = random.randint(100, 999)
    
    project_id = f"FB{st.session_state.event_year}{str(next_index).zfill(3)}"
    return project_id, sort_date

FIREBEAN_SYSTEM_PROMPT = """
You are a Lead PR Strategist and Chief Editor for a premium B2B/B2C communications agency.
Task: Transform diagnostic data into a professional PR strategy JSON.
Always return a valid JSON object with keys: challenge_summary, solution_summary, 1_google_slide, 2_facebook_post, 3_threads_post, 4_instagram_post, 5_linkedin_post, 6_website, 7_faq.

**ABSOLUTE RULE 1 — POST-EVENT RETROSPECTIVE MODE**:
This tool is EXCLUSIVELY used AFTER an event has already taken place. All content you generate MUST be written as a retrospective case showcase.

**ABSOLUTE RULE 2 — INTERNAL TERMINOLOGY PROHIBITION**:
NEVER use "Firebean Brain", "Firebean Brain Team", or similar internal terminology. Use professional alternatives like "Our strategic approach", "Our creative concept", "Our team\'s expertise".

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
"""

def get_is_dark_mode():
    """Determine if it\'s dark mode based on Hong Kong time"""
    hk_hour = datetime.now().hour
    return hk_hour < 8 or hk_hour >= 20

def call_gemini_sdk(prompt, is_json=False, max_retries=2):
    """Call Gemini API with retry logic"""
    api_key = st.session_state.get("GEMINI_API_KEY", "")
    if not api_key:
        return None
    
    client = genai.Client(api_key=api_key)
    
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model=STABLE_MODEL_ID,
                contents=prompt,
                config=genai.types.GenerateContentConfig(
                    temperature=0.7 if not is_json else 0.3,
                    max_output_tokens=4000 if is_json else 2000
                )
            )
            return response.text
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(1)
            else:
                return None

def log_debug(msg):
    """Log debug messages"""
    if "debug_logs" not in st.session_state:
        st.session_state.debug_logs = []
    st.session_state.debug_logs.append(f"[{datetime.now().strftime(\'%H:%M:%S\')}] {msg}")

def apply_styles(is_dark):
    """
    Apply Neumorphism styles based on theme, including neon red progress circle.
    """
    bg_color = "#1E2128" if is_dark else "#E0E5EC"
    text_color = "#E0E5EC" if is_dark else "#1E2128"
    accent = "#FF6B6B"
    
    st.markdown(f"""
        <style>
        body {{
            background-color: {bg_color};
            color: {text_color};
        }}
        .neu-card {{
            background: {bg_color};
            border-radius: 10px;
            padding: 20px;
            box-shadow: 8px 8px 16px rgba(0,0,0,0.2), -8px -8px 16px rgba(255,255,255,0.1);
            margin: 15px 0;
        }}
        .mc-question {{
            font-weight: bold;
            margin: 10px 0;
            color: {accent};
        }}
        .debug-terminal {{
            background-color: #000;
            color: #0f0;
            font-family: \'Courier New\', Courier, monospace;
            padding: 15px;
            border-radius: 5px;
            font-size: 0.85em;
            max-height: 300px;
            overflow-y: auto;
            border: 1px solid #333;
        }}
        #logo-container {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }}
        .progress-circle-container {{
            position: relative;
            width: 300px; /* Match logo width */
            height: 300px; /* Match logo height */
            border-radius: 50%;
            display: flex;
            justify-content: center;
            align-items: center;
            background: conic-gradient(transparent 0% 0%, #FF0000 0% 0%); /* Initial state */
            box-shadow: 0 0 15px #FF0000, inset 0 0 10px #FF0000; /* Neon glow */
        }}
        .progress-circle-inner {{
            position: absolute;
            width: 80%;
            height: 80%;
            border-radius: 50%;
            background: {bg_color};
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            font-size: 3em;
            font-weight: bold;
            color: #FF0000; /* Neon Red */
            text-shadow: 0 0 5px #FF0000;
            box-shadow: 8px 8px 16px rgba(0,0,0,0.2), -8px -8px 16px rgba(255,255,255,0.1);
        }}
        .progress-version {{
            font-size: 0.8em;
            color: #FF0000;
            margin-top: 5px;
        }}
        </style>
    """, unsafe_allow_html=True)

def main():
    st.set_page_config(page_title="FIREBEAN BRAIN", layout="wide")
    
    # Initialize session state
    if "active_tab" not in st.session_state: 
        st.session_state.active_tab = "Project Collector"
    if "client_name" not in st.session_state: 
        st.session_state.client_name = ""
    if "project_name" not in st.session_state: 
        st.session_state.project_name = ""
    if "venue" not in st.session_state: 
        st.session_state.venue = ""
    if "event_year" not in st.session_state: 
        st.session_state.event_year = str(datetime.now().year)
    if "event_month" not in st.session_state: 
        st.session_state.event_month = MONTH_OPTIONS[datetime.now().month - 1]
    if "youtube" not in st.session_state: 
        st.session_state.youtube = ""
    if "category" not in st.session_state: 
        st.session_state.category = [] 
    if "what_we_do" not in st.session_state: 
        st.session_state.what_we_do = []
    if "scope" not in st.session_state: 
        st.session_state.scope = []
    if "project_photos" not in st.session_state: 
        st.session_state.project_photos = []
    if "hero_photo_index" not in st.session_state: 
        st.session_state.hero_photo_index = 0
    if "open_question_ans" not in st.session_state: 
        st.session_state.open_question_ans = ""
    if "mc_questions" not in st.session_state: 
        st.session_state.mc_questions = []
    if "ai_content" not in st.session_state: 
        st.session_state.ai_content = None
    if "logo_black" not in st.session_state: 
        st.session_state.logo_black = ""
    if "logo_white" not in st.session_state: 
        st.session_state.logo_white = ""
    if "user_dark_mode" not in st.session_state: 
        st.session_state.user_dark_mode = None
    if "sync_success" not in st.session_state: 
        st.session_state.sync_success = False

    is_dark = get_is_dark_mode()
    apply_styles(is_dark)

    with st.sidebar:
        st.markdown("### 🛠️ Settings")
        st.session_state.user_dark_mode = st.toggle("Dark Mode", value=is_dark)
        if st.button("Clear All Data", type="secondary"):
            for key in list(st.session_state.keys()): 
                del st.session_state[key]
            st.rerun()
        
        st.markdown("---")
        st.markdown("### 🔑 API Keys")
        gemini_key = st.text_input("GEMINI_API_KEY", type="password", value=st.session_state.get("GEMINI_API_KEY", ""))
        if gemini_key: 
            st.session_state.GEMINI_API_KEY = gemini_key

    # Display Logo with Version Number and Progress Circle
    st.markdown("<div id=\'logo-container\'>", unsafe_allow_html=True)
    col_logo, col_version_progress = st.columns([3, 1])
    with col_logo:
        logo_url = "https://raw.githubusercontent.com/dickson-crypto/Firebean-app/main/Firebeanlogo2026.png"
        st.image(logo_url, width=300, use_container_width=False)
    with col_version_progress:
        # Calculate Progress (11 items)
        progress_items = [
            ("Logo Black", st.session_state.logo_black != ""),
            ("Logo White", st.session_state.logo_white != ""),
            ("Category", len(st.session_state.category) > 0), 
            ("What We Do", len(st.session_state.what_we_do) > 0),
            ("Scope of Work", len(st.session_state.scope) > 0),
            ("Client Name", st.session_state.client_name != ""),
            ("Project Name", st.session_state.project_name != ""),
            ("Venue", st.session_state.venue != ""),
            ("Event Year", st.session_state.event_year != ""),
            ("Event Month", st.session_state.event_month != ""),
            (f"{MC_QUESTION_COUNT} MC Questions Answered", len(st.session_state.mc_questions) == MC_QUESTION_COUNT and all(st.session_state.get(f"ans_{q.get(\'id\', i+1)}", []) for i, q in enumerate(st.session_state.mc_questions)))
        ]
        
        completed = sum(1 for _, done in progress_items if done)
        total = len(progress_items)
        progress_pct = (completed / total) * 100 if total > 0 else 0

        st.markdown(f"""
            <div style=\'text-align: right; padding-top: 10px;\'>
                <div class=\'progress-circle-container\' style=\'background: conic-gradient(#FF0000 {progress_pct}%, transparent {progress_pct}% 100%);\'>
                    <div class=\'progress-circle-inner\'>
                        {int(progress_pct)}%
                        <div class=\'progress-version\'>{APP_VERSION}</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

    # FIXED NAVIGATION
    tab_options = ["Project Collector", "Review & Multi-Sync"]
    active_idx = tab_options.index(st.session_state.active_tab)
    tabs_nav = st.radio("Navigation", tab_options, index=active_idx, horizontal=True, label_visibility="collapsed")
    if tabs_nav != st.session_state.active_tab:
        st.session_state.active_tab = tabs_nav
        st.rerun()

    if st.session_state.active_tab == "Project Collector":
        # Display Missing Items Checklist (moved here)
        if progress_pct < 100:
            st.markdown("### 📌 溫馨提示 Checklist")
            missing_items = [name for name, done in progress_items if not done]
            for item in missing_items:
                st.markdown(f"❌ **{item}**")
        else:
            st.markdown("### ✅ All Requirements Met!")
        
        st.markdown("<div class=\'neu-card\'>", unsafe_allow_html=True)
        st.markdown("### Project Basics")
        
        # Logo Uploads in one row
        st.markdown("#### Logo Upload ✱ (Required)")
        logo_col1, logo_col2 = st.columns(2)
        with logo_col1:
            st.session_state.logo_black = st.file_uploader("Upload Black Logo", type=[\'png\', \'jpg\', \'jpeg\'], key="logo_b")
        with logo_col2:
            st.session_state.logo_white = st.file_uploader("Upload White Logo", type=[\'png\', \'jpg\', \'jpeg\'], key="logo_w")
        
        st.markdown("#### Project Info")
        info_col1, info_col2, info_col3 = st.columns(3)
        with info_col1:
            st.markdown("**Category**")
            selected_categories = []
            for option in WHO_WE_HELP_OPTIONS:
                if st.checkbox(option, value=(option in st.session_state.category), key=f"cat_{option}"):
                    selected_categories.append(option)
            st.session_state.category = selected_categories
        with info_col2:
            st.markdown("**What We Do**")
            selected_what_we_do = []
            for option in WHAT_WE_DO_OPTIONS:
                if st.checkbox(option, value=(option in st.session_state.what_we_do), key=f"what_{option}"):
                    selected_what_we_do.append(option)
            st.session_state.what_we_do = selected_what_we_do
        with info_col3:
            st.markdown("**Scope of Work**")
            selected_scope = []
            for option in SOW_OPTIONS:
                if st.checkbox(option, value=(option in st.session_state.scope), key=f"scope_{option}"):
                    selected_scope.append(option)
            st.session_state.scope = selected_scope
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        st.markdown("<div class=\'neu-card\'>", unsafe_allow_html=True)
        st.markdown("#### Client & Project Details")
        c1, c2 = st.columns([1, 1])
        with c1:
            st.session_state.client_name = st.text_input("Client Name", value=st.session_state.client_name, key="client_input")
            st.session_state.project_name = st.text_input("Project Name", value=st.session_state.project_name, key="proj_input")
            st.session_state.venue = st.text_input("Venue", value=st.session_state.venue, key="venue_input")
        
        with c2:
            st.session_state.event_year = st.selectbox("Event Year", YEAR_OPTIONS, index=YEAR_OPTIONS.index(st.session_state.event_year) if st.session_state.event_year in YEAR_OPTIONS else 0, key="year_sel")
            st.session_state.event_month = st.selectbox("Event Month", MONTH_OPTIONS, index=MONTH_OPTIONS.index(st.session_state.event_month) if st.session_state.event_month in MONTH_OPTIONS else 0, key="month_sel")
            st.session_state.youtube = st.text_input("YouTube Link (Optional)", value=st.session_state.youtube, key="yt_input")
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Project Photos and Open Question in one row
        st.markdown("<div class=\'neu-card\'>", unsafe_allow_html=True)
        photo_col, text_col = st.columns([1, 1])
        with photo_col:
            st.markdown("#### Project Photos") 
            up = st.file_uploader("Upload Project Photos (Up to 8)", type=[\'jpg\', \'jpeg\', \'png\'], accept_multiple_files=True, key="p_u")
            if up:
                st.session_state.project_photos = up[:8]
            
            if st.session_state.project_photos:
                st.markdown(f"**已上傳 {len(st.session_state.project_photos)} 張相片**")
                st.markdown("##### Select Hero Photo")
                cols = st.columns(4)
                for idx, photo in enumerate(st.session_state.project_photos):
                    with cols[idx % 4]:
                        st.image(photo, use_container_width=True)
                        if st.button(f"Hero", key=f"hero_{idx}", type="primary" if st.session_state.hero_photo_index == idx else "secondary"):
                            st.session_state.hero_photo_index = idx
                            st.rerun()
        with text_col:
            st.markdown("#### Additional Notes")
            st.session_state.open_question_ans = st.text_area("Anything else to add?", value=st.session_state.open_question_ans, height=300, key="open_q_input") 
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<div class=\'neu-card\'>", unsafe_allow_html=True)
        st.markdown(f"#### {MC_QUESTION_COUNT} Diagnostic Questions (MC)") 
        
        if st.button(f"生成 {MC_QUESTION_COUNT} 題繁中診斷題目", use_container_width=True):
            with st.status("生成中...", expanded=True) as status:
                facts = f"Client: {st.session_state.client_name}, Project: {st.session_state.project_name}, Category: {\', \'.join(st.session_state.category)}, SOW: {\', \'.join(st.session_state.scope)}, Notes: {st.session_state.open_question_ans}"
                
                mc_prompt = f"""Generate {MC_QUESTION_COUNT} Traditional Chinese multiple-choice diagnostic questions for a PR/Marketing case study.\n\nFacts: {facts}\n\nReturn a JSON object with this exact structure:\n{{\n  "questions": [\n    {{\n      "id": 1,\n      "question": "Question text in Traditional Chinese?",\n      "options": ["Option A", "Option B", "Option C", "Option D"]\n    }},\n    {{\n      "id": 2,\n      "question": "Next question in Traditional Chinese?",\n      "options": ["Option A", "Option B", "Option C", "Option D"]\n    }}\n  ]\n}}\n\nCRITICAL REQUIREMENTS:\n1. Generate EXACTLY {MC_QUESTION_COUNT} questions (id from 1 to {MC_QUESTION_COUNT})\n2. Each question MUST have exactly 4 options\n3. All text MUST be in Traditional Chinese\n4. Return ONLY valid JSON, no other text or explanation\n5. Each option should be a single string"""
                        
                res = call_gemini_sdk(mc_prompt, is_json=True)
                if res:
                    log_debug(f"MC Response received: {res[:100]}...")
                    parsed = extract_json(res)
                    if parsed:
                        questions = validate_mc_questions(parsed, MC_QUESTION_COUNT)
                        if questions and len(questions) == MC_QUESTION_COUNT:
                            st.session_state.mc_questions = questions
                            status.update(label=f"✅ 成功生成 {len(questions)} 題！", state="complete", expanded=False)
                            st.rerun()
                        else:
                            log_debug(f"Validation failed. Parsed: {parsed}. Expected {MC_QUESTION_COUNT} questions, got {len(questions) if questions else 0}.")
                            st.error(f"生成的題目格式不正確或數量不符。請重試。(Expected {MC_QUESTION_COUNT} questions, got {len(questions) if questions else 0})")
                    else:
                        log_debug(f"JSON extraction failed from: {res[:200]}")
                        st.error("AI 返回的不是有效的 JSON。請重試。")
                else:
                    st.error("生成失敗。請確保已上傳相片並重試。")

        if st.session_state.mc_questions:
            st.markdown(f"**已生成 {len(st.session_state.mc_questions)} 題**")
            for i, q in enumerate(st.session_state.mc_questions):
                q_id = q.get(\'id\', q.get(\'number\', q.get(\'q_id\', i + 1)))
                st.markdown(f"<div class=\'mc-question\'>Q{q_id}. {q.get(\'question\', \'\')}</div>", unsafe_allow_html=True)
                ans_key = f"ans_{q_id}"
                current_selections = st.session_state.get(ans_key, [])
                new_selections = []
                for opt in q.get(\'options\', []):
                    if st.checkbox(opt, value=(opt in current_selections), key=f"chk_{q_id}_{opt}"):
                        new_selections.append(opt)
                st.session_state[ans_key] = new_selections
        st.markdown("</div>", unsafe_allow_html=True)

        cr = st.columns([1])[0]
        with cr:
            st.markdown("<div class=\'neu-card\'>", unsafe_allow_html=True)
            
            # Lock button if progress < 100%
            is_complete = progress_pct >= 100
            if st.button("🚀 FIREBEAN BRAIN! (Generate AI Content)", use_container_width=True, type="primary" if is_complete else "secondary", disabled=not is_complete):
                if not is_complete:
                    st.error("⚠️ 請完成所有必填項目才能繼續！")
                else:
                    with st.spinner("正在生成全套 PR 策略與文案..."):
                        context = f"Client: {st.session_state.client_name}, Project: {st.session_state.project_name}, Category: {\', \'.join(st.session_state.category)}, SOW: {\', \'.join(st.session_state.scope)}, Notes: {st.session_state.open_question_ans}"
                        res = call_gemini_sdk(f"{FIREBEAN_SYSTEM_PROMPT}\\n\\nContext: {context}", is_json=True)
                        if res:
                            parsed = extract_json(res)
                            if parsed:
                                st.session_state.ai_content = parsed
                                st.session_state.active_tab = "Review & Multi-Sync"
                                st.rerun()
                            else:
                                st.error("AI returned an invalid format. Please try again.")
            st.markdown("</div>", unsafe_allow_html=True)

    elif st.session_state.active_tab == "Review & Multi-Sync":
        if not st.session_state.ai_content:
            st.warning("請先在 Project Collector 頁面生成 AI 內容。")
            if st.button("← 返回 Project Collector"):
                st.session_state.active_tab = "Project Collector"
                st.rerun()
        else:
            st.markdown("<div class=\'neu-card\'>", unsafe_allow_html=True)
            st.markdown("### Review & Edit Content")
            
            ai = st.session_state.ai_content
            
            col1, col2 = st.columns([1, 1])
            with col1:
                st.markdown("#### Challenge Summary")
                st.write(ai.get("challenge_summary", ""))
            with col2:
                st.markdown("#### Solution Summary")
                st.write(ai.get("solution_summary", ""))
            
            st.markdown("---")
            
            st.markdown("#### Generated Content")
            tabs = st.tabs(["Google Slide", "Facebook", "Threads", "Instagram", "LinkedIn", "Website", "FAQ"])
            
            with tabs[0]:
                st.write(ai.get("1_google_slide", ""))
            with tabs[1]:
                st.write(ai.get("2_facebook_post", ""))
            with tabs[2]:
                st.write(ai.get("3_threads_post", ""))
            with tabs[3]:
                st.write(ai.get("4_instagram_post", ""))
            with tabs[4]:
                st.write(ai.get("5_linkedin_post", ""))
            with tabs[5]:
                st.write(ai.get("6_website", ""))
            with tabs[6]:
                faq = ai.get("7_faq", [])
                if isinstance(faq, list):
                    for qa in faq:
                        st.write(f"**Q:** {list(qa.values())[0] if qa else \'\'}")
                        st.write(f"**A:** {list(qa.values())[1] if len(qa) > 1 else \'\'}")
            
            st.markdown("</div>", unsafe_allow_html=True)
            
            st.markdown("<div class=\'neu-card\'>", unsafe_allow_html=True)
            if st.button("💾 Sync to Master DB", use_container_width=True, type="primary"):
                with st.spinner("Syncing to Master DB and Google Slides..."):
                    if trigger_full_sync():
                        st.balloons()
                        st.success("✅ 同步成功！你的案例已保存到 Master DB 和 Google Slides。")
                    else:
                        st.error("❌ 同步失敗: 無法處理圖片")
            st.markdown("</div>", unsafe_allow_html=True)

def trigger_full_sync():
    """Trigger the full sync to Google Sheet and Slides"""
    try:
        # Prepare images
        processed_imgs = []
        for photo in st.session_state.project_photos:
            img = Image.open(photo)
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format=\'PNG\')
            b64 = base64.b64encode(img_byte_arr.getvalue()).decode()
            processed_imgs.append(b64)
        
        # Prepare slide payload
        slide_payload = {
            "project_name": st.session_state.project_name,
            "client_name": st.session_state.client_name,
            "images": processed_imgs,
            "logo_black": st.session_state.logo_black,
            "logo_white": st.session_state.logo_white
        }
        
        # Call Slide Script
        sr = requests.post(SLIDE_SCRIPT_URL, json=slide_payload, timeout=120)
        if sr.status_code != 200:
            log_debug(f"Slide sync failed: HTTP {sr.status_code}")
            return False
        
        # Prepare sheet payload
        ai = st.session_state.ai_content
        faq = ai.get("7_faq", {})
        
        payload = {
            "client_name": st.session_state.client_name,
            "project_name": st.session_state.project_name,
            "category": \', \'.join(st.session_state.category), 
            "what_we_do": \', \'.join(st.session_state.what_we_do),
            "scope": \', \'.join(st.session_state.scope),
            "venue": st.session_state.venue,
            "event_year": st.session_state.event_year,
            "event_month": st.session_state.event_month,
            "youtube": st.session_state.youtube,
            "challenge": ai.get("challenge_summary", ""),
            "solution": ai.get("solution_summary", ""),
            "faq_en": format_faq_to_python_string(faq.get("en", [])),
            "faq_tc": format_faq_to_python_string(faq.get("tc", [])),
            "faq_jp": format_faq_to_python_string(faq.get("jp", [])),
            "ai_content": ai,
            "logo_black": st.session_state.logo_black,
            "logo_white": st.session_state.logo_white,
            "hero_index": st.session_state.hero_photo_index,
            "images": processed_imgs
        }
        
        r = requests.post(SHEET_SCRIPT_URL, json=payload, timeout=120)
        if r.status_code != 200:
            log_debug(f"Sheet sync failed: HTTP {r.status_code}")
            return False

        return True
    except Exception as e:
        log_debug(f"Sync error: {str(e)}")
        return False

if __name__ == "__main__":
    main()
