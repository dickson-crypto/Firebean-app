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

def validate_mc_questions(data):
    """
    Validates and extracts MC questions from various response structures.
    Handles: direct list, nested 'questions' key, or other variations.
    """
    if not data:
        return []
    
    # If it's a list directly, use it
    if isinstance(data, list):
        questions = data
    # If it's a dict with 'questions' key, extract it
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
    
    return valid_q

def format_faq_to_python_string(faq_list):
    """
    Safely converts a list of Q&A dicts into a standardized Python-style string for the Master DB.
    """
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
        
        question = str(qa_pair[q_key]).replace("\\", "\\\\").replace("'", "\\'")
        answer = str(qa_pair[a_key]).replace("\\", "\\\\").replace("'", "\\'")
        
        formatted_pairs.append(f"{{'{q_key}': '{question}', '{a_key}': '{answer}'}}")
    
    return f"[" + ", ".join(formatted_pairs) + "]"

# --- 1. 核心配置 ---
SHEET_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbz2k7ZZ0shtl5wnhqB5J2wBcxnP7D08cRupRbz3hyi53G25mKYuz6qn5YqkTbPiYjIY/exec"
SLIDE_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbyUsYLxjxDn1PjQHDzFXyQ4yyt2XJW-131GCCxZ-kJ7VBOb1RVgSEfa5kzS7wKb_cam/exec"
STABLE_MODEL_ID = "gemini-2.5-flash"

WHO_WE_HELP_OPTIONS = ["GOVERNMENT & PUBLIC SECTOR", "LIFESTYLE & CONSUMER", "F&B & HOSPITALITY", "MALLS & VENUES"]
WHAT_WE_DO_OPTIONS = ["ROVING EXHIBITIONS", "SOCIAL & CONTENT", "INTERACTIVE & TECH", "PR & MEDIA", "EVENTS & CEREMONIES"]
SOW_OPTIONS = ["Event Planning", "Event Coordination", "Event Production", "Theme Design", "Concept Development", "Social Media Management", "KOL / MI Line up", "Artist Endorsement", "Media Pitching", "PR Consulting", "Souvenir Sourcing"]

CURRENT_YEAR = datetime.now().year
YEAR_OPTIONS = [str(y) for y in range(CURRENT_YEAR, 2011, -1)]
MONTH_OPTIONS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]

def generate_system_metadata():
    """自動生成大寫無符號 Project_id 與標準化 Sort_date"""
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
NEVER use "Firebean Brain", "Firebean Brain Team", or similar internal terminology. Use professional alternatives like "Our strategic approach", "Our creative concept", "Our team's expertise".

STRICTLY FORBIDDEN in ALL outputs:
- ANY invitation language (join us, register now, don't miss, etc.)
- ANY future-tense event promotion
- ANY specific date, time, ticket price, or venue address used in promotional context
- CTA links or registration details
- Phrases like "save the date", "mark your calendar", "coming soon"

**CRITICAL INSTRUCTION FOR 'challenge_summary' AND 'solution_summary'**:
BOTH MUST be in ENGLISH ONLY. Keep them concise: 1-2 short sentences (max 50 words each).

**CRITICAL INSTRUCTION FOR '6_website' (Magazine Feature Article)**:
The '6_website' key MUST be a nested JSON object with: "angle_chosen", "en", "tc", and "jp".
Write a 500-word POST-EVENT feature article in valid HTML using ONLY <h1>, <h3>, and <p> tags.

**CRITICAL INSTRUCTIONS FOR SOCIAL MEDIA POSTS**:
All posts are POST-EVENT highlights for the agency's own channels.

1. '2_facebook_post': 100-250 words, Traditional Chinese, warm and storytelling tone
2. '4_instagram_post': <150 words, Traditional Chinese, behind-the-scenes retrospective
3. '3_threads_post': <50 words, Traditional Chinese, witty and insightful
4. '5_linkedin_post': 200-400 words, English, professional case study tone

**CRITICAL INSTRUCTION FOR '7_faq'**:
The '7_faq' key MUST be a nested JSON object with: "en", "tc", and "jp".
Each language key must contain a list of 3-4 Q&A objects with keys "Q1", "A1", "Q2", "A2", etc.
"""

def call_gemini_sdk(prompt, image_files=None, is_json=False):
    """使用 Google GenAI SDK 呼叫 Gemini"""
    try:
        api_key = st.secrets.get("GEMINI_API_KEY") or st.session_state.get("GEMINI_API_KEY")
        if not api_key:
            st.error("請在 Secrets 或 Sidebar 中設定 GEMINI_API_KEY")
            return None
            
        client = genai.Client(api_key=api_key)
        contents = [prompt]
        
        if image_files:
            for f in image_files:
                if hasattr(f, "seek"): 
                    f.seek(0)
                img = Image.open(f)
                contents.append(img)
        
        config = {"response_mime_type": "application/json"} if is_json else None
        response = client.models.generate_content(
            model=STABLE_MODEL_ID,
            contents=contents,
            config=config
        )
        return response.text
    except Exception as e:
        st.error(f"Gemini API Error: {str(e)}")
        return None

def log_debug(msg, level="info"):
    """記錄調試日誌"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    formatted_msg = f"[{timestamp}] [{level.upper()}] {msg}"
    if "debug_logs" not in st.session_state:
        st.session_state.debug_logs = []
    st.session_state.debug_logs.append(formatted_msg)
    if len(st.session_state.debug_logs) > 50:
        st.session_state.debug_logs.pop(0)

def clean_field(val):
    """清理輸入欄位"""
    if not val: 
        return ""
    return str(val).replace("\n", " ").replace("\r", "").strip()

def get_is_dark_mode():
    """判斷當前是否為深色模式"""
    if st.session_state.user_dark_mode is not None:
        return st.session_state.user_dark_mode
    hr = datetime.now().hour
    return hr >= 18 or hr < 6

def apply_styles(is_dark):
    """根據模式應用 CSS"""
    bg = "#1E2128" if is_dark else "#f4f7f6"
    card_bg = "#2D3436" if is_dark else "#ffffff"
    text_color = "#E0E0E0" if is_dark else "#2d3436"
    accent = "#00d2ff" if is_dark else "#0984e3"
    
    st.markdown(f"""
        <style>
        .stApp {{ background-color: {bg}; color: {text_color}; }}
        .neu-card {{
            background: {card_bg};
            padding: 25px;
            border-radius: 15px;
            box-shadow: 0 4px 15px rgba(0,0,0,{"0.3" if is_dark else "0.05"});
            margin-bottom: 20px;
        }}
        .mc-question {{
            font-weight: bold;
            font-size: 1.1em;
            margin-top: 15px;
            color: {accent};
        }}
        .debug-terminal {{
            background-color: #000;
            color: #0f0;
            font-family: 'Courier New', Courier, monospace;
            padding: 15px;
            border-radius: 5px;
            font-size: 0.85em;
            max-height: 300px;
            overflow-y: auto;
            border: 1px solid #333;
        }}
        #logo-anchor {{
            display: flex;
            justify-content: center;
            align-items: center;
            margin-bottom: 20px;
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
        st.session_state.category = WHO_WE_HELP_OPTIONS[0]
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

    st.markdown('<div id="logo-anchor">', unsafe_allow_html=True)
    logo_url = "https://raw.githubusercontent.com/dickson-crypto/Firebean-app/main/Firebeanlogo2026.png"
    st.image(logo_url, width=300, use_container_width=False)
    st.markdown('</div>', unsafe_allow_html=True)

    # FIXED NAVIGATION
    tab_options = ["Project Collector", "Review & Multi-Sync"]
    active_idx = tab_options.index(st.session_state.active_tab)
    tabs_nav = st.radio("Navigation", tab_options, index=active_idx, horizontal=True, label_visibility="collapsed")
    if tabs_nav != st.session_state.active_tab:
        st.session_state.active_tab = tabs_nav
        st.rerun()

    if st.session_state.active_tab == "Project Collector":
        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        st.markdown("### Project Basics")
        
        c1, c2 = st.columns([1, 1])
        with c1:
            l_black = st.file_uploader("Upload Black Logo", type=['png', 'jpg'], key="logo_b")
            if l_black: 
                st.session_state.logo_black = base64.b64encode(l_black.read()).decode()
            if st.session_state.logo_black:
                st.markdown(f'<div style="background-color: #f4f7f6; padding: 10px; border-radius: 8px;"><img src="data:image/png;base64,{st.session_state.logo_black}" style="max-height: 60px;"></div>', unsafe_allow_html=True)
        with c2:
            l_white = st.file_uploader("Upload White Logo", type=['png', 'jpg'], key="logo_w")
            if l_white: 
                st.session_state.logo_white = base64.b64encode(l_white.read()).decode()
            if st.session_state.logo_white:
                st.markdown(f'<div style="background-color: #2D3436; padding: 10px; border-radius: 8px;"><img src="data:image/png;base64,{st.session_state.logo_white}" style="max-height: 60px;"></div>', unsafe_allow_html=True)

        b1, b2, b3 = st.columns(3)
        st.session_state.client_name = clean_field(b1.text_input("Client", value=st.session_state.client_name, key="client_name_input"))
        st.session_state.project_name = clean_field(b2.text_input("Project", value=st.session_state.project_name, key="project_name_input"))
        st.session_state.venue = clean_field(b3.text_input("Venue", value=st.session_state.venue, key="venue_input"))

        b4, b5, b6 = st.columns(3)
        y_idx = YEAR_OPTIONS.index(st.session_state.event_year) if st.session_state.event_year in YEAR_OPTIONS else 0
        m_idx = MONTH_OPTIONS.index(st.session_state.event_month) if st.session_state.event_month in MONTH_OPTIONS else 1
        st.session_state.event_year = b4.selectbox("Event Year", YEAR_OPTIONS, index=y_idx, key="year_select")
        st.session_state.event_month = b5.selectbox("Event Month", MONTH_OPTIONS, index=m_idx, key="month_select")
        st.session_state.youtube = b6.text_input("YouTube Link (Optional)", value=st.session_state.youtube, key="youtube_input")

        st.markdown("<hr>", unsafe_allow_html=True)
        ca, cb, cc = st.columns(3)
        with ca:
            st.markdown("##### Category")
            st.session_state.category = st.radio("Category", WHO_WE_HELP_OPTIONS, index=WHO_WE_HELP_OPTIONS.index(st.session_state.category) if st.session_state.category in WHO_WE_HELP_OPTIONS else 0, label_visibility="collapsed", key="cat_radio")
        with cb:
            st.markdown("##### What we do")
            st.session_state.what_we_do = [o for o in WHAT_WE_DO_OPTIONS if st.checkbox(o, key=f"w_{o}", value=(o in st.session_state.what_we_do))]
        with cc:
            st.markdown("##### Scope of work")
            st.session_state.scope = [o for o in SOW_OPTIONS if st.checkbox(o, key=f"s_{o}", value=(o in st.session_state.scope))]
        st.markdown('</div>', unsafe_allow_html=True)

        cl, cr = st.columns([1.2, 1])
        with cl:
            st.markdown('<div class="neu-card">', unsafe_allow_html=True)
            if st.button("生成 15 題繁中診斷題目"):
                if not st.session_state.project_photos: 
                    st.error("請先上傳相片。")
                else:
                    with st.status("🧠 AI 大腦啟動中...", expanded=True) as status:
                        facts = call_gemini_sdk("請詳細掃描並提取這些活動相片中的實體事實 (Facts)...", image_files=st.session_state.project_photos)
                        
                        # IMPROVED: More explicit MC generation prompt
                        mc_prompt = f"""Based on these facts from the event photos, generate exactly 15 PR diagnostic multiple-choice questions in Traditional Chinese.

Facts: {facts}

Return a JSON object with this exact structure:
{{
  "questions": [
    {{
      "id": 1,
      "question": "Question text in Traditional Chinese?",
      "options": ["Option A", "Option B", "Option C", "Option D"]
    }},
    {{
      "id": 2,
      "question": "Next question in Traditional Chinese?",
      "options": ["Option A", "Option B", "Option C", "Option D"]
    }}
  ]
}}

CRITICAL REQUIREMENTS:
1. Generate EXACTLY 15 questions (id from 1 to 15)
2. Each question MUST have exactly 4 options
3. All text MUST be in Traditional Chinese
4. Return ONLY valid JSON, no other text or explanation
5. Each option should be a single string"""
                        
                        res = call_gemini_sdk(mc_prompt, is_json=True)
                        if res:
                            log_debug(f"MC Response received: {res[:100]}...")
                            parsed = extract_json(res)
                            if parsed:
                                questions = validate_mc_questions(parsed)
                                if questions and len(questions) > 0:
                                    st.session_state.mc_questions = questions
                                    status.update(label=f"✅ 成功生成 {len(questions)} 題！", state="complete", expanded=False)
                                    st.rerun()
                                else:
                                    log_debug(f"Validation failed. Parsed: {parsed}")
                                    st.error(f"生成的題目格式不正確。請重試。(Got {len(questions) if questions else 0} questions)")
                            else:
                                log_debug(f"JSON extraction failed from: {res[:200]}")
                                st.error("AI 返回的不是有效的 JSON。請重試。")
                        else:
                            st.error("生成失敗。請確保已上傳相片並重試。")

            if st.session_state.mc_questions:
                st.markdown(f"**已生成 {len(st.session_state.mc_questions)} 題**")
                for i, q in enumerate(st.session_state.mc_questions):
                    q_id = q.get('id', q.get('number', q.get('q_id', i + 1)))
                    st.markdown(f"<div class='mc-question'>Q{q_id}. {q.get('question', '')}</div>", unsafe_allow_html=True)
                    ans_key = f"ans_{q_id}"
                    current_selections = st.session_state.get(ans_key, [])
                    new_selections = []
                    for opt in q.get('options', []):
                        if st.checkbox(opt, value=(opt in current_selections), key=f"chk_{q_id}_{opt}"):
                            new_selections.append(opt)
                    st.session_state[ans_key] = new_selections
            st.markdown('</div>', unsafe_allow_html=True)

        with cr:
            st.markdown('<div class="neu-card">', unsafe_allow_html=True)
            # FIXED: Photo uploader with better state management
            up = st.file_uploader("Upload Project Photos (Up to 8)", type=['jpg', 'jpeg', 'png'], accept_multiple_files=True, key="p_u")
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
            st.markdown('</div>', unsafe_allow_html=True)
            
            st.markdown('<div class="neu-card">', unsafe_allow_html=True)
            st.session_state.open_question_ans = st.text_area("Anything else to add?", value=st.session_state.open_question_ans, height=150, key="open_q_input")
            if st.button("🚀 FIREBEAN BRAIN! (Generate AI Content)", use_container_width=True, type="primary"):
                with st.spinner("正在生成全套 PR 策略與文案..."):
                    context = f"Client: {st.session_state.client_name}, Project: {st.session_state.project_name}, Category: {st.session_state.category}, SOW: {', '.join(st.session_state.scope)}, Notes: {st.session_state.open_question_ans}"
                    res = call_gemini_sdk(f"{FIREBEAN_SYSTEM_PROMPT}\n\nContext: {context}", is_json=True)
                    if res:
                        parsed = extract_json(res)
                        if parsed:
                            st.session_state.ai_content = parsed
                            st.session_state.active_tab = "Review & Multi-Sync"
                            st.rerun()
                        else:
                            st.error("AI returned an invalid format. Please try again.")
            st.markdown('</div>', unsafe_allow_html=True)

    elif st.session_state.active_tab == "Review & Multi-Sync":
        if not st.session_state.ai_content:
            st.warning("請先在 Project Collector 頁面生成 AI 內容。")
        else:
            st.markdown('<div class="neu-card">', unsafe_allow_html=True)
            st.markdown("### Review & Edit Content")
            ai = st.session_state.ai_content
            ai["challenge_summary"] = st.text_area("Challenge Summary", value=ai.get("challenge_summary", ""), key="rev_challenge")
            ai["solution_summary"] = st.text_area("Solution Summary", value=ai.get("solution_summary", ""), key="rev_solution")
            
            tabs = st.tabs(["Website Articles", "Social Media", "FAQ", "Google Slide"])
            with tabs[0]:
                web = ai.get("6_website", {})
                web["en"] = st.text_area("English Article (HTML)", value=web.get("en", ""), height=300, key="rev_web_en")
                web["tc"] = st.text_area("Traditional Chinese Article (HTML)", value=web.get("tc", ""), height=300, key="rev_web_tc")
                web["jp"] = st.text_area("Japanese Article (HTML)", value=web.get("jp", ""), height=300, key="rev_web_jp")
            with tabs[1]:
                ai["2_facebook_post"] = st.text_area("Facebook Post", value=ai.get("2_facebook_post", ""), height=200, key="rev_fb")
                ai["4_instagram_post"] = st.text_area("Instagram Post", value=ai.get("4_instagram_post", ""), height=200, key="rev_ig")
                ai["3_threads_post"] = st.text_area("Threads Post", value=ai.get("3_threads_post", ""), height=100, key="rev_threads")
                ai["5_linkedin_post"] = st.text_area("LinkedIn Post", value=ai.get("5_linkedin_post", ""), height=200, key="rev_li")
            with tabs[2]:
                faq = ai.get("7_faq", {})
                st.write("FAQ (JSON Format)")
                faq["en"] = st.text_area("English FAQ", value=json.dumps(faq.get("en", []), indent=2, ensure_ascii=False), key="rev_faq_en")
                faq["tc"] = st.text_area("Chinese FAQ", value=json.dumps(faq.get("tc", []), indent=2, ensure_ascii=False), key="rev_faq_tc")
                faq["jp"] = st.text_area("Japanese FAQ", value=json.dumps(faq.get("jp", []), indent=2, ensure_ascii=False), key="rev_faq_jp")
            with tabs[3]:
                ai["1_google_slide"] = st.text_input("Google Slide Link", value=ai.get("1_google_slide", ""), key="rev_slide")
            
            if st.button("💾 Sync to Master DB", use_container_width=True, type="primary"):
                with st.spinner("正在同步數據至 Master DB 與 Google Slides..."):
                    if trigger_full_sync():
                        st.balloons()
                        st.success("✅ Sync Success! All data pushed to Master DB and Google Slides.")
                        st.session_state.sync_success = True
                    else: 
                        st.error("❌ Sync Failed! Please check the Debug Terminal for details.")
            st.markdown('</div>', unsafe_allow_html=True)

    with st.expander("🛠️ Debug Terminal", expanded=False):
        st.markdown(f'<div class="debug-terminal">{"\n".join(st.session_state.get("debug_logs", []))}</div>', unsafe_allow_html=True)

def trigger_full_sync():
    try:
        project_id, sort_date = generate_system_metadata()
        processed_imgs = []
        for f in st.session_state.project_photos:
            if hasattr(f, "seek"): 
                f.seek(0)
            img = Image.open(f).convert('RGB')
            img = ImageOps.exif_transpose(img)
            img.thumbnail((1200, 1200))
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=75)
            processed_imgs.append(base64.b64encode(buf.getvalue()).decode())

        ai = st.session_state.ai_content or {}
        
        # Trigger Google Slide creation FIRST
        slide_url = ai.get("1_google_slide", "")
        try:
            slide_payload = {
                "action": "create_slide",
                "project_id": project_id,
                "client_name": st.session_state.client_name,
                "project_name": st.session_state.project_name,
                "category": st.session_state.category,
                "date": f"{st.session_state.event_month} {st.session_state.event_year}",
                "venue": st.session_state.venue,
                "scope": ", ".join(st.session_state.scope),
                "challenge": ai.get("challenge_summary", ""),
                "solution": ai.get("solution_summary", ""),
                "logo_white_base64": st.session_state.logo_white or "",
                "images": processed_imgs
            }
            sr = requests.post(SLIDE_SCRIPT_URL, json=slide_payload, timeout=120)
            if sr.status_code == 200:
                slide_result = extract_json(sr.text)
                if slide_result and slide_result.get("status") == "success" and slide_result.get("slide_url"):
                    slide_url = slide_result["slide_url"]
                    ai["1_google_slide"] = slide_url
                    st.session_state.ai_content = ai
                    log_debug(f"Slide created: {slide_url}")
            else:
                log_debug(f"Slide creation HTTP error: {sr.status_code}")
        except Exception as slide_err:
            log_debug(f"Slide creation error: {str(slide_err)}")

        # Now sync to Master DB
        faq = ai.get("7_faq", {})
        payload = {
            "action": "sync_project",
            "client_name": st.session_state.client_name,
            "project_name": st.session_state.project_name,
            "project_id": project_id,
            "sort_date": sort_date,
            "date": f"{st.session_state.event_month} {st.session_state.event_year}",
            "venue": st.session_state.venue,
            "event_year": st.session_state.event_year,
            "event_month": st.session_state.event_month,
            "youtube": st.session_state.youtube,
            "category": st.session_state.category,
            "category_what": ", ".join(st.session_state.what_we_do),
            "scope": ", ".join(st.session_state.scope),
            "open_question": st.session_state.open_question_ans,
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
