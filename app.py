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

# --- 1. 核心配置 (Updated with New Deployment URLs) ---
SHEET_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbxy6JwJpmclJOBerKJO4EJ50oKyL86Ux1Qci2oHx1RQiw8ruL_Um6qVYsWydyEsLawQ/exec"
SLIDE_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbxKP-8Xrvy6hblPqTmtXn76rO3DFOeU6jYQtLw5QDfDP1-adNDk02bhoKihfvp_Xsvy/exec"
# Note: Master DB Slide Creator URL (Secondary) is reserved if you need to switch slide templates.
STABLE_MODEL_ID = "gemini-2.0-flash" # Optimized for speed and vision

WHO_WE_HELP_OPTIONS = ["GOVERNMENT & PUBLIC SECTOR", "LIFESTYLE & CONSUMER", "F&B & HOSPITALITY", "MALLS & VENUES"]
WHAT_WE_DO_OPTIONS = ["ROVING EXHIBITIONS", "SOCIAL & CONTENT", "INTERACTIVE & TECH", "PR & MEDIA", "EVENTS & CEREMONIES"]
SOW_OPTIONS = ["Event Planning", "Event Coordination", "Event Production", "Theme Design", "Concept Development", "Social Media Management", "KOL / MI Line up", "Artist Endorsement", "Media Pitching", "PR Consulting", "Souvenir Sourcing"]

CURRENT_YEAR = datetime.now().year
YEAR_OPTIONS = [str(y) for y in range(CURRENT_YEAR, 2011, -1)]
MONTH_OPTIONS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]

# --- 🛡️ FAQ 扁平化清洗函數 ---
def safe_flatten_faq(faq_input):
    if not faq_input:
        return "[]"
    if isinstance(faq_input, (list, dict)):
        return json.dumps(faq_input, ensure_ascii=False)
    if isinstance(faq_input, str):
        faq_input = faq_input.strip()
        if not faq_input:
            return "[]"
        try:
            parsed = json.loads(faq_input)
            return json.dumps(parsed, ensure_ascii=False)
        except Exception as e:
            log_debug(f"FAQ 扁平化警告: {str(e)}", "warning")
            return faq_input.replace("\n", " ").replace("\r", "").strip()
    return "[]"

# --- 系統自動生成邏輯 (ID 與 日期) ---
def generate_system_metadata():
    month_map = {m: str(i+1).zfill(2) for i, m in enumerate(MONTH_OPTIONS)}
    m_num = month_map.get(st.session_state.event_month, "01")
    sort_date = f"{st.session_state.event_year}-{m_num}-01"

    try:
        count_res = requests.get(SHEET_SCRIPT_URL + "?action=get_row_count", timeout=5)
        next_index = int(count_res.text) + 1 if count_res.status_code == 200 else 100
    except:
        next_index = 999 
    
    project_id = f"FB{st.session_state.event_year}{str(next_index).zfill(3)}"
    return project_id, sort_date

FIREBEAN_SYSTEM_PROMPT = """
You are a Lead PR Strategist and Chief Editor for a premium B2B/B2C communications agency.
Task: Transform diagnostic data into a professional PR strategy JSON.
Always return a valid JSON object with keys: challenge_summary, solution_summary, 1_google_slide, 2_facebook_post, 3_threads_post, 4_instagram_post, 5_linkedin_post, 6_website, 7_faq.

**ABSOLUTE RULE 1 — POST-EVENT RETROSPECTIVE MODE**:
This tool is EXCLUSIVELY used AFTER an event has already taken place. All content you generate MUST be written as a retrospective case showcase.

**ABSOLUTE RULE 2 — INTERNAL TERMINOLOGY PROHIBITION**:
NEVER use the phrase "Firebean Brain". Instead, use professional alternatives like "Our strategic approach".
"""

# --- 2. 核心邏輯 ---

def log_debug(msg, type="info"):
    if "debug_logs" not in st.session_state: st.session_state.debug_logs = []
    timestamp = datetime.now().strftime("%H:%M:%S")
    st.session_state.debug_logs.append({"time": timestamp, "msg": msg, "type": type})

def call_gemini_sdk(prompt, image_files=None, is_json=False, max_retries=2):
    secret_key = st.secrets.get("GEMINI_API_KEY", "")
    if not secret_key:
        st.error("🚨 找不到 API Key")
        return None

    for attempt in range(max_retries):
        try:
            genai.configure(api_key=secret_key)
            model = genai.GenerativeModel(model_name=STABLE_MODEL_ID, system_instruction=FIREBEAN_SYSTEM_PROMPT)
            contents = [prompt]

            if image_files:
                for f in image_files:
                    if hasattr(f, "seek"): f.seek(0)
                    img = Image.open(f)
                    img = ImageOps.exif_transpose(img)
                    img.thumbnail((800, 800))
                    contents.append(img)

            response = model.generate_content(contents, generation_config={
                "response_mime_type": "application/json" if is_json else "text/plain",
                "temperature": 0.2
            })

            if response and response.text:
                text = response.text.strip()
                if not is_json:
                    return text
                match = re.search(r'(\{.*\})|(\[.*\])', text, re.DOTALL)
                json_str = match.group(0) if match else text
                json.loads(json_str)
                return json_str

        except json.JSONDecodeError as je:
            log_debug(f"⚠️ JSON 解析失敗 (第 {attempt+1} 次)，正在重試...", "error")
            if attempt < max_retries - 1:
                time.sleep(1)
                continue
            else:
                st.warning("⚠️ AI 返回格式不穩定，請再試一次。")
        except Exception as e:
            log_debug(f"❌ API 錯誤: {str(e)}", "error")
            st.error("❌ AI 運算發生錯誤。")
            break
    return None

def init_session_state():
    fields = {
        "active_tab": "Project Collector",
        "client_name": "", "project_name": "", "venue": "", "youtube": "",
        "event_year": str(CURRENT_YEAR), 
        "event_month": "FEB",
        "category": WHO_WE_HELP_OPTIONS[0], "what_we_do": [], "scope": [],
        "project_photos": [], "ai_content": {}, "logo_white": "", "logo_black": "", 
        "debug_logs": [], "mc_questions": [], "open_question_ans": "", 
        "challenge": "", "solution": "", "visual_facts": "",
        "hero_photo_index": 0,
        "sync_success": False,  
        "draft_project_id": "",  
        "loaded_image_urls": [],  
        "faq_en_edit": "",  
        "faq_tc_edit": "",  
        "faq_jp_edit": "",  
    }
    for k, v in fields.items():
        if k not in st.session_state:
            st.session_state[k] = v

def reset_for_new_case():
    keys_to_reset = [
        "client_name", "project_name", "venue", "youtube",
        "event_year", "event_month", "category", "what_we_do", "scope",
        "project_photos", "ai_content", "logo_white", "logo_black",
        "mc_questions", "open_question_ans", "challenge", "solution",
        "visual_facts", "hero_photo_index", "sync_success",
        "draft_project_id", "loaded_image_urls",
        "faq_en_edit", "faq_tc_edit", "faq_jp_edit"
    ]
    defaults = {
        "event_year": str(CURRENT_YEAR), "event_month": "FEB",
        "category": WHO_WE_HELP_OPTIONS[0], "what_we_do": [], "scope": [],
        "project_photos": [], "ai_content": {}, "hero_photo_index": 0,
        "sync_success": False,
        "draft_project_id": "",
        "loaded_image_urls": []
    }
    for k in keys_to_reset:
        st.session_state[k] = defaults.get(k, "")
    for i in range(1, 16):
        if f"ans_{i}" in st.session_state: del st.session_state[f"ans_{i}"]
    for key in ["l_b", "l_w"]:
        if key in st.session_state: del st.session_state[key]
    st.session_state.active_tab = "Project Collector"
    log_debug("🔄 已重置。", "success")

def create_dummy_image(color, label):
    img = Image.new('RGB', (800, 600), color=color)
    d = ImageDraw.Draw(img)
    d.text((40, 40), label, fill=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    buf.seek(0)
    return buf

def fill_dummy_data():
    st.session_state.client_name = "Firebean HQ"
    st.session_state.project_name = f"{CURRENT_YEAR} 旗艦同步測試" 
    st.session_state.venue = "香港會議展覽中心"
    st.session_state.youtube = "https://youtube.com/firebean_sync_demo"
    st.session_state.event_year = str(CURRENT_YEAR) 
    st.session_state.event_month = "FEB"
    st.session_state.category = "LIFESTYLE & CONSUMER"
    st.session_state.what_we_do = ["INTERACTIVE & TECH", "PR & MEDIA"]
    st.session_state.scope = ["Theme Design", "Event Production", "Concept Development"]
    st.session_state.open_question_ans = "將 15 個通用診斷問題轉化為一套連貫、引人入勝且可操作的跨平台策略。"
    colors = ["#FF5733", "#33FF57", "#3357FF", "#F333FF", "#33FFF3", "#F3FF33", "#999999", "#222222"]
    st.session_state.project_photos = [create_dummy_image(c, f"P{i+1}") for i, c in enumerate(colors)]
    st.session_state.mc_questions = [{"id": i+1, "question": f"診斷指標 {i+1}？", "options": ["戰略優化", "維持"]} for i in range(15)]
    for i in range(1, 16): st.session_state[f"ans_{i}"] = ["戰略優化"]
    dummy_logo = base64.b64encode(create_dummy_image("#000000", "LOGO").getvalue()).decode()
    st.session_state.logo_black = dummy_logo
    st.session_state.logo_white = dummy_logo

# --- 3. UI 元件 ---

def get_is_dark_mode():
    from datetime import timezone, timedelta
    hk_tz = timezone(timedelta(hours=8))
    hk_hour = datetime.now(hk_tz).hour
    return hk_hour >= 20 or hk_hour < 8

def get_circle_progress_html(percent, is_dark):
    circum = 439.8
    offset = circum * (1 - percent/100)
    bg = "#2A2D35" if is_dark else "#E0E5EC"
    text_color = "#E0E5EC" if is_dark else "#2D3436"
    return f"""<div style='display: flex; justify-content: flex-end;'><div style='position: relative; width: 110px; height: 110px; border-radius: 50%; background: {bg}; display: flex; align-items: center; justify-content: center;'><svg width='110' height='110'><circle stroke='#1E2128' stroke-width='8' fill='transparent' r='45' cx='55' cy='55'/><circle stroke='#FF0000' stroke-width='8' stroke-dasharray='{circum}' stroke-dashoffset='{offset}' stroke-linecap='round' fill='transparent' r='45' cx='55' cy='55' style='transition: all 0.8s; transform: rotate(-90deg); transform-origin: center;'/></svg><div style='position: absolute; font-size: 20px; font-weight: 900; color: {text_color};'>{percent}%</div></div></div>"""

def apply_styles(is_dark):
    bg_color = "#1E2128" if is_dark else "#E0E5EC"
    text_color = "#E0E5EC" if is_dark else "#2D3436"
    st.markdown(f"""<style>
        .stApp {{ background-color: {bg_color} !important; color: {text_color} !important; }}
        .neu-card {{ background: {bg_color}; border-radius: 20px; box-shadow: 9px 9px 16px rgba(0,0,0,0.2), -9px -9px 16px rgba(255,255,255,0.05); padding: 25px; margin-bottom: 20px; }}
        button[kind="primary"] {{ background-color: #FF2A2A !important; color: white !important; }}
        .mc-question {{ font-weight: 700; color: #FF0000 !important; border-left: 4px solid #FF0000; padding-left: 10px; }}
        .debug-terminal {{ background: #0D0F14 !important; color: #00FF88 !important; padding: 15px; border-radius: 10px; height: 300px; overflow-y: scroll; }}
    </style>""", unsafe_allow_html=True)

# --- 4. Main App ---

def fetch_draft_list():
    try:
        r = requests.post(SHEET_SCRIPT_URL, json={"action": "get_raw_input_list"}, timeout=15)
        if r.status_code == 200:
            data = r.json()
            if data.get("status") == "success": return data.get("data", [])
    except Exception as e: log_debug(f"❌ 無法獲取草稿: {str(e)}", "error")
    return []

def load_draft_into_session(project_id):
    try:
        r = requests.post(SHEET_SCRIPT_URL, json={"action": "get_raw_input_details", "project_id": project_id}, timeout=15)
        if r.status_code == 200:
            data = r.json()
            if data.get("status") == "success":
                d = data["data"]
                st.session_state.client_name = d.get("client_name", "")
                st.session_state.project_name = d.get("project_name", "")
                st.session_state.venue = d.get("venue", "")
                st.session_state.youtube = d.get("youtube", "")
                st.session_state.open_question_ans = d.get("open_question", "")
                st.session_state.loaded_image_urls = d.get("image_urls", [])
                st.session_state.draft_project_id = project_id
                return True
    except Exception as e: log_debug(f"❌ 載入失敗: {str(e)}", "error")
    return False

def save_draft_to_sheet():
    try:
        processed_imgs = []
        if st.session_state.project_photos:
            for f in st.session_state.project_photos:
                if hasattr(f, "seek"): f.seek(0)
                img = Image.open(f).convert("RGB")
                img.thumbnail((800, 800))
                buf = io.BytesIO()
                img.save(buf, format="JPEG", quality=70)
                processed_imgs.append(base64.b64encode(buf.getvalue()).decode())

        draft_id = st.session_state.get("draft_project_id", "") or f"DRAFT_{int(time.time())}"
        payload = {
            "action": "save_raw_input", "project_id": draft_id,
            "client_name": st.session_state.client_name, "project_name": st.session_state.project_name,
            "venue": st.session_state.venue, "images": processed_imgs,
        }
        r = requests.post(SHEET_SCRIPT_URL, json=payload, timeout=60)
        return r.status_code == 200
    except Exception as e: return False

def main():
    st.set_page_config(page_title="Firebean Brain Collector", layout="wide")
    init_session_state()
    is_dark = get_is_dark_mode()
    apply_styles(is_dark)

    c1, c2 = st.columns([1, 1])
    with c1: 
        if st.button("🏠 HOME"):
            if st.session_state.get("sync_success", False): reset_for_new_case()
            else: st.session_state.active_tab = "Project Collector"
            st.rerun()
    with c2: progress_placeholder = st.empty()

    nav_cols = st.columns(4)
    tabs = ["Project Collector", "Review & Multi-Sync", "Load Project"]
    for i, tab in enumerate(tabs):
        if nav_cols[i].button(tab, use_container_width=True, type="primary" if st.session_state.active_tab == tab else "secondary"):
            st.session_state.active_tab = tab
            st.rerun()
    if nav_cols[3].button("老細一鍵填充", use_container_width=True):
        fill_dummy_data()
        st.rerun()

    if st.session_state.active_tab == "Load Project":
        st.markdown('<div class="neu-card">### 📂 載入草稿</div>', unsafe_allow_html=True)
        if st.button("🔄 獲取列表"):
            st.session_state["_draft_list"] = fetch_draft_list()
        drafts = st.session_state.get("_draft_list", [])
        if drafts:
            selected = st.selectbox("選擇項目", [d['project_id'] for d in drafts])
            if st.button("⬇️ 載入"):
                if load_draft_into_session(selected):
                    st.session_state.active_tab = "Project Collector"
                    st.rerun()

    elif st.session_state.active_tab == "Project Collector":
        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            ub = st.file_uploader("Black Logo", type=['png'])
            if ub: st.session_state.logo_black = base64.b64encode(ub.read()).decode()
        with col2:
            uw = st.file_uploader("White Logo", type=['png'])
            if uw: st.session_state.logo_white = base64.b64encode(uw.read()).decode()

        b1, b2, b3 = st.columns(3)
        st.session_state.client_name = b1.text_input("Client", st.session_state.client_name)
        st.session_state.project_name = b2.text_input("Project", st.session_state.project_name)
        st.session_state.venue = b3.text_input("Venue", st.session_state.venue)

        st.session_state.project_photos = st.file_uploader("Upload 4-8 Photos", accept_multiple_files=True) or st.session_state.project_photos

        filled = sum([bool(st.session_state.client_name), bool(st.session_state.project_name), len(st.session_state.project_photos) >= 4])
        progress_placeholder.markdown(get_circle_progress_html(int((filled/3)*100), is_dark), unsafe_allow_html=True)

        if st.button("💾 儲存草稿"):
            if save_draft_to_sheet(): st.success("已儲存")

        if filled >= 3:
            if st.button("前往 Review & Multi-Sync 👉", type="primary", use_container_width=True):
                st.session_state.active_tab = "Review & Multi-Sync"
                st.rerun()

    elif st.session_state.active_tab == "Review & Multi-Sync":
        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        if st.button("生成文案"):
            with st.spinner("AI 構思中..."):
                prompt = f"分析專案: {st.session_state.project_name}. Client: {st.session_state.client_name}."
                res = call_gemini_sdk(prompt, is_json=True)
                if res: st.session_state.ai_content = json.loads(res)
        
        if st.session_state.ai_content:
            st.json(st.session_state.ai_content)
            if st.button("Confirm & Sync (Sheet + Slide)", type="primary", use_container_width=True):
                with st.spinner("🔄 同步中 (Slide Fix Enabled)..."):
                    pid, sdate = generate_system_metadata()
                    processed_imgs = []
                    for f in st.session_state.project_photos:
                        if hasattr(f, "seek"): f.seek(0)
                        img = Image.open(f).convert("RGB")
                        img.thumbnail((1600, 1600))
                        buf = io.BytesIO()
                        img.save(buf, format="JPEG", quality=85)
                        processed_imgs.append(base64.b64encode(buf.getvalue()).decode())

                    payload = {
                        "action": "sync_project", "project_id": pid, "sort_date": sdate,
                        "client_name": st.session_state.client_name, "project_name": st.session_state.project_name,
                        "venue": st.session_state.venue, "images": processed_imgs,
                        "logo_white": st.session_state.logo_white, "logo_black": st.session_state.logo_black,
                        "faq_en": safe_flatten_faq(st.session_state.faq_en_edit),
                    }
                    
                    # 1. Sync to Sheet (Master DB Script)
                    r1 = requests.post(SHEET_SCRIPT_URL, json=payload, timeout=60)
                    # 2. Sync to Slides (Case Study Script with Fix)
                    payload["action"] = "create_slide"
                    payload["photos"] = processed_imgs # Matching the key in script
                    payload["logo_white_base64"] = st.session_state.logo_white
                    r2 = requests.post(SLIDE_SCRIPT_URL, json=payload, timeout=60)

                    if r1.status_code == 200 and r2.status_code == 200:
                        st.balloons()
                        st.success(f"✅ 同步成功! ID: {pid}")
                        st.session_state.sync_success = True

    with st.expander("🛠️ Debug Terminal", expanded=False):
        logs = "".join([f"<div>[{l['time']}] {l['msg']}</div>" for l in reversed(st.session_state.get("debug_logs", []))])
        st.markdown(f"<div class='debug-terminal'>{logs}</div>", unsafe_allow_html=True)

if __name__ == "__main__": main()
