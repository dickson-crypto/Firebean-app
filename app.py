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

# --- 1. 核心配置 ---
SHEET_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbzaQu2KpJ06I0yWL4dEwk0naB1FOlHkt7Ta340xH84IDwQI7jQNUI3eSmxrwKyQHNj5/exec"
SLIDE_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbyZvtm8M8a5sLYF3vz9kLyAdimzzwpSlnTkzIeQ3DJxkklNYNlwSoJc5j5CkorM6w5V/exec"
STABLE_MODEL_ID = "gemini-2.0-flash"

WHO_WE_HELP_OPTIONS = ["GOVERNMENT & PUBLIC SECTOR", "LIFESTYLE & CONSUMER", "F&B & HOSPITALITY", "MALLS & VENUES"]
WHAT_WE_DO_OPTIONS = ["ROVING EXHIBITIONS", "SOCIAL & CONTENT", "INTERACTIVE & TECH", "PR & MEDIA", "EVENTS & CEREMONIES"]
SOW_OPTIONS = ["Event Planning", "Event Coordination", "Event Production", "Theme Design", "Concept Development", "Social Media Management", "KOL / MI Line up", "Artist Endorsement", "Media Pitching", "PR Consulting", "Souvenir Sourcing"]

CURRENT_YEAR = datetime.now().year
YEAR_OPTIONS = [str(y) for y in range(CURRENT_YEAR, 2011, -1)]
MONTH_OPTIONS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]

# --- 🛡️ FAQ 安全清洗函數 ---
def safe_flatten_faq(faq_input):
    """將文字框內容壓縮成沒有換行符號的單行字串 (Flat String)"""
    if not faq_input: return "[]"
    try:
        # 如果是字串，試著解析 JSON
        if isinstance(faq_input, str):
            faq_input = faq_input.strip()
            if not faq_input: return "[]"
            parsed = json.loads(faq_input)
            return json.dumps(parsed, ensure_ascii=False)
        return json.dumps(faq_input, ensure_ascii=False)
    except:
        # 解析失敗則暴力移除換行與單引號
        return str(faq_input).replace("\n", " ").replace("\r", "").replace("'", "\\'").strip()

# --- 2. 系統邏輯 ---
def log_debug(msg, type="info"):
    if "debug_logs" not in st.session_state: st.session_state.debug_logs = []
    timestamp = datetime.now().strftime("%H:%M:%S")
    st.session_state.debug_logs.append({"time": timestamp, "msg": msg, "type": type})

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
You are a Lead PR Strategist. Task: Transform diagnostic data into professional PR strategy JSON.
Required keys: challenge_summary, solution_summary, 1_google_slide, 2_facebook_post, 3_threads_post, 4_instagram_post, 5_linkedin_post, 6_website, 7_faq.

**CRITICAL FOR 6_website**: Must be a nested object with "angle_chosen", "en", "tc", "jp". Use <h1>, <h3>, <p> only.
**CRITICAL FOR 7_faq**: Must be a nested object with "en", "tc", "jp". Each must be a JSON array: [{"Q1":"...","A1":"..."}].
"""

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
            response = model.generate_content(contents, generation_config={"response_mime_type": "application/json" if is_json else "text/plain", "temperature": 0.2})
            if response and response.text:
                text = response.text.strip()
                if not is_json: return text
                match = re.search(r'(\{.*\})|(\[.*\])', text, re.DOTALL)
                json_str = match.group(0) if match else text
                json.loads(json_str)
                return json_str
        except Exception as e:
            log_debug(f"API Error: {str(e)}", "error")
            time.sleep(1)
    return None

def init_session_state():
    fields = {
        "active_tab": "Project Collector", "client_name": "", "project_name": "", "venue": "", "youtube": "",
        "event_year": str(CURRENT_YEAR), "event_month": "FEB", "category": WHO_WE_HELP_OPTIONS[0], "what_we_do": [], "scope": [],
        "project_photos": [], "ai_content": {}, "logo_white": "", "logo_black": "", "debug_logs": [], "mc_questions": [], 
        "open_question_ans": "", "challenge": "", "solution": "", "hero_photo_index": 0, "sync_success": False,
        "faq_en_edit": "", "faq_tc_edit": "", "faq_jp_edit": ""
    }
    for k, v in fields.items():
        if k not in st.session_state: st.session_state[k] = v

def reset_for_new_case():
    for k in list(st.session_state.keys()):
        if k != "debug_logs": del st.session_state[k]
    init_session_state()
    st.rerun()

def fill_dummy_data():
    st.session_state.client_name = "Firebean HQ"
    st.session_state.project_name = f"{CURRENT_YEAR} 旗艦同步測試" 
    st.session_state.venue = "香港會議展覽中心"
    st.session_state.open_question_ans = "轉化 15 個指標為跨平台策略。"
    colors = ["#FF5733", "#33FF57", "#3357FF", "#F333FF"]
    st.session_state.project_photos = [create_dummy_image(c, f"P{i+1}") for i, c in enumerate(colors)]
    st.session_state.mc_questions = [{"id": i+1, "question": f"指標 {i+1}？", "options": ["優化", "維持"]} for i in range(15)]
    for i in range(1, 16): st.session_state[f"ans_{i}"] = ["優化"]
    log_debug("🚀 填充完成", "success")

def create_dummy_image(color, label):
    img = Image.new('RGB', (800, 600), color=color)
    d = ImageDraw.Draw(img)
    d.text((40, 40), label, fill=(255, 255, 255))
    buf = io.BytesIO(); img.save(buf, format="JPEG"); buf.seek(0)
    return buf

# --- 3. UI 介面 ---
def main():
    st.set_page_config(page_title="Firebean Collector", layout="wide")
    init_session_state()
    
    st.markdown("""<style>.neu-card { background: #1E2128; border-radius: 20px; box-shadow: 9px 9px 16px #14161C; padding: 25px; margin-bottom: 20px; color: white; }</style>""", unsafe_allow_html=True)

    nav = st.columns(3)
    if nav[0].button("Project Collector", use_container_width=True): st.session_state.active_tab = "Project Collector"; st.rerun()
    if nav[1].button("Review & Sync", use_container_width=True): st.session_state.active_tab = "Review & Multi-Sync"; st.rerun()
    if nav[2].button("一鍵填充", use_container_width=True): fill_dummy_data(); st.rerun()

    if st.session_state.active_tab == "Project Collector":
        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        st.session_state.client_name = c1.text_input("Client", st.session_state.client_name)
        st.session_state.project_name = c2.text_input("Project", st.session_state.project_name)
        st.session_state.venue = c3.text_input("Venue", st.session_state.venue)
        
        up = st.file_uploader("Upload Photos", accept_multiple_files=True)
        if up: st.session_state.project_photos = up
        
        if st.button("生成診斷題目"):
            res = call_gemini_sdk("Generate 15 PR MC questions in Traditional Chinese JSON array.", is_json=True)
            if res: st.session_state.mc_questions = json.loads(res); st.rerun()
        
        if st.session_state.mc_questions:
            for q in st.session_state.mc_questions:
                st.session_state[f"ans_{q['id']}"] = st.multiselect(q['question'], q['options'], key=f"q_{q['id']}")
            st.session_state.open_question_ans = st.text_area("核心概念", st.session_state.open_question_ans)
        st.markdown('</div>', unsafe_allow_html=True)

    elif st.session_state.active_tab == "Review & Multi-Sync":
        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        if st.button("生成六大平台文案"):
            with st.spinner("AI 撰寫中..."):
                prompt = f"分析專案: {st.session_state.project_name}。生成 JSON。包含 6_website 與 7_faq (Array of Objects)。"
                res = call_gemini_sdk(prompt, is_json=True)
                if res:
                    data = json.loads(res)
                    st.session_state.ai_content = data
                    faq = data.get("7_faq", {})
                    # 預填文字框
                    st.session_state.faq_en_edit = json.dumps(faq.get("en", []), ensure_ascii=False, indent=2)
                    st.session_state.faq_tc_edit = json.dumps(faq.get("tc", []), ensure_ascii=False, indent=2)
                    st.session_state.faq_jp_edit = json.dumps(faq.get("jp", []), ensure_ascii=False, indent=2)
                    st.rerun()

        if st.session_state.ai_content:
            st.json(st.session_state.ai_content)
            st.markdown("### 💬 編輯 FAQ")
            st.session_state.faq_en_edit = st.text_area("FAQ EN", value=st.session_state.faq_en_edit, height=150)
            st.session_state.faq_tc_edit = st.text_area("FAQ TC", value=st.session_state.faq_tc_edit, height=150)
            st.session_state.faq_jp_edit = st.text_area("FAQ JP", value=st.session_state.faq_jp_edit, height=150)

            if st.button("Confirm & Sync", type="primary", use_container_width=True):
                with st.spinner("同步中..."):
                    try:
                        pid, sdate = generate_system_metadata()
                        processed_imgs = []
                        for f in st.session_state.project_photos:
                            if hasattr(f, "seek"): f.seek(0)
                            img = ImageOps.exif_transpose(Image.open(f).convert("RGB"))
                            img.thumbnail((1200, 1200))
                            buf = io.BytesIO(); img.save(buf, format="JPEG", quality=85)
                            processed_imgs.append(base64.b64encode(buf.getvalue()).decode())

                        payload = {
                            "action": "sync_project", "project_id": pid, "sort_date": sdate,
                            "client_name": st.session_state.client_name, "project_name": st.session_state.project_name,
                            "venue": st.session_state.venue, "date": f"{st.session_state.event_year} {st.session_state.event_month}",
                            "challenge": st.session_state.ai_content.get("challenge_summary", ""),
                            "solution": st.session_state.ai_content.get("solution_summary", ""),
                            "images": processed_imgs, "ai_content": st.session_state.ai_content,
                            # 🚀 這裡就是核心修正：使用安全扁平化字串送出
                            "faq_en": safe_flatten_faq(st.session_state.faq_en_edit),
                            "faq_tc": safe_flatten_faq(st.session_state.faq_tc_edit),
                            "faq_jp": safe_flatten_faq(st.session_state.faq_jp_edit)
                        }
                        
                        # Debug Print 到日誌
                        print(f"DEBUG_SEND_EN: {payload['faq_en']}")
                        
                        r1 = requests.post(SHEET_SCRIPT_URL, json=payload, timeout=60)
                        
                        slide_payload = payload.copy()
                        slide_payload["action"] = "create_slide"
                        requests.post(SLIDE_SCRIPT_URL, json=slide_payload, timeout=60)

                        st.balloons(); st.success(f"成功同步！編號: {pid}")
                        st.session_state.sync_success = True
                    except Exception as e: st.error(f"失敗: {e}")
        st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__": main()
