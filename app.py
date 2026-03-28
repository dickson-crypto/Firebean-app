import streamlit as st
from google import genai
from google.genai import types
import io
import base64
import time
import json
import requests
import re
from PIL import Image, ImageDraw, ImageOps
from datetime import datetime

# 🚀 FIX: HEIC support for iPhone uploads
try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
except ImportError:
    pass

# --- 1. 核心配置 ---
SHEET_SCRIPT_URL   = "https://script.google.com/macros/s/AKfycbxy6JwJpmclJOBerKJO4EJ50oKyL86Ux1Qci2oHx1RQiw8ruL_Um6qVYsWydyEsLawQ/exec"
SLIDE_DB_URL       = "https://script.google.com/macros/s/AKfycbx_7Xf8_HERQel93WJB2F_KjFOWHtCXzfvEkP9B_p7Kh4ImRAWRgWSXtLklvdbYsqbI/exec"
CASE_STUDY_URL     = "https://script.google.com/macros/s/AKfycbxKP-8Xrvy6hblPqTmtXn76rO3DFOeU6jYQtLw5QDfDP1-adNDk02bhoKihfvp_Xsvy/exec"

# ✅ gemini-2.5-flash — current stable model for new API keys (2026)
STABLE_MODEL_ID = "gemini-2.5-flash"

WHO_WE_HELP_OPTIONS = ["GOVERNMENT & PUBLIC SECTOR", "LIFESTYLE & CONSUMER", "F&B & HOSPITALITY", "MALLS & VENUES"]
WHAT_WE_DO_OPTIONS  = ["ROVING EXHIBITIONS", "SOCIAL & CONTENT", "INTERACTIVE & TECH", "PR & MEDIA", "EVENTS & CEREMONIES"]
SOW_OPTIONS = ["Event Planning", "Event Coordination", "Event Production", "Theme Design", "Concept Development",
               "Social Media Management", "KOL / MI Line up", "Artist Endorsement", "Media Pitching", "PR Consulting", "Souvenir Sourcing"]

CURRENT_YEAR  = datetime.now().year
YEAR_OPTIONS  = [str(y) for y in range(CURRENT_YEAR, 2011, -1)]
MONTH_OPTIONS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]

# --- 🛡️ FAQ 扁平化清洗函數 ---
def safe_flatten_faq(faq_input):
    if not faq_input: return "[]"
    if isinstance(faq_input, (list, dict)): return json.dumps(faq_input, ensure_ascii=False)
    if isinstance(faq_input, str):
        try: return json.dumps(json.loads(faq_input.strip()), ensure_ascii=False)
        except: return faq_input.replace("\\n", " ").replace("\\r", "").strip()
    return "[]"

# --- 系統自動生成邏輯 ---
def generate_system_metadata():
    year  = st.session_state.get("event_year", str(CURRENT_YEAR))
    month = st.session_state.get("event_month", "JAN")
    m_num = {m: str(i+1).zfill(2) for i, m in enumerate(MONTH_OPTIONS)}.get(month, "01")
    sort_date = f"{year}-{m_num}-01"
    try:
        count_res  = requests.get(SHEET_SCRIPT_URL + "?action=get_row_count", timeout=5)
        next_index = int(count_res.text.strip()) + 1 if count_res.status_code == 200 else 100
    except:
        next_index = 999
    return f"FB{year}{str(next_index).zfill(3)}", sort_date

FIREBEAN_SYSTEM_PROMPT = "You are a Lead PR Strategist at Firebean Limited, Hong Kong. Transform diagnostic data into a professional PR strategy JSON. Written in past tense retrospective mode. Output valid JSON only."

# --- 2. 核心邏輯 ---
def log_debug(msg, type="info"):
    if "debug_logs" not in st.session_state: st.session_state.debug_logs = []
    st.session_state.debug_logs.append({"time": datetime.now().strftime("%H:%M:%S"), "msg": msg, "type": type})

def open_image_safe(f):
    """Open a PIL Image from either an UploadedFile or a BytesIO (dummy)."""
    if hasattr(f, "seek"):
        f.seek(0)
    return Image.open(f)

def call_gemini_sdk(prompt, image_files=None, is_json=False, system_prompt=None):
    api_key = st.secrets.get("GEMINI_API_KEY", "")
    if not api_key:
        log_debug("GEMINI_API_KEY not found in secrets.", "error")
        return None
    try:
        client = genai.Client(api_key=api_key)
        contents = []
        # Add images first (before text, as recommended)
        if image_files:
            for f in image_files:
                try:
                    img = open_image_safe(f)
                    img.thumbnail((800, 800))
                    # Convert PIL image to inline bytes part
                    buf = io.BytesIO()
                    img.save(buf, format="JPEG")
                    img_bytes = buf.getvalue()
                    contents.append(types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg"))
                except Exception as img_err:
                    log_debug(f"Image load skipped: {img_err}", "warning")
        # Add text prompt
        contents.append(prompt)

        cfg = types.GenerateContentConfig(
            system_instruction=system_prompt if system_prompt else None,
            temperature=0.7,
        )
        res = client.models.generate_content(
            model=STABLE_MODEL_ID,
            contents=contents,
            config=cfg,
        )
        raw = res.text
        if is_json:
            # Strip markdown code fences if present
            raw = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.IGNORECASE)
            raw = re.sub(r"\s*```$", "", raw.strip())
            match = re.search(r'(\{.*\})|(\[.*\])', raw, re.DOTALL)
            return match.group(0) if match else raw
        return raw
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
        "faq_en_edit": "", "faq_tc_edit": "", "faq_jp_edit": ""
    }
    for k, v in fields.items():
        if k not in st.session_state: st.session_state[k] = v

def reset_for_new_case():
    keys_to_clear = list(st.session_state.keys())
    for k in keys_to_clear:
        del st.session_state[k]
    init_session_state()
    for w in WHAT_WE_DO_OPTIONS: st.session_state[f"w_{w}"] = False
    for s in SOW_OPTIONS:         st.session_state[f"s_{s}"] = False
    st.session_state.active_tab = "Project Collector"

def create_dummy_image(color, label):
    img = Image.new('RGB', (800, 600), color=color)
    ImageDraw.Draw(img).text((40, 40), label, fill=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    buf.seek(0)
    return buf

def fill_dummy_data():
    st.session_state.client_name  = "Firebean HQ"
    st.session_state.project_name = f"{CURRENT_YEAR} 旗艦同步測試"
    st.session_state.venue        = "香港會議展覽中心"
    st.session_state.category     = "LIFESTYLE & CONSUMER"

    st.session_state.what_we_do = ["INTERACTIVE & TECH", "PR & MEDIA"]
    for w in WHAT_WE_DO_OPTIONS: st.session_state[f"w_{w}"] = (w in st.session_state.what_we_do)
    st.session_state.scope = ["Theme Design", "Event Production", "Concept Development"]
    for s in SOW_OPTIONS: st.session_state[f"s_{s}"] = (s in st.session_state.scope)

    st.session_state.open_question_ans = "將 15 個通用診斷問題轉化為一套連貫且可操作的跨平台策略。"

    colors = ["#FF5733", "#33FF57", "#3357FF", "#F333FF", "#33FFF3", "#F3FF33", "#999999", "#222222"]
    st.session_state.project_photos = [create_dummy_image(c, f"P{i+1}") for i, c in enumerate(colors)]
    dummy_logo = base64.b64encode(create_dummy_image("#000000", "LOGO").getvalue()).decode()
    st.session_state.logo_black = dummy_logo
    st.session_state.logo_white = dummy_logo

    st.session_state.mc_questions = [{"id": i+1, "question": f"診斷指標 {i+1}", "options": ["戰略優化"]} for i in range(15)]
    for i in range(1, 16): st.session_state[f"ans_{i}"] = ["戰略優化"]
    log_debug("🚀 老細一鍵填充成功 (100% Status).", "success")

# --- 3. UI 元件 ---
def get_is_dark_mode():
    hk_hour = datetime.now().hour
    return hk_hour >= 20 or hk_hour < 8

def get_circle_progress_html(percent, is_dark):
    circum = 439.8
    offset = circum * (1 - percent / 100)
    bg, sh_d, sh_l, txt, trk = (
        ("#2A2D35", "#1a1d23", "#3a3f4d", "#E0E5EC", "#1E2128") if is_dark
        else ("#E0E5EC", "#bec3c9", "#ffffff", "#2D3436", "#d1d9e6")
    )
    return (
        f"<div style='display:flex;justify-content:flex-end;'>"
        f"<div style='position:relative;width:110px;height:110px;border-radius:50%;background:{bg};"
        f"box-shadow:9px 9px 16px {sh_d},-9px -9px 16px {sh_l};display:flex;align-items:center;justify-content:center;'>"
        f"<svg width='110' height='110'>"
        f"<circle stroke='{trk}' stroke-width='8' fill='transparent' r='45' cx='55' cy='55'/>"
        f"<circle stroke='#FF0000' stroke-width='8' stroke-dasharray='{circum}' stroke-dashoffset='{offset}' "
        f"stroke-linecap='round' fill='transparent' r='45' cx='55' cy='55' "
        f"style='transition:all 0.8s;transform:rotate(-90deg);transform-origin:center;'/>"
        f"</svg>"
        f"<div style='position:absolute;font-size:20px;font-weight:900;color:{txt};'>{percent}%</div>"
        f"</div></div>"
    )

def apply_styles(is_dark):
    bg, card, sh_d, sh_l, txt, in_bg = (
        ("#1E2128", "#1E2128", "#14161C", "#282C38", "#E0E5EC", "#252830") if is_dark
        else ("#E0E5EC", "#E0E5EC", "#bec3c9", "#ffffff", "#2D3436", "#e8ecf2")
    )
    st.markdown(f"""<style>
        .stApp {{ background-color: {bg} !important; color: {txt} !important; font-family: 'Inter', sans-serif; }}
        .neu-card {{ background: {card}; border-radius: 20px; box-shadow: 9px 9px 16px {sh_d}, -9px -9px 16px {sh_l}; padding: 25px; margin-bottom: 20px; }}
        div[data-testid="stElementContainer"]:has(#logo-anchor) + div button {{
            background-image: url('https://raw.githubusercontent.com/dickson-crypto/Firebean-app/main/Firebeanlogo2026.png') !important;
            background-size: contain !important; background-repeat: no-repeat !important;
            min-height: 180px !important; width: 540px !important;
            background-color: transparent !important; border: none !important; box-shadow: none !important;
        }}
        .mc-question {{ font-weight: 700; color: #FF0000 !important; border-left: 4px solid #FF0000; padding-left: 10px; margin-top: 15px; }}
        .checkbox-group {{ padding-left: 20px; margin-bottom: 10px; }}
        button[kind="primary"] {{ background-color: #FF2A2A !important; color: white !important; border-radius: 12px !important; box-shadow: 0px 4px 15px rgba(255,0,0,0.35) !important; }}
        .debug-terminal {{ background: #111; color: #0f0; font-family: monospace; font-size: 12px; padding: 10px; border-radius: 8px; max-height: 300px; overflow-y: auto; }}
    </style>""", unsafe_allow_html=True)

# --- 4. Review tab helper: build rich AI prompt from session state ---
def build_content_prompt():
    mc_summary = []
    for q in st.session_state.get("mc_questions", []):
        ans = st.session_state.get(f"ans_{q['id']}", [])
        mc_summary.append(f"Q{q['id']}. {q['question']} → {', '.join(ans)}")
    return f"""
以下是 Firebean 的項目診斷資料，請生成六大平台（Website、Instagram、LinkedIn、Facebook、EDM、Press Release）的對接文案 JSON。

客戶: {st.session_state.get('client_name','')}
項目: {st.session_state.get('project_name','')}
場地: {st.session_state.get('venue','')}
分類: {st.session_state.get('category','')}
服務範圍: {', '.join(st.session_state.get('what_we_do',[]))}
工作範圍: {', '.join(st.session_state.get('scope',[]))}
核心概念: {st.session_state.get('open_question_ans','')}

診斷問卷:
{''.join(mc_summary)}

請輸出嚴格 JSON，格式:
{{
  "website": {{"headline":"","body":"","cta":""}},
  "instagram": {{"caption":"","hashtags":""}},
  "linkedin": {{"headline":"","body":""}},
  "facebook": {{"caption":""}},
  "edm": {{"subject":"","preview":"","body":""}},
  "press_release": {{"headline":"","lead":"","body":""}}
}}
""".strip()

# --- 5. Main App ---
def main():
    st.set_page_config(page_title="Firebean Brain Collector", layout="wide")
    init_session_state()
    is_dark = get_is_dark_mode()
    apply_styles(is_dark)

    # ── Header row ──
    c1, c2 = st.columns([1, 1])
    with c1:
        st.markdown('<span id="logo-anchor"></span>', unsafe_allow_html=True)
        if st.button("", key="logo_btn"):
            reset_for_new_case()
            st.rerun()
    with c2:
        mc_ans   = sum([1 for i in range(1, 16) if st.session_state.get(f"ans_{i}")])
        logo_ok  = bool(st.session_state.logo_black) and bool(st.session_state.logo_white)
        criteria = [
            logo_ok,
            bool(st.session_state.client_name),
            bool(st.session_state.project_name),
            bool(st.session_state.venue),
            bool(st.session_state.event_year),
            bool(st.session_state.event_month),
            bool(st.session_state.category),
            len(st.session_state.what_we_do) > 0,
            len(st.session_state.scope) > 0,
            len(st.session_state.project_photos) >= 4,
            mc_ans == 15,
            bool(st.session_state.open_question_ans.strip()),
        ]
        percent = int((sum(criteria) / 12) * 100)
        st.markdown(get_circle_progress_html(percent, is_dark), unsafe_allow_html=True)

    # ── Navigation ──
    nav_cols = st.columns(4)
    tabs = ["Project Collector", "Review & Multi-Sync", "Load Project", "老細一鍵填充 (深度內容測試)"]
    for i, t in enumerate(tabs[:3]):
        btn_type = "primary" if st.session_state.active_tab == t else "secondary"
        if nav_cols[i].button(t, use_container_width=True, type=btn_type):
            st.session_state.active_tab = t
            st.rerun()
    if nav_cols[3].button(tabs[3], use_container_width=True):
        fill_dummy_data()
        st.rerun()

    st.markdown("---")

    # ════════════════════════════════════════════
    # TAB 1: Project Collector
    # ════════════════════════════════════════════
    if st.session_state.active_tab == "Project Collector":
        with st.container():
            st.markdown('<div class="neu-card">', unsafe_allow_html=True)

            col1, col2 = st.columns(2)
            with col1:
                ub = st.file_uploader("Black Logo (PNG)", type=["png"], key="l_b_up")
                if ub:
                    st.session_state.logo_black = base64.b64encode(ub.read()).decode()
                if st.session_state.logo_black:
                    st.image(base64.b64decode(st.session_state.logo_black), width=150)
            with col2:
                uw = st.file_uploader("White Logo (PNG)", type=["png"], key="l_w_up")
                if uw:
                    st.session_state.logo_white = base64.b64encode(uw.read()).decode()
                if st.session_state.logo_white:
                    st.markdown(
                        f'<div style="background:#333;padding:5px;display:inline-block;">'
                        f'<img src="data:image/png;base64,{st.session_state.logo_white}" width="150"></div>',
                        unsafe_allow_html=True,
                    )

            b1, b2, b3 = st.columns(3)
            st.session_state.client_name  = b1.text_input("Client",  st.session_state.client_name)
            st.session_state.project_name = b2.text_input("Project", st.session_state.project_name)
            st.session_state.venue        = b3.text_input("Venue",   st.session_state.venue)

            d1, d2, d3 = st.columns(3)
            with d1:
                st.session_state.event_year = st.selectbox(
                    "Year", YEAR_OPTIONS,
                    index=YEAR_OPTIONS.index(st.session_state.event_year) if st.session_state.event_year in YEAR_OPTIONS else 0
                )
            with d2:
                st.session_state.event_month = st.selectbox(
                    "Month", MONTH_OPTIONS,
                    index=MONTH_OPTIONS.index(st.session_state.event_month) if st.session_state.event_month in MONTH_OPTIONS else 1
                )
            with d3:
                st.session_state.youtube = st.text_input("YouTube URL (optional)", st.session_state.youtube)

            ca, cb, cc = st.columns(3)
            with ca:
                st.markdown("##### Category")
                st.session_state.category = st.radio(
                    "Category", WHO_WE_HELP_OPTIONS,
                    index=WHO_WE_HELP_OPTIONS.index(st.session_state.category),
                    label_visibility="collapsed",
                )
            with cb:
                st.markdown("##### What we do")
                st.session_state.what_we_do = [
                    o for o in WHAT_WE_DO_OPTIONS
                    if st.checkbox(o, key=f"w_{o}", value=st.session_state.get(f"w_{o}", False))
                ]
            with cc:
                st.markdown("##### Scope of work")
                st.session_state.scope = [
                    o for o in SOW_OPTIONS
                    if st.checkbox(o, key=f"s_{o}", value=st.session_state.get(f"s_{o}", False))
                ]

            st.markdown("</div>", unsafe_allow_html=True)

        cl, cr = st.columns([1.2, 1])
        with cl:
            st.markdown('<div class="neu-card">', unsafe_allow_html=True)
            if st.button("生成 15 題繁中診斷題目"):
                with st.spinner("AI Strategizing..."):
                    prompt = (
                        f"你是 Firebean 的 PR 策略師。根據以下項目資訊，生成 15 題專業 PR 診斷問題的 JSON 陣列。\n"
                        f"客戶: {st.session_state.client_name}, 項目: {st.session_state.project_name}, 場地: {st.session_state.venue}\n"
                        f"每題格式: {{\"id\": 1, \"question\": \"...\", \"options\": [\"A選項\", \"B選項\", \"C選項\"]}}\n"
                        f"輸出嚴格 JSON 陣列，共 15 題，選項每題 3-4 個，繁體中文。"
                    )
                    res = call_gemini_sdk(
                        prompt,
                        image_files=st.session_state.project_photos if st.session_state.project_photos else None,
                        is_json=True,
                        system_prompt=FIREBEAN_SYSTEM_PROMPT,
                    )
                    if res:
                        try:
                            parsed = json.loads(res)
                            st.session_state.mc_questions = parsed if isinstance(parsed, list) else parsed.get("questions", [])
                            log_debug(f"✅ 生成 {len(st.session_state.mc_questions)} 題成功", "success")
                        except json.JSONDecodeError as je:
                            log_debug(f"JSON parse error: {je} | raw: {res[:200]}", "error")
                            st.error("AI 返回格式有誤，請重試。")
                    st.rerun()

            if st.session_state.mc_questions:
                for q in st.session_state.mc_questions:
                    st.markdown(f"<div class='mc-question'>Q{q['id']}. {q['question']}</div>", unsafe_allow_html=True)
                    ans_key = f"ans_{q['id']}"
                    current = st.session_state.get(ans_key, [])
                    new_ans = []
                    for opt in q.get("options", []):
                        if st.checkbox(opt, value=(opt in current), key=f"chk_{q['id']}_{opt}"):
                            new_ans.append(opt)
                    st.session_state[ans_key] = new_ans

            st.session_state.open_question_ans = st.text_area("最核心的概念？", st.session_state.open_question_ans)
            st.markdown("</div>", unsafe_allow_html=True)

        with cr:
            st.markdown('<div class="neu-card">', unsafe_allow_html=True)
            f_up = st.file_uploader("Upload 4-8 Photos", accept_multiple_files=True, key="photo_up")
            if f_up:
                st.session_state.project_photos = f_up
            if st.session_state.project_photos:
                n = len(st.session_state.project_photos)
                st.session_state.hero_photo_index = st.radio(
                    "Select Hero Banner:", range(n), horizontal=True,
                    format_func=lambda i: f"#{i+1}",
                )
                g_cols = st.columns(4)
                for i, f in enumerate(st.session_state.project_photos):
                    with g_cols[i % 4]:
                        try:
                            img = open_image_safe(f)
                            st.image(img, use_container_width=True)
                        except Exception as e:
                            st.caption(f"Photo {i+1} preview error")
            st.markdown("</div>", unsafe_allow_html=True)

        if percent >= 100:
            st.markdown("---")
            st.success("🎉 完美！進度達 100%！")
            if st.button("準備就緒，前往 Review & Multi-Sync 👉", type="primary", use_container_width=True):
                st.session_state.active_tab = "Review & Multi-Sync"
                st.rerun()

    # ════════════════════════════════════════════
    # TAB 2: Review & Multi-Sync
    # ════════════════════════════════════════════
    elif st.session_state.active_tab == "Review & Multi-Sync":
        st.markdown('<div class="neu-card">', unsafe_allow_html=True)

        # ── Project summary ──
        with st.expander("📋 Project Summary", expanded=True):
            col_a, col_b = st.columns(2)
            col_a.markdown(f"**Client:** {st.session_state.client_name}")
            col_a.markdown(f"**Project:** {st.session_state.project_name}")
            col_a.markdown(f"**Venue:** {st.session_state.venue}")
            col_b.markdown(f"**Year/Month:** {st.session_state.event_year} {st.session_state.event_month}")
            col_b.markdown(f"**Category:** {st.session_state.category}")
            col_b.markdown(f"**What We Do:** {', '.join(st.session_state.what_we_do)}")

        # ── AI content generation ──
        if st.button("生成六大平台對接文案", type="primary", use_container_width=True):
            with st.spinner("AI 正在生成六大平台文案..."):
                prompt = build_content_prompt()
                res = call_gemini_sdk(
                    prompt,
                    image_files=st.session_state.project_photos if st.session_state.project_photos else None,
                    is_json=True,
                    system_prompt=FIREBEAN_SYSTEM_PROMPT,
                )
                if res:
                    try:
                        st.session_state.ai_content = json.loads(res)
                        log_debug("✅ 六大平台文案生成成功", "success")
                    except json.JSONDecodeError as je:
                        log_debug(f"JSON parse error: {je} | raw: {res[:300]}", "error")
                        st.error("AI 返回格式有誤，請重試。")
                else:
                    st.error("AI 生成失敗，請檢查 Debug Terminal。")

        # ── Show & edit AI content ──
        if st.session_state.ai_content:
            st.markdown("#### 📝 AI 生成文案 (可編輯)")
            edited = {}
            for platform, data in st.session_state.ai_content.items():
                with st.expander(f"🔵 {platform.upper()}", expanded=False):
                    platform_edits = {}
                    for field, value in data.items():
                        platform_edits[field] = st.text_area(
                            f"{field}", value, key=f"edit_{platform}_{field}", height=100
                        )
                    edited[platform] = platform_edits
            if edited:
                st.session_state.ai_content = edited

            st.markdown("---")

            # ── FAQ fields ──
            with st.expander("🌐 FAQ (多語言)", expanded=False):
                st.session_state.faq_en_edit = st.text_area("FAQ (English)", st.session_state.faq_en_edit, height=100)
                st.session_state.faq_tc_edit = st.text_area("FAQ (繁中)", st.session_state.faq_tc_edit, height=100)
                st.session_state.faq_jp_edit = st.text_area("FAQ (日文)", st.session_state.faq_jp_edit, height=100)

            # ── Confirm & Sync button ──
            if st.button("✅ Confirm & Sync to Master DB + Slide", type="primary", use_container_width=True):
                with st.spinner("🔄 同步中... 請稍候 (最長 60 秒)"):
                    pid, sdate = generate_system_metadata()
                    log_debug(f"🆔 Project ID: {pid}", "info")

                    # Process images to base64
                    processed_imgs = []
                    for f in st.session_state.project_photos:
                        try:
                            img = open_image_safe(f).convert("RGB")
                            buf = io.BytesIO()
                            img.save(buf, format="JPEG", quality=85)
                            processed_imgs.append(base64.b64encode(buf.getvalue()).decode())
                        except Exception as ie:
                            log_debug(f"Image encode skipped: {ie}", "warning")

                    # Build full payload
                    payload = {
                        "action":        "sync_project",
                        "project_id":    pid,
                        "sort_date":     sdate,
                        "client_name":   st.session_state.client_name,
                        "project_name":  st.session_state.project_name,
                        "venue":         st.session_state.venue,
                        "event_year":    st.session_state.event_year,
                        "event_month":   st.session_state.event_month,
                        "category":      st.session_state.category,
                        "what_we_do":    st.session_state.what_we_do,
                        "scope":         st.session_state.scope,
                        "youtube":       st.session_state.youtube,
                        "ai_content":    st.session_state.ai_content,
                        "images":        processed_imgs,
                        "logo_white":    st.session_state.logo_white,
                        "logo_black":    st.session_state.logo_black,
                        "faq_en":        safe_flatten_faq(st.session_state.faq_en_edit),
                        "faq_tc":        safe_flatten_faq(st.session_state.faq_tc_edit),
                        "faq_jp":        safe_flatten_faq(st.session_state.faq_jp_edit),
                        "hero_index":    st.session_state.hero_photo_index,
                    }

                    errors = []

                    # 1️⃣ Sync to Master DB (Google Sheet)
                    try:
                        r1 = requests.post(SHEET_SCRIPT_URL, json=payload, timeout=60)
                        if r1.status_code == 200:
                            log_debug(f"✅ Master DB sync OK: {r1.text[:100]}", "success")
                        else:
                            log_debug(f"⚠️ Master DB status {r1.status_code}: {r1.text[:100]}", "warning")
                            errors.append(f"Master DB: {r1.status_code}")
                    except Exception as e:
                        log_debug(f"❌ Master DB error: {e}", "error")
                        errors.append(f"Master DB: {e}")

                    # 2️⃣ Create Slide in Master DB Slide Creator
                    slide_payload = {**payload, "action": "create_slide", "photos": processed_imgs, "logo_white_base64": st.session_state.logo_white}
                    try:
                        r2 = requests.post(SLIDE_DB_URL, json=slide_payload, timeout=60)
                        if r2.status_code == 200:
                            log_debug(f"✅ Slide DB OK: {r2.text[:100]}", "success")
                        else:
                            log_debug(f"⚠️ Slide DB status {r2.status_code}: {r2.text[:100]}", "warning")
                            errors.append(f"Slide DB: {r2.status_code}")
                    except Exception as e:
                        log_debug(f"❌ Slide DB error: {e}", "error")
                        errors.append(f"Slide DB: {e}")

                    # 3️⃣ Create Firebean Case Study Slide
                    case_payload = {**slide_payload, "action": "create_case_study"}
                    try:
                        r3 = requests.post(CASE_STUDY_URL, json=case_payload, timeout=60)
                        if r3.status_code == 200:
                            log_debug(f"✅ Case Study Slide OK: {r3.text[:100]}", "success")
                        else:
                            log_debug(f"⚠️ Case Study status {r3.status_code}: {r3.text[:100]}", "warning")
                            errors.append(f"Case Study: {r3.status_code}")
                    except Exception as e:
                        log_debug(f"❌ Case Study error: {e}", "error")
                        errors.append(f"Case Study: {e}")

                    if not errors:
                        st.balloons()
                        st.success(f"🎉 同步成功！Project ID: **{pid}**")
                        st.session_state.sync_success = True
                        st.session_state.draft_project_id = pid
                    else:
                        st.warning(f"部分同步完成，Project ID: **{pid}**\n錯誤: {', '.join(errors)}")

        st.markdown("</div>", unsafe_allow_html=True)

    # ════════════════════════════════════════════
    # TAB 3: Load Project
    # ════════════════════════════════════════════
    elif st.session_state.active_tab == "Load Project":
        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        st.markdown("#### 📂 Load Existing Project")
        project_id_input = st.text_input("Enter Project ID (e.g. FB2026001)", "")
        if st.button("Load Project", use_container_width=True):
            if project_id_input:
                with st.spinner(f"Loading {project_id_input}..."):
                    try:
                        r = requests.get(
                            SHEET_SCRIPT_URL + f"?action=load_project&project_id={project_id_input}",
                            timeout=10,
                        )
                        if r.status_code == 200:
                            data = r.json()
                            st.session_state.update(data)
                            st.success(f"✅ Project {project_id_input} loaded.")
                            log_debug(f"Project {project_id_input} loaded OK", "success")
                        else:
                            st.error(f"Project not found (status {r.status_code})")
                    except Exception as e:
                        st.error(f"Load failed: {e}")
            else:
                st.warning("Please enter a Project ID.")
        st.markdown("</div>", unsafe_allow_html=True)

    # ── Debug Terminal (always visible at bottom) ──
    with st.expander("🛠️ Debug Terminal", expanded=False):
        logs = "".join(
            [f"<div style='color:{'#f00' if l['type']=='error' else '#ff0' if l['type']=='warning' else '#0f0' if l['type']=='success' else '#aaa'}'>[{l['time']}] {l['msg']}</div>"
             for l in reversed(st.session_state.get("debug_logs", []))]
        )
        st.markdown(f"<div class='debug-terminal'>{logs if logs else '<span style=color:#555>No logs yet.</span>'}</div>", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
