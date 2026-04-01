import streamlit as st
import requests
import json
import time
import random
from PIL import Image, ImageOps
from datetime import datetime

# 🚀 iPhone HEIC Support
try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
except ImportError:
    pass

# ==========================================
# 1. CONFIGURATION & NEON STYLING
# ==========================================
WEB_APP_URL = "https://script.google.com/macros/s/AKfycbyCfSfjgYi7yQFpqBDshjYQ1Zye4VjaT-U4_0nfF9c5oYF1Pr0CrGI38Is4BS3KigIz/exec"
apiKey = "" 
APP_VERSION = "v11.9.6"

st.set_page_config(
    page_title=f"Firebean Brain Collector {APP_VERSION}",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS: Neon Progress + Adaptive Neumorphic
st.markdown("""
    <style>
        [data-testid="stSidebar"] {display: none;}
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}

        /* Neon Red Progress Fixed */
        .progress-hub {
            position: fixed;
            top: 25px;
            right: 40px;
            z-index: 1000;
        }

        /* Neumorphic Foundations */
        .neu-card {
            border-radius: 20px;
            padding: 30px;
            margin-bottom: 25px;
            background: #f0f0f0;
            box-shadow: 12px 12px 24px #bebebe, -12px -12px 24px #ffffff;
            border: 1px solid rgba(255,255,255,0.2);
        }

        @media (prefers-color-scheme: dark) {
            .neu-card {
                background: #1e2128;
                box-shadow: 10px 10px 20px #15171c, -5px -5px 15px #272b34;
            }
        }

        /* MC Question Headers */
        .mc-header {
            color: #FF0000;
            font-weight: 900;
            text-transform: uppercase;
            letter-spacing: 1px;
            border-left: 5px solid #FF0000;
            padding-left: 15px;
            margin: 20px 0 10px 0;
        }

        /* Terminal Debug Box */
        .terminal-box {
            background: #000;
            color: #39ff14;
            font-family: 'Courier New', monospace;
            padding: 15px;
            border-radius: 12px;
            font-size: 12px;
            line-height: 1.6;
            border: 1px solid #333;
            box-shadow: inset 0 0 10px #000;
        }

        /* Neon Circle Animation */
        @keyframes neonPulse {
            0% { filter: drop-shadow(0 0 2px #FF0000); opacity: 0.8; }
            50% { filter: drop-shadow(0 0 12px #FF0000); opacity: 1; }
            100% { filter: drop-shadow(0 0 2px #FF0000); opacity: 0.8; }
        }
        .neon-svg { animation: neonPulse 2.5s infinite ease-in-out; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. UI UTILITIES
# ==========================================
def render_neon_progress(percent):
    circum = 282.7 # 2 * PI * 45
    offset = circum * (1 - percent / 100)
    st.markdown(f"""
    <div class="progress-hub">
        <div style="position:relative; width:110px; height:110px; display:flex; align-items:center; justify-content:center;">
            <svg width="110" height="110" class="neon-svg">
                <circle stroke="rgba(255,0,0,0.1)" stroke-width="10" fill="transparent" r="45" cx="55" cy="55"/>
                <circle stroke="#FF0000" stroke-width="10" stroke-dasharray="{circum}" stroke-dashoffset="{offset}" 
                        stroke-linecap="round" fill="transparent" r="45" cx="55" cy="55" 
                        style="transition: stroke-dashoffset 1s; transform: rotate(-90deg); transform-origin: center;"/>
            </svg>
            <div style="position:absolute; font-size:24px; font-weight:900; color:#FF0000; text-shadow: 0 0 8px rgba(255,0,0,0.6);">{percent}%</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

def call_gemini_ai(prompt, sys_prompt):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-09-2025:generateContent?key={apiKey}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}], 
        "systemInstruction": {"parts": [{"text": sys_prompt}]}, 
        "generationConfig": {"responseMimeType": "application/json"}
    }
    try:
        res = requests.post(url, json=payload, timeout=60)
        if res.status_code == 200:
            return res.json()['candidates'][0]['content']['parts'][0]['text']
    except: pass
    return None

# ==========================================
# 3. APP STATE & BOSS TEST
# ==========================================
if 'page' not in st.session_state: st.session_state.page = 1
if 'form_data' not in st.session_state: st.session_state.form_data = {}
if 'mc_questions' not in st.session_state: st.session_state.mc_questions = []
if 'ai_results' not in st.session_state: st.session_state.ai_results = {}

def run_boss_test():
    st.session_state.form_data = {
        "client": "Firebean Ltd.", "project": "Strategic Neumorphic Rollout", "venue": "HQ Digital Hub",
        "category": ["LIFESTYLE & CONSUMER", "GOVERNMENT & PUBLIC SECTOR"],
        "what_we_do": ["SOCIAL & CONTENT", "INTERACTIVE & TECH", "PR & MEDIA"],
        "scope": ["Event Planning", "Concept Development", "PR Consulting"],
        "drive_folder": "https://drive.google.com/drive/folders/mock_boss_id",
        "open_question": "How can we transform static project data into hyper-responsive, SEO-driven case studies using AI-orchestrated strategy and Neon-Neumorphic UI?"
    }
    st.rerun()

# ==========================================
# 4. PAGE 1: SMART COLLECTOR
# ==========================================
REQUIRED_FIELDS = ["client", "project", "venue", "category", "what_we_do", "scope", "drive_folder", "open_question"]

if st.session_state.page == 1:
    # 1. Progress Logic
    filled = sum(1 for k in REQUIRED_FIELDS if st.session_state.form_data.get(k))
    percent = int((filled / len(REQUIRED_FIELDS)) * 100)
    render_neon_progress(percent)

    st.image("https://raw.githubusercontent.com/dickson-crypto/Firebean-app/main/Firebeanlogo2026.png", width=340)
    
    if st.button("🚀 BOSS TEST MODE (Populate All)", use_container_width=True):
        run_boss_test()

    st.markdown('<div class="neu-card">', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1: client = st.text_input("Client", value=st.session_state.form_data.get("client", ""))
    with c2: project = st.text_input("Project Name", value=st.session_state.form_data.get("project", ""))
    with c3: venue = st.text_input("Venue", value=st.session_state.form_data.get("venue", ""))
    
    st.markdown("---")
    
    # Checkbox Grid
    g1, g2, g3 = st.columns(3)
    with g1:
        st.markdown('<div class="mc-header">Category</div>', unsafe_allow_html=True)
        cat_opts = ["GOVERNMENT & PUBLIC SECTOR", "LIFESTYLE & CONSUMER", "F&B & HOSPITALITY", "MALLS & VENUES"]
        selected_cat = [opt for opt in cat_opts if st.checkbox(opt, key=f"c_{opt}", value=(opt in st.session_state.form_data.get("category", [])))]
    with g2:
        st.markdown('<div class="mc-header">What We Do</div>', unsafe_allow_html=True)
        wwd_opts = ["ROVING EXHIBITIONS", "SOCIAL & CONTENT", "INTERACTIVE & TECH", "PR & MEDIA", "EVENTS & CEREMONIES"]
        selected_wwd = [opt for opt in wwd_opts if st.checkbox(opt, key=f"w_{opt}", value=(opt in st.session_state.form_data.get("what_we_do", [])))]
    with g3:
        st.markdown('<div class="mc-header">Scope of Work</div>', unsafe_allow_html=True)
        sow_opts = ["Event Planning", "Event Production", "Theme Design", "Concept Development", "PR Consulting"]
        selected_sow = [opt for opt in sow_opts if st.checkbox(opt, key=f"s_{opt}", value=(opt in st.session_state.form_data.get("scope", [])))]

    st.markdown("---")
    drive = st.text_input("Google Drive Folder URL (Required for Gallery)", value=st.session_state.form_data.get("drive_folder", ""))
    open_q = st.text_area("核心戰略概念？ AI 將以此為基底進行多維度生成。", value=st.session_state.form_data.get("open_question", ""), height=150)
    st.markdown("</div>", unsafe_allow_html=True)

    # Gated Navigation
    if percent >= 100:
        if st.button("Unlock AI Diagnostic Suite 👉", type="primary", use_container_width=True):
            st.session_state.form_data.update({
                "client":client, "project":project, "venue":venue, 
                "category":selected_cat, "what_we_do":selected_wwd, 
                "scope":selected_sow, "drive_folder":drive, "open_question":open_q
            })
            st.session_state.page = 2
            st.rerun()
    else:
        st.warning(f"Complete all strategic inputs to unlock Step 2 ({percent}% Complete)")

# ==========================================
# 5. PAGE 2: DIAGNOSTIC & SYNC
# ==========================================
elif st.session_state.page == 2:
    st.title("Step 2: Strategic Diagnostic & Master Sync")
    if st.button("← Back"): st.session_state.page = 1; st.rerun()

    l, r = st.columns([1.2, 1])
    
    with l:
        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        if st.button("📝 生成 15 題專業 PR 診斷 (Gemini Engine)", use_container_width=True):
            sys_prompt = "Generate 15 PR diagnostic questions. Output JSON format: [{'q': 'Question', 'opts': ['A','B','C']}]"
            res = call_gemini_ai(f"Project: {st.session_state.form_data['project']}. Core: {st.session_state.form_data['open_question']}", sys_prompt)
            if res: st.session_state.mc_questions = json.loads(res.replace("```json", "").replace("```", ""))
        
        if st.session_state.mc_questions:
            for i, q in enumerate(st.session_state.mc_questions):
                st.markdown(f'<div class="mc-header">Q{i+1}. {q["q"]}</div>', unsafe_allow_html=True)
                for opt in q["opts"]: st.checkbox(opt, key=f"mc_{i}_{opt}")
        st.markdown("</div>", unsafe_allow_html=True)

    with r:
        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        st.markdown('<div class="mc-header">Strategic Terminal</div>', unsafe_allow_html=True)
        log_placeholder = st.empty()
        
        if st.button("🚀 EXECUTE MASTER SYNC", type="primary", use_container_width=True):
            styles = ["Analytical (ROI Focus)", "Narrative (Storytelling)", "Bold (Disruption)", "SEO (Tactical)", "Visionary (Impact)"]
            selected_style = random.choice(styles)
            
            log_placeholder.markdown(f'<div class="terminal-box">> Selected Writing Style: {selected_style}<br>> Generating Multilingual SEO Data...</div>', unsafe_allow_html=True)
            
            # Step 2: AI Generation for Web Content & FAQs
            sys_prompt = f"""
            You are a Top-Tier PR Expert. Output a JSON object only.
            STYLE DIRECTION: {selected_style}
            STRUCTURE:
            - "BoringChallenge": One professional sentence (max 40 words).
            - "CreativeSolution": One creative sentence (max 40 words).
            - "Web": {{ "EN": "HTML", "TC": "HTML", "JP": "HTML" }}
            - "FAQ": {{ "EN": [{"q":"...","a":"..."}], "TC": [...], "JP": [...] }}
            """
            ai_res = call_gemini_ai(f"Concept: {st.session_state.form_data['open_question']}", sys_prompt)
            
            if ai_res:
                st.session_state.ai_results = json.loads(ai_res.replace("```json", "").replace("```", ""))
                log_placeholder.markdown(f'<div class="terminal-box">> AI Content Created.<br>> Selected Style: {selected_style}<br>> Finalizing Sync...</div>', unsafe_allow_html=True)
                
                payload = {
                    **st.session_state.form_data, 
                    "category": ", ".join(st.session_state.form_data['category']),
                    "what_we_do": ", ".join(st.session_state.form_data['what_we_do']),
                    "scope": "\n".join(st.session_state.form_data['scope']),
                    "challenge": st.session_state.ai_results.get("BoringChallenge"),
                    "solution": st.session_state.ai_results.get("CreativeSolution"),
                    "ai_content": st.session_state.ai_results,
                    "date": datetime.now().strftime("%Y %b").upper()
                }
                
                res = requests.post(WEB_APP_URL, json=payload)
                if res.status_code == 200:
                    log_placeholder.markdown('<div class="terminal-box">> SYNC SUCCESSFUL.<br>> Master DB Updated.<br>> GitHub Workflow Triggered.</div>', unsafe_allow_html=True)
                    st.balloons()
                else:
                    st.error("Sync Failed. Check Handlers.gs")
            else:
                st.error("AI Generation Failed.")
        st.markdown("</div>", unsafe_allow_html=True)

st.markdown(f"<p style='text-align: center; color: grey; font-size: 10px;'>Firebean Limited | HQ Strategic Hub {APP_VERSION}</p>", unsafe_allow_html=True)
