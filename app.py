import streamlit as st
import requests
import json
import time
from PIL import Image, ImageOps
import io
from datetime import datetime

# ==========================================
# 1. CONFIGURATION & NEUMORPHIC STYLING
# ==========================================
# ACTION: Ensure your Apps Script Web App URL is pasted here
WEB_APP_URL = "https://script.google.com/macros/s/.../exec"
apiKey = "" # Environment provides the key automatically
APP_VERSION = "v11.4.5"

st.set_page_config(
    page_title=f"Firebean Brain Collector {APP_VERSION}",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for Neumorphic Design & Adaptive Themes (Light/Dark)
st.markdown("""
    <style>
        [data-testid="stSidebar"] {display: none;}
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        
        /* Neumorphic Card Styling */
        .neu-card {
            border-radius: 20px;
            padding: 30px;
            margin-bottom: 25px;
            box-shadow: 10px 10px 20px rgba(0,0,0,0.1), -10px -10px 20px rgba(255,255,255,0.7);
            border: 1px solid rgba(255,255,255,0.2);
        }
        
        /* Progress Circle Container */
        .progress-container {
            display: flex;
            justify-content: flex-end;
            margin-bottom: -80px;
            padding-right: 20px;
        }

        /* Navigation Buttons */
        .stButton > button {
            border-radius: 12px;
            font-weight: bold;
            transition: all 0.3s;
        }
        
        .next-btn > div > button {
            background-color: #ff4b4b !important;
            color: white !important;
            padding: 15px 0px !important;
            width: 100% !important;
            font-size: 18px !important;
            box-shadow: 0 4px 15px rgba(255, 75, 75, 0.3);
            border: none !important;
        }

        /* Status Message Boxes */
        .status-box {
            padding: 15px;
            border-radius: 10px;
            margin-bottom: 15px;
            font-weight: 600;
        }
        .status-yellow { background-color: #FFF2CC; color: #856404; }
        .status-green { background-color: #D9EAD3; color: #274E13; }

        /* MC Question Headers */
        .mc-header {
            color: #FF0000;
            font-weight: bold;
            border-left: 4px solid #FF0000;
            padding-left: 10px;
            margin-top: 20px;
        }

        /* AI Purple Buttons */
        .ai-btn > div > button {
            background-color: #7B61FF !important;
            color: white !important;
            border: none !important;
            font-size: 14px !important;
        }
        
        /* Dark mode support */
        @media (prefers-color-scheme: dark) {
            .neu-card {
                box-shadow: 10px 10px 20px rgba(0,0,0,0.4), -5px -5px 15px rgba(255,255,255,0.05);
                background-color: #1E2128;
                border: 1px solid rgba(255,255,255,0.1);
            }
        }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. UTILITIES & AI ENGINE
# ==========================================
def get_progress_circle(percent):
    circum = 439.8
    offset = circum * (1 - percent / 100)
    return f"""
    <div class="progress-container">
        <div style="position:relative; width:110px; height:110px; display:flex; align-items:center; justify-content:center;">
            <svg width="110" height="110">
                <circle stroke="#e8ecf2" stroke-width="8" fill="transparent" r="45" cx="55" cy="55"/>
                <circle stroke="#FF0000" stroke-width="8" stroke-dasharray="{circum}" stroke-dashoffset="{offset}" 
                        stroke-linecap="round" fill="transparent" r="45" cx="55" cy="55" 
                        style="transition: stroke-dashoffset 0.8s; transform: rotate(-90deg); transform-origin: center;"/>
            </svg>
            <div style="position:absolute; font-size:22px; font-weight:900;">{percent}%</div>
        </div>
    </div>
    """

def call_gemini_ai(prompt, system_instruction="", progress_msg="AI Processing..."):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-09-2025:generateContent?key={apiKey}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}], 
        "systemInstruction": {"parts": [{"text": system_instruction}]},
        "generationConfig": {"responseMimeType": "application/json"} if "JSON" in system_instruction else {}
    }
    
    with st.status(progress_msg, expanded=True) as status:
        st.write("📡 Connecting to Firebean Strategic Engine...")
        try:
            res = requests.post(url, json=payload, timeout=60)
            if res.status_code == 200:
                status.update(label="✅ Strategy Crafted!", state="complete", expanded=False)
                return res.json()['candidates'][0]['content']['parts'][0]['text'].strip()
        except Exception as e:
            st.error(f"AI Connection Failed: {e}")
    return None

# ==========================================
# 3. STATE & BOSS TEST LOGIC
# ==========================================
if 'page' not in st.session_state: st.session_state.page = 1
if 'form_data' not in st.session_state: st.session_state.form_data = {}
if 'mc_questions' not in st.session_state: st.session_state.mc_questions = []
if 'ai_results' not in st.session_state: st.session_state.ai_results = {}
if 'mock_assets' not in st.session_state: st.session_state.mock_assets = False

def run_boss_test():
    st.session_state.form_data = {
        "client": "Firebean Limited",
        "project": f"Strategic CMS Launch {APP_VERSION}",
        "venue": "Digital Experience Hub",
        "year": "2026",
        "month": "MAR",
        "youtube": "https://youtube.com/firebean_cms",
        "category": ["LIFESTYLE & CONSUMER"],
        "what_we_do": ["SOCIAL & CONTENT", "INTERACTIVE & TECH"],
        "scope": ["Event Planning", "Concept Development"],
        "challenge": "Transforming static project data into strategic evergreen case studies for better SEO.",
        "solution": f"Integrated Gemini AI with a Neumorphic UI ({APP_VERSION}) to automate multi-platform strategic recaps.",
        "drive_folder": "https://drive.google.com/drive/folders/test_folder_id"
    }
    st.session_state.mock_assets = True
    st.rerun()

# ==========================================
# 4. PAGE 1: PROJECT COLLECTOR
# ==========================================
required_keys = ["client", "project", "venue", "category", "what_we_do", "scope", "challenge", "solution", "drive_folder"]

if st.session_state.page == 1:
    # 1. Calculate Progress
    filled = sum(1 for k in required_keys if st.session_state.form_data.get(k))
    if st.session_state.mock_assets: filled += 1
    percent = int((filled / (len(required_keys) + 1)) * 100)
    
    # 2. Header
    st.markdown(get_progress_circle(percent), unsafe_allow_html=True)
    st.image("https://raw.githubusercontent.com/dickson-crypto/Firebean-app/main/Firebeanlogo2026.png", width=340)
    
    if st.button("🚀 老細一鍵填充 (Boss Test Mode)", use_container_width=True):
        run_boss_test()

    st.markdown('<div class="neu-card">', unsafe_allow_html=True)
    
    c1, c2, c3 = st.columns(3)
    with c1: client = st.text_input("Client", value=st.session_state.form_data.get("client", ""))
    with c2: project = st.text_input("Project", value=st.session_state.form_data.get("project", ""))
    with c3: venue = st.text_input("Venue", value=st.session_state.form_data.get("venue", ""))
    
    d1, d2, d3 = st.columns(3)
    with d1: year = st.selectbox("Year", [str(y) for y in range(2026, 2019, -1)], index=0)
    with d2: month = st.selectbox("Month", ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"], index=2)
    with d3: youtube = st.text_input("YouTube URL (optional)", value=st.session_state.form_data.get("youtube", ""))

    st.markdown("<br>", unsafe_allow_html=True)
    
    # Checkbox Selection Groups
    g1, g2, g3 = st.columns(3)
    with g1:
        st.markdown("**Category**")
        cat_opts = ["GOVERNMENT & PUBLIC SECTOR", "LIFESTYLE & CONSUMER", "F&B & HOSPITALITY", "MALLS & VENUES"]
        selected_cat = [opt for opt in cat_opts if st.checkbox(opt, key=f"cat_{opt}", value=(opt in st.session_state.form_data.get("category", [])))]
    with g2:
        st.markdown("**What we do**")
        wwd_opts = ["ROVING EXHIBITIONS", "SOCIAL & CONTENT", "INTERACTIVE & TECH", "PR & MEDIA", "EVENTS & CEREMONIES"]
        selected_wwd = [opt for opt in wwd_opts if st.checkbox(opt, key=f"wwd_{opt}", value=(opt in st.session_state.form_data.get("what_we_do", [])))]
    with g3:
        st.markdown("**Scope of work**")
        sow_opts = ["Event Planning", "Event Production", "Theme Design", "Concept Development", "PR Consulting"]
        selected_sow = [opt for opt in sow_opts if st.checkbox(opt, key=f"sow_{opt}", value=(opt in st.session_state.form_data.get("scope", [])))]
    
    st.markdown("---")
    
    # Text Areas with SEO Enhance
    st.write("**Boring Challenge (Recap Focus)**")
    ch_1, ch_2 = st.columns([0.88, 0.12])
    with ch_1: challenge = st.text_area("Challenge", value=st.session_state.form_data.get("challenge", ""), height=100, label_visibility="collapsed")
    with ch_2:
        st.markdown('<div class="ai-btn" style="margin-top:30px;">', unsafe_allow_html=True)
        if st.button("✨ SEO", key="ai_ch"):
            res = call_gemini_ai(f"Enhance this for SEO and searchability: {challenge}", "Expert PR strategist. Focus on keywords.", "✨ Optimizing for Search...")
            if res: st.session_state.form_data["challenge"] = res; st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    st.write("**Creative Solution (Recap Focus)**")
    so_1, so_2 = st.columns([0.88, 0.12])
    with so_1: solution = st.text_area("Solution", value=st.session_state.form_data.get("solution", ""), height=100, label_visibility="collapsed")
    with so_2:
        st.markdown('<div class="ai-btn" style="margin-top:30px;">', unsafe_allow_html=True)
        if st.button("✨ SEO", key="ai_so"):
            res = call_gemini_ai(f"Enhance this for SEO and searchability: {solution}", "Creative PR tone. Focus on innovation.", "✨ Optimizing for Search...")
            if res: st.session_state.form_data["solution"] = res; st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    drive_folder = st.text_input("Drive Link", value=st.session_state.form_data.get("drive_folder", ""))
    st.markdown("</div>", unsafe_allow_html=True)

    # Assets & MC Questions Section
    cl, cr = st.columns([1.2, 1])
    with cl:
        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        if st.button("生成 15 題繁中診斷題目"):
            prompt = f"為項目 {project} 生成 15 題專業 PR 診斷多選題。格式: JSON [{{'id':1, 'q':'...', 'o':['A','B','C']}}]"
            res = call_gemini_ai(prompt, "Output valid JSON only. Strategic diagnostic tone.", "📝 Generating Questions...")
            if res: 
                try: st.session_state.mc_questions = json.loads(res.replace("```json", "").replace("```", ""))
                except: st.error("AI Output Format Error.")
        
        if st.session_state.mc_questions:
            for q in st.session_state.mc_questions:
                st.markdown(f'<div class="mc-header">Q{q["id"]}. {q["q"]}</div>', unsafe_allow_html=True)
                for opt in q["o"]: st.checkbox(opt, key=f"mc_{q['id']}_{opt}")
        st.markdown('</div>', unsafe_allow_html=True)

    with cr:
        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        photos = st.file_uploader("Upload Project Photos (min 4)", accept_multiple_files=True)
        if st.session_state.mock_assets: st.info("✅ Boss Test: Mock Assets Loaded.")
        if photos:
            st.session_state.mock_assets = False
            p_cols = st.columns(4)
            for i, p in enumerate(photos[:8]):
                with p_cols[i%4]:
                    img = ImageOps.exif_transpose(Image.open(p)) # Auto-orientation fix
                    st.image(img, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # Progress Messaging & Navigation
    st.markdown("---")
    status_class = "status-green" if percent >= 100 else "status-yellow"
    status_msg = f"進度 {percent}% — " + ("完美！準備同步！" if percent >= 100 else "請填寫所有必填欄位")
    st.markdown(f'<div class="status-box {status_class}">{status_msg}</div>', unsafe_allow_html=True)

    if st.button("前往 Review & Multi-Sync 👉", type="primary", use_container_width=True):
        st.session_state.form_data.update({
            "client":client, "project":project, "venue":venue, "date":f"{month} {year}",
            "category":", ".join(selected_cat), "what_we_do":", ".join(selected_wwd), 
            "scope":", ".join(selected_sow), "challenge":challenge, "solution":solution, 
            "drive_folder":drive_folder, "youtube":youtube
        })
        st.session_state.page = 2
        st.rerun()

# ==========================================
# 5. PAGE 2: REVIEW & AI STRATEGY
# ==========================================
elif st.session_state.page == 2:
    st.title("Step 2: SEO & AI Search Engine")
    if st.button("← Back to Collector"): st.session_state.page = 1; st.rerun()

    st.markdown('<div class="neu-card">', unsafe_allow_html=True)
    if st.button("🚀 生成 6 平台文案 + SEO & AI Search Metadata", type="primary", use_container_width=True):
        sys_prompt = """
        You are a Top-Tier PR & SEO Expert. Generate a unique JSON response for 6 platforms.
        
        SEO & SEARCH READABILITY:
        1. Web Content: Use Semantic HTML tags (h1, h2, p).
        2. Content Variety: Rotate styles (Analytical, Storytelling).
        3. Searchability: Use bullet points and strategic headers for AI crawlers.
        
        Output JSON only.
        """
        user_prompt = f"Project: {st.session_state.form_data['project']}. Client: {st.session_state.form_data['client']}. Category: {st.session_state.form_data['category']}. Challenge: {st.session_state.form_data['challenge']}. Solution: {st.session_state.form_data['solution']}."
        res = call_gemini_ai(user_prompt, sys_prompt, "🚀 Optimizing for Search Engines...")
        if res:
            try: st.session_state.ai_results = json.loads(res.replace("```json", "").replace("```", ""))
            except: st.error("AI JSON Format Error.")

    if st.session_state.ai_results:
        with st.expander("LinkedIn (Professional EN)", expanded=True): st.write(st.session_state.ai_results.get("LinkedIn"))
        with st.expander("Facebook (Conversational Cantonese)"): st.write(st.session_state.ai_results.get("Facebook"))
        with st.expander("Web Article (SEO HTML Preview)"):
            web_data = st.session_state.ai_results.get("Web", {})
            st.markdown(web_data.get("TC", web_data.get("web_tc", "No content")), unsafe_allow_html=True)

    st.write("---")
    if st.button("✅ Confirm & Sync to Master DB", type="primary", use_container_width=True):
        with st.status("📡 Synchronizing SEO Data...") as status:
            payload = {**st.session_state.form_data, "ai_content": st.session_state.ai_results}
            try:
                res = requests.post(WEB_APP_URL, json=payload, timeout=30)
                if res.status_code == 200:
                    status.update(label="✅ Master DB Synced!", state="complete")
                    st.balloons(); time.sleep(2)
                    st.session_state.form_data = {}; st.session_state.page = 1; st.rerun()
                else:
                    st.error(f"Sync Failed: {res.text}")
            except Exception as e:
                st.error(f"Connection Error: {e}")
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown(f"<p style='text-align: center; color: grey; font-size: 10px;'>Firebean Limited CMS {APP_VERSION} | Strategy-Driven Portal</p>", unsafe_allow_html=True)
