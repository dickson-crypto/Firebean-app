import streamlit as st
import requests
import json
import time
import random
from PIL import Image, ImageOps
from datetime import datetime

# ==========================================
# 1. CONFIGURATION & NEUMORPHIC STYLING
# ==========================================
WEB_APP_URL = "https://script.google.com/macros/s/.../exec" # 請填入你的部署網址
apiKey = "" 
APP_VERSION = "v11.8.5"

st.set_page_config(
    page_title=f"Firebean Brain Collector {APP_VERSION}",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Neumorphic UI Styling
st.markdown("""
    <style>
        [data-testid="stSidebar"] {display: none;}
        .neu-card {
            border-radius: 20px;
            padding: 30px;
            margin-bottom: 25px;
            box-shadow: 10px 10px 20px rgba(0,0,0,0.1), -10px -10px 20px rgba(255,255,255,0.7);
            border: 1px solid rgba(255,255,255,0.2);
        }
        .stButton > button { border-radius: 12px; font-weight: bold; height: 50px; }
        @media (prefers-color-scheme: dark) {
            .neu-card { box-shadow: 10px 10px 20px rgba(0,0,0,0.4), -5px -5px 15px rgba(255,255,255,0.05); background-color: #1E2128; }
        }
    </style>
""", unsafe_allow_html=True)

# --- AI RULES (Synchronized from Main.gs) ---
WRITING_DIRECTIONS = [
    "Analytical & Data-Driven (Focus on ROI and Metrics)",
    "Narrative & Story-Based (Focus on the Client Journey)",
    "Provocative & Bold (Focus on Industry Disruption)",
    "SEO-Focused & Tactical (Focus on keywords and execution details)",
    "Futuristic & Visionary (Focus on long-term impact and innovation)"
]

# ==========================================
# 2. UTILITIES
# ==========================================
def call_gemini_ai(prompt, system_instruction="", progress_msg="AI Processing..."):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-09-2025:generateContent?key={apiKey}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}], 
        "systemInstruction": {"parts": [{"text": system_instruction}]},
        "generationConfig": {"responseMimeType": "application/json"}
    }
    with st.status(progress_msg, expanded=True) as status:
        try:
            res = requests.post(url, json=payload, timeout=60)
            if res.status_code == 200:
                status.update(label="✅ Strategy Crafted!", state="complete")
                return res.json()['candidates'][0]['content']['parts'][0]['text']
        except Exception as e:
            st.error(f"AI Failed: {e}")
    return None

# ==========================================
# 3. PAGE 1: COLLECTOR
# ==========================================
if 'page' not in st.session_state: st.session_state.page = 1
if 'form_data' not in st.session_state: st.session_state.form_data = {}
if 'ai_results' not in st.session_state: st.session_state.ai_results = {}

if st.session_state.page == 1:
    st.image("https://raw.githubusercontent.com/dickson-crypto/Firebean-app/main/Firebeanlogo2026.png", width=340)
    st.title("Project Collector & Brain Sync")

    st.markdown('<div class="neu-card">', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1: client = st.text_input("Client", value=st.session_state.form_data.get("client", ""))
    with c2: project = st.text_input("Project Name", value=st.session_state.form_data.get("project", ""))
    with c3: venue = st.text_input("Venue", value=st.session_state.form_data.get("venue", ""))
    
    st.markdown("**Category (Controls Website Filters)**")
    cat_opts = ["GOVERNMENT & PUBLIC SECTOR", "LIFESTYLE & CONSUMER", "F&B & HOSPITALITY", "MALLS & VENUES"]
    selected_cat = [opt for opt in cat_opts if st.checkbox(opt, key=f"cat_{opt}")]
    
    st.markdown("**What We Do**")
    wwd_opts = ["ROVING EXHIBITIONS", "SOCIAL & CONTENT", "INTERACTIVE & TECH", "PR & MEDIA", "EVENTS & CEREMONIES"]
    selected_wwd = [opt for opt in wwd_opts if st.checkbox(opt, key=f"wwd_{opt}")]

    st.markdown("**Gallery Assets**")
    drive_folder = st.text_input("Google Drive Folder URL (Required for Photo 1-8)", value=st.session_state.form_data.get("drive_folder", ""))
    
    st.markdown("**Strategic Input**")
    open_question = st.text_area("最核心的概念？ AI 將以此生成全平台文案。", value=st.session_state.form_data.get("open_question", ""), height=150)
    st.markdown("</div>", unsafe_allow_html=True)

    if st.button("Review & AI Strategy 👉", type="primary", use_container_width=True):
        st.session_state.form_data.update({
            "client":client, "project":project, "venue":venue,
            "category":", ".join(selected_cat), "what_we_do":", ".join(selected_wwd), 
            "drive_folder": drive_folder, "open_question":open_question,
            "date": datetime.now().strftime("%Y %b").upper()
        })
        st.session_state.page = 2
        st.rerun()

# ==========================================
# 4. PAGE 2: AI STRATEGY & SYNC
# ==========================================
elif st.session_state.page == 2:
    st.title("Step 2: AI Strategy Optimization")
    if st.button("← Back"): st.session_state.page = 1; st.rerun()

    st.markdown('<div class="neu-card">', unsafe_allow_html=True)
    if st.button("🚀 生成戰略文案 (隨機選擇寫作風格)", type="primary", use_container_width=True):
        direction = random.choice(WRITING_DIRECTIONS)
        st.info(f"AI 寫作方向：{direction}")
        
        sys_prompt = f"""
        You are a Top-Tier PR Expert. Output a JSON object only.
        STYLE DIRECTION: {direction}
        STRUCTURE:
        - "BoringChallenge": One professional sentence (max 40 words).
        - "CreativeSolution": One creative sentence (max 40 words).
        - "Web": {{ "EN": "3-4 Paragraphs HTML", "TC": "3-4 Paragraphs HTML", "JP": "3-4 Paragraphs HTML" }}
        - "FAQ": {{ "EN": [{"q":"...","a":"..."}], "TC": [...], "JP": [...] }}
        RULES: Each Web content must have 2 H2 subtitles and end with a bold punchline.
        """
        prompt = f"Concept: {st.session_state.form_data['open_question']}. Client: {st.session_state.form_data['client']}."
        res = call_gemini_ai(prompt, sys_prompt, "📊 Generating Multilingual Strategy...")
        if res: st.session_state.ai_results = json.loads(res.replace("```json", "").replace("```", ""))

    if st.session_state.ai_results:
        st.subheader("Preview")
        st.write(f"**Challenge:** {st.session_state.ai_results.get('BoringChallenge')}")
        st.write(f"**Solution:** {st.session_state.ai_results.get('CreativeSolution')}")
        
        if st.button("✅ Confirm & Master Sync", type="primary", use_container_width=True):
            payload = {
                **st.session_state.form_data, 
                "challenge": st.session_state.ai_results.get("BoringChallenge"),
                "solution": st.session_state.ai_results.get("CreativeSolution"),
                "ai_content": st.session_state.ai_results,
                "scope": "Concept Development, Event Production" # Default scope
            }
            res = requests.post(WEB_APP_URL, json=payload, timeout=60)
            if res.status_code == 200:
                st.success("Synced to Master DB!"); st.balloons()
                time.sleep(2); st.session_state.page = 1; st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown(f"<p style='text-align: center; color: grey; font-size: 10px;'>Firebean Limited CMS {APP_VERSION}</p>", unsafe_allow_html=True)
