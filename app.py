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

# 🚀 FIX: HEIC support for iPhone uploads identified in logs
try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
except ImportError:
    pass

# --- 1. 核心配置 (Updated with your 2026 URLs) ---
SHEET_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbxy6JwJpmclJOBerKJO4EJ50oKyL86Ux1Qci2oHx1RQiw8ruL_Um6qVYsWydyEsLawQ/exec"
SLIDE_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbx_7Xf8_HERQel93WJB2F_KjFOWHtCXzfvEkP9B_p7Kh4ImRAWRgWSXtLklvdbYsqbI/exec"

# 🚀 FIX: Use production-stable string for Pro Tier to resolve 404
STABLE_MODEL_ID = "gemini-1.5-pro" 

WHO_WE_HELP_OPTIONS = ["GOVERNMENT & PUBLIC SECTOR", "LIFESTYLE & CONSUMER", "F&B & HOSPITALITY", "MALLS & VENUES"]
WHAT_WE_DO_OPTIONS = ["ROVING EXHIBITIONS", "SOCIAL & CONTENT", "INTERACTIVE & TECH", "PR & MEDIA", "EVENTS & CEREMONIES"]
SOW_OPTIONS = ["Event Planning", "Event Coordination", "Event Production", "Theme Design", "Concept Development", "Social Media Management", "KOL / MI Line up", "Artist Endorsement", "Media Pitching", "PR Consulting", "Souvenir Sourcing"]

CURRENT_YEAR = datetime.now().year
YEAR_OPTIONS = [str(y) for y in range(CURRENT_YEAR, 2011, -1)]
MONTH_OPTIONS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]

# --- 🛡️ FAQ 扁平化清洗函數 ---
def safe_flatten_faq(faq_input):
    if not faq_input: return "[]"
    if isinstance(faq_input, (list, dict)):
        return json.dumps(faq_input, ensure_ascii=False)
    if isinstance(faq_input, str):
        try:
            return json.dumps(json.loads(faq_input.strip()), ensure_ascii=False)
        except:
            return faq_input.replace("\n", " ").replace("\r", "").strip()
    return "[]"

# --- 系統自動生成邏輯 ---
def generate_system_metadata():
    m_num = {m: str(i+1).zfill(2) for i, m in enumerate(MONTH_OPTIONS)}.get(st.session_state.event_month, "01")
    sort_date = f"{st.session_state.event_year}-{m_num}-01"
    try:
        count_res = requests.get(SHEET_SCRIPT_URL + "?action=get_row_count", timeout=5)
        next_index = int(count_res.text) + 1 if count_res.status_code == 200 else 100
    except:
        next_index = 999 
    return f"FB{st.session_state.event_year}{str(next_index).zfill(3)}", sort_date

FIREBEAN_SYSTEM_PROMPT = """
You are a Lead PR Strategist and Chief Editor. Transform diagnostic data into a professional PR strategy JSON.
Written in past tense retrospective mode. No internal terminology.
"""

# --- 2. 核心邏輯 ---
def log_debug(msg, type="info"):
    if "debug_logs" not in st.session_state: st.session_state.debug_logs = []
    st.session_state.debug_logs.append({"time": datetime.now().strftime("%H:%M:%S"), "msg": msg, "type": type})

def call_gemini_sdk(prompt, image_files=None, is_json=False):
    secret_key = st.secrets.get("GEMINI_API_KEY", "")
    if not secret_key: return None
    try:
        genai.configure(api_key=secret_key)
        model = genai.GenerativeModel(model_name=STABLE_MODEL_ID, system_instruction=FIREBEAN_SYSTEM_PROMPT)
        contents = [prompt]
        if image_files:
            for f in image_files:
                if hasattr(f, "seek"): f.seek(0)
                img = Image.open(f)
                img.thumbnail((800, 800))
                contents.append(img)
        response = model.generate_content(contents)
        if is_json:
            match = re.search(r'(\{.*\})|(\[.*\])', response.text, re.DOTALL)
            return match.group(0) if match else response.text
        return response.text
    except Exception as e:
        log_debug(f"AI API Error: {str(e)}", "error")
        return None

def init_session_state():
    fields = {
        "active_tab": "Project Collector", "client_name": "", "project_name": "", "venue": "", "youtube": "",
        "event_year": str(CURRENT_YEAR), "event_month": "FEB", "category": WHO_WE_HELP_OPTIONS[0],
        "what_we_do": [], "scope": [], "project_photos": [], "ai_content": {}, "logo_white": "", "logo_black": "", 
        "debug_logs": [], "mc_questions": [], "open_question_ans": "", "challenge": "", "solution": "", 
        "hero_photo_index": 0, "sync_success": False, "draft_project_id": "", "loaded_image_urls": [],
        "faq_en_edit": "", "faq_tc_edit": "", "faq_jp_edit": "", 
    }
    for k, v in fields.items():
        if k not in st.session_state: st.session_state[k] = v

def reset_for_new_case():
    init_session_state()
    for i in range(1, 16):
        if f"ans_{i}" in st.session_state: del st.session_state[f"ans_{i}"]
    for w in WHAT_WE_DO_OPTIONS: st.session_state[f"w_{w}"] = False
    for s in SOW_OPTIONS: st.session_state[f"s_{s}"] = False
    st.session_state.active_tab = "Project Collector"

def create_dummy_image(color, label):
    img = Image.new('RGB', (800, 600), color=color)
    ImageDraw.Draw(img).text((40, 40), label, fill=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf

def fill_dummy_data():
    # 🚀 FIX: Correctly set widget keys to select checkboxes visually
    st.session_state.client_name = "Firebean HQ"
    st.session_state.project_name = f"{CURRENT_YEAR} 旗艦同步測試" 
    st.session_state.venue = "香港會議展覽中心"
    st.session_state.category = "LIFESTYLE & CONSUMER"
    
    # 🚀 Visual Checkbox Filling
    st.session_state.what_we_do = ["INTERACTIVE & TECH", "PR & MEDIA"]
    for w in WHAT_WE_DO_OPTIONS: st.session_state[f"w_{w}"] = (w in st.session_state.what_we_do)
    
    st.session_state.scope = ["Theme Design", "Event Production", "Concept Development"]
    for s in SOW_OPTIONS: st.session_state[f"s_{s}"] = (s in st.session_state.scope)

    st.session_state.open_question_ans = "將 15 個通用診斷問題轉化為一套連貫且可操作的跨平台策略。"
    
    # Generate 8 photos and 2 logos
    colors = ["#FF5733", "#33FF57", "#3357FF", "#F333FF", "#33FFF3", "#F3FF33", "#999999", "#222222"]
    st.session_state.project_photos = [create_dummy_image(c, f"P{i+1}") for i, c in enumerate(colors)]
    dummy_logo = base64.b64encode(create_dummy_image("#000000", "LOGO").getvalue()).decode()
    st.session_state.logo_black = dummy_logo
    st.session_state.logo_white = dummy_logo
    
    # Populate 15 MC Answers to hit 100%
    st.session_state.mc_questions = [{"id": i+1, "question": f"診斷指標 {i+1}", "options": ["戰略優化"]} for i in range(15)]
    for i in range(1, 16): st.session_state[f"ans_{i}"] = ["戰略優化"]
    log_debug("🚀 Boss Fill Complete (100% Status).", "success")

# --- 3. UI 元件 (Progress SVG & Night Mode) ---
def get_is_dark_mode():
    from datetime import timezone, timedelta
    hk_tz = timezone(timedelta(hours=8))
    hk_hour = datetime.now(hk_tz).hour
    return hk_hour >= 20 or hk_hour < 8

def get_circle_progress_html(percent, is_dark):
    circum = 439.8
    offset = circum * (1 - percent/100)
    bg, sh_d, sh_l, txt, trk = ("#2A2D35", "#1a1d23", "#3a3f4d", "#E0E5EC", "#1E2128") if is_dark else ("#E0E5EC", "#bec3c9", "#ffffff", "#2D3436", "#d1d9e6")
    return f"""<div style='display: flex; justify-content: flex-end;'><div style='position: relative; width: 110px; height: 110px; border-radius: 50%; background: {bg}; box-shadow: 9px 9px 16px {sh_d}, -9px -9px 16px {sh_l}; display: flex; align-items: center; justify-content: center;'><svg width='110' height='110'><circle stroke='{trk}' stroke-width='8' fill='transparent' r='45' cx='55' cy='55'/><circle stroke='#FF0000' stroke-width='8' stroke-dasharray='{circum}' stroke-dashoffset='{offset}' stroke-linecap='round' fill='transparent' r='45' cx='55' cy='55' style='transition: all 0.8s; transform: rotate(-90deg); transform-origin: center;'/></svg><div style='position: absolute; font-size: 20px; font-weight: 900; color: {txt};'>{percent}%</div></div></div>"""

def apply_styles(is_dark):
    bg, card, sh_d, sh_l, txt, in_bg = ("#1E2128", "#1E2128", "#14161C", "#282C38", "#E0E5EC", "#252830") if is_dark else ("#E0E5EC", "#E0E5EC", "#bec3c9", "#ffffff", "#2D3436", "#e8ecf2")
    st.markdown(f"""<style>
        .stApp {{ background-color: {bg} !important; color: {txt} !important; font-family: 'Inter', sans-serif; }}
        .neu-card {{ background: {card}; border-radius: 20px; box-shadow: 9px 9px 16px {sh_d}, -9px -9px 16px {sh_l}; padding: 25px; margin-bottom: 20px; }}
        div[data-testid="stElementContainer"]:has(#logo-anchor) + div button {{ background-image: url('https://raw.githubusercontent.com/dickson-crypto/Firebean-app/main/Firebeanlogo2026.png') !important; background-size: contain !important; background-repeat: no-repeat !important; min-height: 180px !important; width: 540px !important; background-color: transparent !important; border: none !important; box-shadow: none !important; cursor: pointer; }}
        .mc-question {{ font-weight: 700; color: #FF0000 !important; border-left: 4px solid #FF0000; padding-left: 10px; margin-top: 15px; }}
        .checkbox-group {{ padding-left: 20px; margin-bottom: 10px; }}
    </style>""", unsafe_allow_html=True)

# --- 4. Main App ---
def main():
    st.set_page_config(page_title="Firebean Brain Collector", layout="wide")
    init_session_state()
    is_dark = get_is_dark_mode()
    apply_styles(is_dark)

    c1, c2 = st.columns([1, 1])
    with c1:
        st.markdown('<span id="logo-anchor"></span>', unsafe_allow_html=True)
        if st.button("", key="logo_btn"):
            reset_for_new_case()
            st.rerun()
    with c2:
        # 🚀 RESTORED: 100% Tracking logic (12 items)
        mc_ans = sum([1 for i in range(1, 16) if st.session_state.get(f"ans_{i}")])
        logo_ok = bool(st.session_state.logo_black) and bool(st.session_state.logo_white)
        items = [logo_ok, bool(st.session_state.client_name), bool(st.session_state.project_name), bool(st.session_state.venue), 
                 bool(st.session_state.event_year), bool(st.session_state.event_month), bool(st.session_state.category), 
                 len(st.session_state.what_we_do)>0, len(st.session_state.scope)>0, len(st.session_state.project_photos)>=4, 
                 mc_ans==15, bool(st.session_state.open_question_ans.strip())]
        percent = int((sum(items)/12)*100)
        st.markdown(get_circle_progress_html(percent, is_dark), unsafe_allow_html=True)

    nav_cols = st.columns(4)
    tabs = ["Project Collector", "Review & Multi-Sync", "Load Project", "老細一鍵填充 (深度內容測試)"]
    for i, t in enumerate(tabs[:3]):
        if nav_cols[i].button(t, use_container_width=True, type="primary" if st.session_state.active_tab == t else "secondary"):
            st.session_state.active_tab = t
            st.rerun()
    if nav_cols[3].button(tabs[3], use_container_width=True):
        fill_dummy_data()
        st.rerun()

    st.markdown("---")

    if st.session_state.active_tab == "Project Collector":
        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            ub = st.file_uploader("Black Logo", type=['png'], key="l_b_up")
            if ub: st.session_state.logo_black = base64.b64encode(ub.read()).decode()
            if st.session_state.logo_black: st.image(base64.b64decode(st.session_state.logo_black), width=150)
        with col2:
            uw = st.file_uploader("White Logo", type=['png'], key="l_w_up")
            if uw: st.session_state.logo_white = base64.b64encode(uw.read()).decode()
            if st.session_state.logo_white: st.markdown(f'<div style="background:#333;padding:5px;display:inline-block;"><img src="data:image/png;base64,{st.session_state.logo_white}" width="150"></div>', unsafe_allow_html=True)

        b1, b2, b3 = st.columns(3)
        st.session_state.client_name = b1.text_input("Client", st.session_state.client_name)
        st.session_state.project_name = b2.text_input("Project", st.session_state.project_name)
        st.session_state.venue = b3.text_input("Venue", st.session_state.venue)

        ca, cb, cc = st.columns(3)
        with ca:
            st.markdown("##### Category")
            st.session_state.category = st.radio("Category", WHO_WE_HELP_OPTIONS, index=WHO_WE_HELP_OPTIONS.index(st.session_state.category), label_visibility="collapsed")
        with cb:
            st.markdown("##### What we do")
            # 🚀 Visual Checkbox Sync
            st.session_state.what_we_do = [o for o in WHAT_WE_DO_OPTIONS if st.checkbox(o, key=f"w_{o}", value=st.session_state.get(f"w_{o}", False))]
        with cc:
            st.markdown("##### Scope of work")
            # 🚀 Visual Checkbox Sync
            st.session_state.scope = [o for o in SOW_OPTIONS if st.checkbox(o, key=f"s_{o}", value=st.session_state.get(f"s_{o}", False))]
        st.markdown('</div>', unsafe_allow_html=True)

        cl, cr = st.columns([1.2, 1])
        with cl:
            st.markdown('<div class="neu-card">', unsafe_allow_html=True)
            if st.button("生成 15 題繁中診斷題目"):
                with st.spinner("AI Strategizing..."):
                    res = call_gemini_sdk("生成 15 題專業 PR 診斷 JSON。", image_files=st.session_state.project_photos, is_json=True)
                    if res: st.session_state.mc_questions = json.loads(res)
                    st.rerun()
            
            # 🚀 Bulleted Checkbox Diagnostic
            if st.session_state.mc_questions:
                for q in st.session_state.mc_questions:
                    st.markdown(f"<div class='mc-question'>Q{q['id']}. {q['question']}</div>", unsafe_allow_html=True)
                    st.markdown("<div class='checkbox-group'>", unsafe_allow_html=True)
                    ans_key = f"ans_{q['id']}"
                    current = st.session_state.get(ans_key, [])
                    new_ans = []
                    for opt in q['options']:
                        if st.checkbox(opt, value=(opt in current), key=f"chk_{q['id']}_{opt}"): new_ans.append(opt)
                    st.session_state[ans_key] = new_ans
                    st.markdown("</div>", unsafe_allow_html=True)
            st.session_state.open_question_ans = st.text_area("最核心的概念？", st.session_state.open_question_ans)
            st.markdown('</div>', unsafe_allow_html=True)

        with cr:
            st.markdown('<div class="neu-card">', unsafe_allow_html=True)
            f_up = st.file_uploader("Upload 4-8 Photos", accept_multiple_files=True)
            if f_up: st.session_state.project_photos = f_up
            if st.session_state.project_photos:
                st.session_state.hero_photo_index = st.radio("Select Hero Banner:", range(len(st.session_state.project_photos)), horizontal=True)
                g_cols = st.columns(4)
                for i, f in enumerate(st.session_state.project_photos):
                    with g_cols[i%4]:
                        try:
                            if hasattr(f, "seek"): f.seek(0)
                            st.image(f, width='stretch')
                        except: st.image(f, width='stretch')
            st.markdown('</div>', unsafe_allow_html=True)

        # 🚀 RESTORED: Navigation drive to Page 2 at 100%
        if percent >= 100:
            st.markdown("---")
            st.success("🎉 完美！進度達 100%！")
            if st.button("準備就緒，前往 Review & Multi-Sync 👉", type="primary", use_container_width=True):
                st.session_state.active_tab = "Review & Multi-Sync"
                st.rerun()

    elif st.session_state.active_tab == "Review & Multi-Sync":
        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        if st.button("生成六大平台對接文案"):
            with st.spinner("AI Generating..."):
                res = call_gemini_sdk("生成文案 JSON。", is_json=True)
                if res: st.session_state.ai_content = json.loads(res)
        
        if st.session_state.ai_content:
            st.json(st.session_state.ai_content)
            if st.button("Confirm & Sync"):
                with st.spinner("🔄 Sequential Syncing (2026 Ready)..."):
                    pid, sdate = generate_system_metadata()
                    processed_imgs = []
                    for f in st.session_state.project_photos:
                        if hasattr(f, "seek"): f.seek(0)
                        try: img = Image.open(f).convert("RGB")
                        except: img = f.convert("RGB") # Handle boss fill dummy
                        buf = io.BytesIO()
                        img.save(buf, format="JPEG", quality=85)
                        processed_imgs.append(base64.b64encode(buf.getvalue()).decode())

                    payload = {
                        "action": "sync_project", "project_id": pid, "sort_date": sdate,
                        "client_name": st.session_state.client_name, "project_name": st.session_state.project_name,
                        "images": processed_imgs, "logo_white": st.session_state.logo_white,
                        "faq_en": safe_flatten_faq(st.session_state.faq_en_edit),
                    }
                    requests.post(SHEET_SCRIPT_URL, json=payload, timeout=60)
                    payload["action"] = "create_slide"
                    payload["photos"] = processed_imgs
                    payload["logo_white_base64"] = st.session_state.logo_white
                    requests.post(SLIDE_SCRIPT_URL, json=payload, timeout=60)
                    st.balloons()
                    st.success(f"Successfully Synced: {pid}")

    with st.expander("🛠️ Debug Terminal", expanded=False):
        logs = "".join([f"<div>[{l['time']}] {l['msg']}</div>" for l in reversed(st.session_state.get("debug_logs", []))])
        st.markdown(f"<div class='debug-terminal'>{logs}</div>", unsafe_allow_html=True)

if __name__ == "__main__": main()
