import streamlit as st
import google.generativeai as genai
import io
import base64
import time
import json
import requests
import re
from PIL import Image, ImageDraw, ImageOps # 確保匯入 ImageOps
from datetime import datetime

# --- 1. 核心配置 ---
SHEET_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbzaQu2KpJ06I0yWL4dEwk0naB1FOlHkt7Ta340xH84IDwQI7jQNUI3eSmxrwKyQHNj5/exec"
SLIDE_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbyZvtm8M8a5sLYF3vz9kLyAdimzzwpSlnTkzIeQ3DJxkklNYNlwSoJc5j5CkorM6w5V/exec"
STABLE_MODEL_ID = "gemini-2.5-flash"

WHO_WE_HELP_OPTIONS = ["GOVERNMENT & PUBLIC SECTOR", "LIFESTYLE & CONSUMER", "F&B & HOSPITALITY", "MALLS & VENUES"]
WHAT_WE_DO_OPTIONS = ["ROVING EXHIBITIONS", "SOCIAL & CONTENT", "INTERACTIVE & TECH", "PR & MEDIA", "EVENTS & CEREMONIES"]
SOW_OPTIONS = ["Event Planning", "Event Coordination", "Event Production", "Theme Design", "Concept Development", "Social Media Management", "KOL / MI Line up", "Artist Endorsement", "Media Pitching", "PR Consulting", "Souvenir Sourcing"]

CURRENT_YEAR = datetime.now().year
YEAR_OPTIONS = [str(y) for y in range(CURRENT_YEAR, 2011, -1)]
MONTH_OPTIONS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]

# --- NEW: 系統自動生成邏輯 (ID 與 日期) ---
def generate_system_metadata():
    """自動生成大寫無符號 Project_id 與標準化 Sort_date"""
    # 1. 映射月份為數字 (Sort_date 用)
    month_map = {m: str(i+1).zfill(2) for i, m in enumerate(MONTH_OPTIONS)}
    m_num = month_map.get(st.session_state.event_month, "01")
    sort_date = f"{st.session_state.event_year}-{m_num}-01"

    # 2. 獲取當前行數生成 ID (向 Sheet 索取當前總行數)
    try:
        # 這裡會觸發 Google Sheet Script 的 action=get_row_count 
        count_res = requests.get(SHEET_SCRIPT_URL + "?action=get_row_count", timeout=5)
        next_index = int(count_res.text) + 1 if count_res.status_code == 200 else 100
    except:
        next_index = 999 
    
    # 格式：FB + 年份 + 三位序號 (如 FB2026005)
    project_id = f"FB{st.session_state.event_year}{str(next_index).zfill(3)}"
    
    return project_id, sort_date

FIREBEAN_SYSTEM_PROMPT = """
You are a Lead PR Strategist and Chief Editor for a premium B2B/B2C communications agency.
Task: Transform diagnostic data into a professional PR strategy JSON.
Always return a valid JSON object with keys: challenge_summary, solution_summary, 1_google_slide, 2_facebook_post, 3_threads_post, 4_instagram_post, 5_linkedin_post, 6_website.

**ABSOLUTE RULE 1 — POST-EVENT RETROSPECTIVE MODE**:
This tool is EXCLUSIVELY used AFTER an event has already taken place. All content you generate MUST be written as a retrospective case showcase — as if you are a journalist or PR strategist documenting and celebrating what already happened.

**ABSOLUTE RULE 2 — INTERNAL TERMINOLOGY PROHIBITION**:
NEVER use the phrase "Firebean Brain", "Firebean Brain Team", or any similar internal terminology in ANY output. These are internal tools only, NOT for public communication.
Instead, use professional alternatives:
- "Our strategic approach", "Our creative concept", "Our team's expertise", "The project team", "Our strategic thinking"
Example: Instead of "Firebean Brain identified the challenge", write "Our strategic analysis revealed the challenge".

STRICTLY FORBIDDEN in ALL outputs (applies to every key in the JSON):
- ANY invitation language (e.g. "join us", "register now", "don't miss", "come and experience", "歡迎報名", "立即登記", "名額有限" etc.)
- ANY future-tense event promotion (e.g. "the event will be held", "活動將於...舉行", "即將舉行" etc.)
- ANY specific date, time, ticket price, or venue address used in a promotional context
- ANY CTA links or registration details
- Phrases like "save the date", "mark your calendar", "coming soon"
- Internal terminology: "Firebean Brain", "Firebean Brain Team", or similar

INSTEAD, always use retrospective language:
- English: "The event took place...", "Guests experienced...", "The project delivered...", "What unfolded was..."
- 繁中: 「活動已圓滿結束」、「當日現場」、「是次項目成功」、「回顧今次」
- Time references: Use vague retrospective references only (e.g. "recently", "at the event", "on the day"). DO NOT state specific year, month, date, or time in the body text — these details belong in metadata only, not in the narrative.

**CRITICAL INSTRUCTION FOR 'challenge_summary'**:
You MUST keep the client's pain points and challenges extremely concise. Use only 1 to 2 short, punchy sentences (maximum 50 words) to define the core challenge. Do not elaborate excessively on the negative impacts.

**CRITICAL INSTRUCTION FOR '6_website' (Magazine Feature Article)**:
The '6_website' key MUST be a nested JSON object containing exactly four keys: "angle_chosen", "en", "tc", and "jp".
Write a highly engaging, 500-word POST-EVENT feature article. This is a case study showcase for the agency's portfolio website, intended to impress prospective clients — NOT to promote a future event.

To ensure a diverse content library, RANDOMLY SELECT ONLY ONE of the 5 writing styles/angles below. Do not mix styles:
1. The Thought Leadership Angle: Reflect on the industry challenge. Frame the Pain Point as a systemic flaw that this project addressed, and the outcome as a visionary blueprint for the industry.
2. The Contrarian / Disruptor Angle: Start with a bold, counter-intuitive hook about what most events get wrong. Show how this project disrupted the norm and delivered something unexpected.
3. The Human-Centric / Emotional Storytelling Angle: Focus on the human experience at the event — the energy, the moments, the emotional impact. Write as if you were there witnessing it.
4. The Analytical Problem-Solver: Break down the brief, the challenge, and the strategic solution. Show how the agency's approach logically solved the client's problem.
5. The Insider / Behind-the-Scenes Angle: Write from an exclusive perspective, revealing the creative process, the challenges overcome during production, and the final triumphant result.

Format & Structure Requirements for '6_website':
- Word Count: Approximately 500 words per language.
    - Structure: Use exactly three sections, each starting with an <h3> heading.
    - Paragraph Count: Ensure each of the three sections contains at least one substantive paragraph (<p>). This is crucial for photo interleaving.
    - The Core Narrative: Seamlessly weave the [Basic Information], [Project Outcome], [Challenge], and [Solution] into the chosen narrative angle. All written in past tense.
    - The Punch Line: The final paragraph before the FAQ must be a single, bolded, highly memorable concluding sentence about the project's impact.
    - The Fast Recap FAQ: End with exactly three Q&A pairs. Use the heading #### Fast Recap FAQ.
    
    **CRITICAL HTML STRUCTURE REQUIREMENT FOR '6_website'**:
    You MUST output valid HTML that matches the CMS parsing format exactly. The structure MUST follow this pattern for photo interleaving:
    <h1>Main Title</h1>
    <h3>First Section Heading</h3>
    <p>Paragraph 1...</p>
    <h3>Second Section Heading</h3>
    <p>Paragraph 2...</p>
    <h3>Third Section Heading</h3>
    <p>Paragraph 3...</p>
    <p>The bolded punch line sentence.</p>
    ### Fast Recap FAQ:
    Q1: Question 1?
    A1: Answer 1...
    Q2: Question 2?
    A2: Answer 2...
    Q3: Question 3?
    A3: Answer 3...
    
    STRICT RULES FOR HTML:
    1. Use ONLY <h1>, <h3>, and <p> tags for main content.
    2. DO NOT use <h2>, <h4>, or any other heading tags.
    3. DO NOT use <span>, <div>, <b>, <strong>, or any style attributes (no inline colors).
    4. After the last paragraph, add a blank line, then switch to Markdown format.
    
    STRICT RULES FOR Q&A SECTION (CRITICAL - MUST BE IN MARKDOWN FORMAT):
    5. The Q&A section MUST use Markdown format, NOT HTML.
    6. The FAQ heading MUST be exactly: ### Fast Recap FAQ:
    7. Each question MUST start with Q1:, Q2:, Q3: (with colon, not question mark).
    8. Each answer MUST start with A1:, A2:, A3: (with colon).
    9. Q&A pairs MUST be on separate lines, one per line.
    10. DO NOT use <h4>, <h3>, or any HTML tags for Q&A - use pure Markdown.
    11. Example format:
        ### Fast Recap FAQ:
        Q1: What was the main challenge?
        A1: The challenge was...
        Q2: How did you solve it?
        A2: We solved it by...
        Q3: What was the outcome?
        A3: The outcome was...

Language Output Requirement for '6_website':
- "angle_chosen": State the name of the angle you selected (e.g., "Style 2: The Contrarian").
- "en": English (Premium editorial, past-tense retrospective tone, valid HTML structure)
- "tc": Traditional Chinese (Hong Kong localization, fluent and natural editorial style, past tense, valid HTML structure)
- "jp": Japanese (Polite, professional business-magazine tone - Desu/Masu form, past tense, valid HTML structure)

**CRITICAL INSTRUCTIONS FOR SOCIAL MEDIA POSTS (2_facebook, 3_threads, 4_instagram, 5_linkedin)**:
All social media posts are POST-EVENT highlights for the agency's own channels. The purpose is to showcase completed work to attract future clients and build brand authority — NOT to promote attendance.

1. '2_facebook_post' (活動精彩回顧):
   - Word Count: 100 - 250 words.
   - Tone: 親切有溫度、故事化。語氣像在跟朋友分享一個精彩的工作回顧。
   - Content: 以「回顧」角度出發，分享活動當日的精彩片段、現場氣氛、團隊如何克服挑戰並交出成果。重點突出項目的亮點與成就。
   - Format: 純回顧內容。絕對不可加入報名連結、活動日期時間、票務資訊或任何邀請參與的字眼。
   - Language: 香港繁體中文 (可適度夾雜廣東話口語)。

2. '4_instagram_post' (幕後花絮 & 成果展示):
   - Word Count: STRICTLY < 150 words. 頭兩行必須在「展開」前抓住眼球。
   - Tone: 極簡視覺化、真實「貼地」，展示團隊的專業與創意成果。
   - Content: 幕後花絮視角 (Behind-the-scenes retrospective)。聚焦團隊籌備過程的真實片段、當日現場的精彩瞬間、最終成果的視覺衝擊。以「已完成」的自豪感作為語氣基調。
   - Format: 配合 Emoji 分段，必帶專業 Hashtags。絕對不可出現活動日期、時間或任何邀請字眼。
   - Language: 香港繁體中文。

3. '3_threads_post' (觀點分享 & 行業洞察):
   - Word Count: 短小精悍，< 50 words (Max 200 characters).
   - Tone: 幽默口語化、隨性但具洞察力。具備引發討論的潛力。
   - Content: 以「做完這個項目之後的感想」為出發點，拋出一個行業觀點或反思 (例如：「做完今次先發現，原來大多數活動都係咁死㗎...」)。絕對不可出現「即將舉行」、「歡迎參與」等字眼。
   - Language: 最地道的廣東話/網絡用語，語氣要 casual。

4. '5_linkedin_post' (案例分析 & 思想領導力):
   - Word Count: 150 - 300 words. 段落必須分明。
   - Tone: 權威 B2B、專業顧問風格。以完成項目的角度分享行業洞見。
   - Content: 以「案例分享」形式，由專業角度回顧此項目：我們面對的挑戰是什麼、我們的策略思維是什麼、最終成果如何。目的是向潛在 B2B 客戶展示公司的專業能力與解決問題的思維。絕對不可出現活動日期、報名資訊或邀請字眼。
   - Language: 雙語並行 (English first, followed by Traditional Chinese)。

DO NOT output any conversational text outside the JSON object.
"""

# --- 2. 核心邏輯 ---

def log_debug(msg, type="info"):
    if "debug_logs" not in st.session_state: st.session_state.debug_logs = []
    timestamp = datetime.now().strftime("%H:%M:%S")
    st.session_state.debug_logs.append({"time": timestamp, "msg": msg, "type": type})

def call_gemini_sdk(prompt, image_files=None, is_json=False, max_retries=2):
    """呼叫 Gemini API，內建 JSON 容錯重試機制 (優化 C)"""
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
                # 嘗試提取 JSON
                match = re.search(r'(\{.*\})|(\[.*\])', text, re.DOTALL)
                json_str = match.group(0) if match else text
                # 驗證 JSON 是否有效
                json.loads(json_str)
                return json_str

        except json.JSONDecodeError as je:
            log_debug(f"⚠️ JSON 解析失敗 (第 {attempt+1} 次)，正在重試... 錯誤: {str(je)}", "error")
            if attempt < max_retries - 1:
                time.sleep(1)
                continue
            else:
                st.warning("⚠️ AI 返回格式不穩定，請再試一次。")
        except Exception as e:
            log_debug(f"❌ API 錯誤: {str(e)}", "error")
            st.error("❌ AI 運算發生錯誤，請查看 Debug Terminal 日誌。")
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
        "sync_success": False,  # 記錄同步是否成功
        "draft_project_id": "",  # 記錄已載入的草稿 ID（用於更新而非新增）
        "loaded_image_urls": [],  # 記錄從草稿載入的圖片 URLs
    }
    for k, v in fields.items():
        if k not in st.session_state:
            st.session_state[k] = v

def reset_for_new_case():
    """完全清空所有資料，準備輸入下一個案例"""
    keys_to_reset = [
        "client_name", "project_name", "venue", "youtube",
        "event_year", "event_month", "category", "what_we_do", "scope",
        "project_photos", "ai_content", "logo_white", "logo_black",
        "mc_questions", "open_question_ans", "challenge", "solution",
        "visual_facts", "hero_photo_index", "sync_success",
        "draft_project_id", "loaded_image_urls"
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
    # 清除 15 題答案
    for i in range(1, 16):
        if f"ans_{i}" in st.session_state:
            del st.session_state[f"ans_{i}"]
    # 清除 logo uploader 的 widget key
    for key in ["l_b", "l_w"]:
        if key in st.session_state:
            del st.session_state[key]
    st.session_state.active_tab = "Project Collector"
    log_debug("🔄 已重置，準備輸入下一個案例。", "success")

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
    log_debug("🚀 高質量測試數據填充完成，進度將達 100%。", "success")

# --- 3. UI 元件 ---

def get_is_dark_mode():
    """根據香港時間判斷是否為夜間模式 (20:00 - 07:59 為深色模式)"""
    # 使用 UTC+8 (香港時間)
    from datetime import timezone, timedelta
    hk_tz = timezone(timedelta(hours=8))
    hk_hour = datetime.now(hk_tz).hour
    # 晚上 8 點 (20:00) 至 早上 7 點 (07:59) 為 Dark Mode
    return hk_hour >= 20 or hk_hour < 8

def get_circle_progress_html(percent, is_dark):
    circum = 439.8
    offset = circum * (1 - percent/100)
    if is_dark:
        bg = "#2A2D35"
        shadow_dark = "#1a1d23"
        shadow_light = "#3a3f4d"
        text_color = "#E0E5EC"
        track_color = "#1E2128"
    else:
        bg = "#E0E5EC"
        shadow_dark = "#bec3c9"
        shadow_light = "#ffffff"
        text_color = "#2D3436"
        track_color = "#d1d9e6"
    return f"""<div style='display: flex; justify-content: flex-end;'><div style='position: relative; width: 110px; height: 110px; border-radius: 50%; background: {bg}; box-shadow: 9px 9px 16px {shadow_dark}, -9px -9px 16px {shadow_light}; display: flex; align-items: center; justify-content: center;'><svg width='110' height='110'><circle stroke='{track_color}' stroke-width='8' fill='transparent' r='45' cx='55' cy='55'/><circle stroke='#FF0000' stroke-width='8' stroke-dasharray='{circum}' stroke-dashoffset='{offset}' stroke-linecap='round' fill='transparent' r='45' cx='55' cy='55' style='transition: all 0.8s; transform: rotate(-90deg); transform-origin: center;'/></svg><div style='position: absolute; font-size: 20px; font-weight: 900; color: {text_color};'>{percent}%</div></div></div>"""

def apply_styles(is_dark):
    if is_dark:
        # ── Dark Mode Neumorphism ──
        # 底色：深灰藍 #1E2128
        # 凸起陰影：更深 #14161C (暗面) + 稍亮 #282C38 (亮面)
        # 凹陷陰影：反向
        bg_color       = "#1E2128"
        card_bg        = "#1E2128"
        shadow_dark    = "#14161C"
        shadow_light   = "#282C38"
        text_color     = "#E0E5EC"
        subtext_color  = "#A0A8B8"
        hr_color       = "#3A3F4D"
        input_bg       = "#252830"
        input_border   = "#3A3F4D"
        toggle_label   = "🌙 夜間模式"
        toggle_bg      = "#252830"
        toggle_border  = "#3A3F4D"
    else:
        # ── Light Mode Neumorphism ──
        bg_color       = "#E0E5EC"
        card_bg        = "#E0E5EC"
        shadow_dark    = "#bec3c9"
        shadow_light   = "#ffffff"
        text_color     = "#2D3436"
        subtext_color  = "#636e72"
        hr_color       = "#c8cdd4"
        input_bg       = "#e8ecf2"
        input_border   = "#d0d5dc"
        toggle_label   = "☀️ 日間模式"
        toggle_bg      = "#E0E5EC"
        toggle_border  = "#c8cdd4"

    st.markdown(f"""<style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;900&display=swap');

        header {{visibility: hidden;}} footer {{visibility: hidden;}}

        /* ── 全域底色與字色 ── */
        .stApp {{
            background-color: {bg_color} !important;
            color: {text_color} !important;
            font-family: 'Inter', sans-serif;
            transition: background-color 0.6s ease, color 0.6s ease;
        }}

        /* ── 所有文字元素 ── */
        .stApp p, .stApp span, .stApp label, .stApp div,
        .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6,
        .stMarkdown, .stText {{
            color: {text_color} !important;
        }}

        /* ── Neumorphism 卡片（凸起效果） ── */
        .neu-card {{
            background: {card_bg};
            border-radius: 20px;
            box-shadow: 9px 9px 16px {shadow_dark}, -9px -9px 16px {shadow_light};
            padding: 25px;
            margin-bottom: 20px;
            transition: background 0.6s ease, box-shadow 0.6s ease;
        }}

        /* ── 分隔線 ── */
        hr {{
            border-color: {hr_color} !important;
        }}

        /* ── 輸入框 ── */
        .stTextInput > div > div > input,
        .stTextArea > div > div > textarea,
        .stSelectbox > div > div > div {{
            background-color: {input_bg} !important;
            color: {text_color} !important;
            border: 1px solid {input_border} !important;
            border-radius: 10px !important;
            box-shadow: inset 3px 3px 6px {shadow_dark}, inset -3px -3px 6px {shadow_light} !important;
            transition: all 0.4s ease;
        }}

        /* ── Selectbox 下拉選項 ── */
        .stSelectbox [data-baseweb="select"] > div {{
            background-color: {input_bg} !important;
            color: {text_color} !important;
            border: 1px solid {input_border} !important;
            box-shadow: inset 3px 3px 6px {shadow_dark}, inset -3px -3px 6px {shadow_light} !important;
        }}

        /* ── Radio & Checkbox 標籤 ── */
        .stRadio label, .stCheckbox label {{
            color: {text_color} !important;
        }}

        /* ── Expander ── */
        .streamlit-expanderHeader {{
            background-color: {card_bg} !important;
            color: {text_color} !important;
            border-radius: 12px !important;
            box-shadow: 4px 4px 8px {shadow_dark}, -4px -4px 8px {shadow_light} !important;
        }}
        .streamlit-expanderContent {{
            background-color: {card_bg} !important;
            border-radius: 0 0 12px 12px !important;
        }}

        /* ── 一般按鈕（凸起效果） ── */
        .stButton > button {{
            min-height: 55px !important;
            font-size: 18px !important;
            font-weight: 700 !important;
            background-color: {card_bg} !important;
            color: {text_color} !important;
            border: none !important;
            border-radius: 14px !important;
            box-shadow: 6px 6px 12px {shadow_dark}, -6px -6px 12px {shadow_light} !important;
            transition: all 0.2s ease !important;
        }}
        .stButton > button:hover {{
            box-shadow: 3px 3px 6px {shadow_dark}, -3px -3px 6px {shadow_light} !important;
            transform: translateY(1px) !important;
        }}
        .stButton > button:active {{
            box-shadow: inset 3px 3px 6px {shadow_dark}, inset -3px -3px 6px {shadow_light} !important;
            transform: translateY(2px) !important;
        }}

        /* ── Logo 按鈕（特殊樣式，不受一般按鈕覆蓋） ── */
        div[data-testid="stElementContainer"]:has(#logo-anchor) + div[data-testid="stElementContainer"] button,
        div.element-container:has(#logo-anchor) + div.element-container button {{
            background-image: url('https://raw.githubusercontent.com/dickson-crypto/Firebean-app/main/Firebeanlogo2026.png') !important;
            background-size: contain !important; background-repeat: no-repeat !important; background-position: left center !important;
            background-color: transparent !important; border: none !important; box-shadow: none !important;
            min-height: 180px !important; width: 540px !important; padding: 0 !important; margin-top: -10px;
        }}
        div.element-container:has(#logo-anchor) + div.element-container button:hover,
        div[data-testid="stElementContainer"]:has(#logo-anchor) + div[data-testid="stElementContainer"] button:hover {{
            transform: scale(1.03) !important; background-color: transparent !important; box-shadow: none !important;
        }}
        div.element-container:has(#logo-anchor) + div.element-container button p,
        div[data-testid="stElementContainer"]:has(#logo-anchor) + div[data-testid="stElementContainer"] button p {{
            display: none !important;
        }}

        /* ── Primary 按鈕（紅色 CTA） ── */
        button[kind="primary"] {{
            background-color: #FF2A2A !important;
            color: white !important;
            border: 2px solid #D00000 !important;
            border-radius: 12px !important;
            transition: all 0.3s ease-in-out !important;
            box-shadow: 0px 4px 15px rgba(255, 0, 0, 0.35) !important;
        }}
        button[kind="primary"]:hover {{
            background-color: #D00000 !important;
            transform: scale(1.02) !important;
            box-shadow: 0px 6px 20px rgba(255, 0, 0, 0.55) !important;
        }}

        /* ── MC 診斷題目 ── */
        .mc-question {{
            font-weight: 700;
            color: #FF0000 !important;
            margin-top: 15px;
            border-left: 4px solid #FF0000;
            padding-left: 10px;
            margin-bottom: 10px;
        }}
        .checkbox-group {{ padding-left: 20px; }}

        /* ── Debug Terminal ── */
        .debug-terminal {{
            background: #0D0F14 !important;
            color: #00FF88 !important;
            padding: 15px;
            font-size: 11px;
            border-top: 4px solid #FF0000;
            border-radius: 10px;
            height: 300px;
            overflow-y: scroll;
        }}

        /* ── 模式標籤 ── */
        .mode-badge {{
            display: inline-block;
            padding: 4px 14px;
            border-radius: 20px;
            font-size: 13px;
            font-weight: 700;
            background: {toggle_bg};
            color: {text_color};
            border: 1px solid {toggle_border};
            box-shadow: 3px 3px 6px {shadow_dark}, -3px -3px 6px {shadow_light};
            margin-top: 8px;
        }}

        /* ── File Uploader ── */
        .stFileUploader > div {{
            background-color: {input_bg} !important;
            border: 2px dashed {input_border} !important;
            border-radius: 12px !important;
            color: {text_color} !important;
        }}

        /* ── Spinner / Status ── */
        .stSpinner > div {{
            border-top-color: #FF2A2A !important;
        }}

        /* ── Toast / Success / Error ── */
        .stSuccess {{
            background-color: {'#1a2e1a' if is_dark else '#d4edda'} !important;
            color: {'#6fcf97' if is_dark else '#155724'} !important;
            border-radius: 10px !important;
        }}
        .stError {{
            background-color: {'#2e1a1a' if is_dark else '#f8d7da'} !important;
            color: {'#eb5757' if is_dark else '#721c24'} !important;
            border-radius: 10px !important;
        }}

    </style>""", unsafe_allow_html=True)

# --- 4. Main App ---

# ── Draft Save / Load Helper Functions ──

def fetch_draft_list():
    """Fetch the list of saved drafts from Google Sheet Raw_Input_DB."""
    try:
        r = requests.post(SHEET_SCRIPT_URL, json={"action": "get_raw_input_list"}, timeout=15)
        if r.status_code == 200:
            data = r.json()
            if data.get("status") == "success":
                return data.get("data", [])
    except Exception as e:
        log_debug(f"❌ 無法獲取草稿列表: {str(e)}", "error")
    return []

def load_draft_into_session(project_id):
    """Load a specific draft from Google Sheet into session state."""
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
                yr = str(d.get("event_year", CURRENT_YEAR))
                st.session_state.event_year = yr if yr in YEAR_OPTIONS else str(CURRENT_YEAR)
                mo = d.get("event_month", "FEB").upper()
                st.session_state.event_month = mo if mo in MONTH_OPTIONS else "FEB"
                cat = d.get("category", WHO_WE_HELP_OPTIONS[0])
                st.session_state.category = cat if cat in WHO_WE_HELP_OPTIONS else WHO_WE_HELP_OPTIONS[0]
                st.session_state.what_we_do = [w for w in d.get("what_we_do", []) if w in WHAT_WE_DO_OPTIONS]
                st.session_state.scope = [s for s in d.get("scope", []) if s in SOW_OPTIONS]
                st.session_state.mc_questions = d.get("mc_questions", [])
                st.session_state.loaded_image_urls = d.get("image_urls", [])
                st.session_state.draft_project_id = project_id
                st.session_state.project_photos = []  # Reset file uploader
                st.session_state.ai_content = {}  # Reset AI content
                log_debug(f"✅ 已成功載入草稿: {project_id}", "success")
                return True
    except Exception as e:
        log_debug(f"❌ 載入草稿失敗: {str(e)}", "error")
    return False

def save_draft_to_sheet():
    """Save current input data as a draft to Google Sheet Raw_Input_DB."""
    try:
        # Process new images to base64 if any are uploaded
        processed_imgs = []
        if st.session_state.project_photos:
            for f in st.session_state.project_photos:
                if hasattr(f, "seek"): f.seek(0)
                try:
                    img = Image.open(f).convert("RGB")
                    img = ImageOps.exif_transpose(img)
                    img.thumbnail((800, 800))  # Smaller size for drafts
                    buf = io.BytesIO()
                    img.save(buf, format="JPEG", quality=70)
                    processed_imgs.append(base64.b64encode(buf.getvalue()).decode())
                except Exception as e:
                    if hasattr(f, "seek"): f.seek(0)
                    processed_imgs.append(base64.b64encode(f.read()).decode())

        # Use existing draft ID if available, otherwise generate a new one
        draft_id = st.session_state.get("draft_project_id", "") or f"DRAFT_{st.session_state.client_name.replace(' ', '_')}_{int(time.time())}"

        payload = {
            "action": "save_raw_input",
            "project_id": draft_id,
            "client_name": st.session_state.client_name,
            "project_name": st.session_state.project_name,
            "venue": st.session_state.venue,
            "event_year": st.session_state.event_year,
            "event_month": st.session_state.event_month,
            "youtube": st.session_state.youtube,
            "category": st.session_state.category,
            "what_we_do": st.session_state.what_we_do,
            "scope": st.session_state.scope,
            "mc_questions": st.session_state.mc_questions,
            "open_question": st.session_state.open_question_ans,
            "images": processed_imgs,
            "existing_image_urls": st.session_state.get("loaded_image_urls", []) if not processed_imgs else []
        }
        r = requests.post(SHEET_SCRIPT_URL, json=payload, timeout=60)
        if r.status_code == 200:
            result = r.json()
            if result.get("status") == "success":
                st.session_state.draft_project_id = result.get("project_id", draft_id)
                log_debug(f"✅ 草稿儲存成功: {st.session_state.draft_project_id}", "success")
                return True
    except Exception as e:
        log_debug(f"❌ 草稿儲存失敗: {str(e)}", "error")
    return False

def main():
    st.set_page_config(page_title="Firebean Brain Collector", layout="wide")
    init_session_state()

    # 自動偵測時間決定模式
    is_dark = get_is_dark_mode()
    apply_styles(is_dark)

    c1, c2 = st.columns([1, 1])
    with c1: 
        st.markdown('<span id="logo-anchor"></span>', unsafe_allow_html=True)
        # ── HOME 按鈕：若已同步成功則完全重置；否則只切換回 Tab 1 ──
        if st.button("🏠 HOME", key="logo_btn", help="返回主頁 / 同步後點擊可重置輸入下一個案例"):
            if st.session_state.get("sync_success", False):
                reset_for_new_case()
            else:
                st.session_state.active_tab = "Project Collector"
            st.rerun()
    with c2: 
        progress_placeholder = st.empty()

    st.markdown("<br>", unsafe_allow_html=True)
    
    nav_cols = st.columns(4)
    if nav_cols[0].button("Project Collector", use_container_width=True, type="primary" if st.session_state.active_tab == "Project Collector" else "secondary"):
        st.session_state.active_tab = "Project Collector"
        st.rerun()
    if nav_cols[1].button("Review & Multi-Sync", use_container_width=True, type="primary" if st.session_state.active_tab == "Review & Multi-Sync" else "secondary"):
        st.session_state.active_tab = "Review & Multi-Sync"
        st.rerun()
    if nav_cols[2].button("📂 Load Project", use_container_width=True, type="primary" if st.session_state.active_tab == "Load Project" else "secondary"):
        st.session_state.active_tab = "Load Project"
        st.rerun()
    if nav_cols[3].button("老細一鍵填充 (深度內容測試)", use_container_width=True):
        fill_dummy_data()
        st.rerun()

    st.markdown("<hr style='margin-top: 5px; margin-bottom: 20px;'>", unsafe_allow_html=True)

    # --- TAB 分頁內容 ---
    if st.session_state.active_tab == "Load Project":
        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        st.markdown("### 📂 載入已儲存的草稿項目 (Load Existing Draft)")
        load_col1, load_col2 = st.columns([3, 1])
        with load_col1:
            if st.button("🔄 獲取草稿列表", use_container_width=True, type="primary"):
                with st.spinner("正在獲取草稿列表..."):
                    drafts = fetch_draft_list()
                    st.session_state["_draft_list"] = drafts
                    if not drafts:
                        st.info("目前尚未儲存任何草稿。")
        with load_col2:
            if st.session_state.get("draft_project_id"):
                st.markdown(f"✅ 目前已載入: `{st.session_state.draft_project_id}`")

        drafts = st.session_state.get("_draft_list", [])
        if drafts:
            st.markdown("<br>", unsafe_allow_html=True)
            draft_options = {f"{d['client_name']} / {d['project_name']} ({d['project_id']})": d['project_id'] for d in drafts}
            selected_label = st.selectbox("選擇要載入的項目", list(draft_options.keys()))
            if st.button("⬇️ 載入此項目到表單並前往 Project Collector", type="primary", use_container_width=True):
                with st.spinner("正在載入項目資料..."):
                    pid = draft_options[selected_label]
                    if load_draft_into_session(pid):
                        st.session_state.active_tab = "Project Collector"
                        st.rerun()
                    else:
                        st.error("❌ 載入失敗，請檢查 Debug Terminal。")

        # Show loaded image previews if any
        if st.session_state.get("loaded_image_urls"):
            st.markdown("<hr>", unsafe_allow_html=True)
            st.markdown("**🖼️ 已載入的圖片（儲存於 Google Drive）:**")
            img_cols = st.columns(min(4, len(st.session_state.loaded_image_urls)))
            for i, url in enumerate(st.session_state.loaded_image_urls):
                with img_cols[i % 4]:
                    st.markdown(f"[🖼️ 圖片 {i+1}]({url})", unsafe_allow_html=False)
            st.info("💡 如需更換圖片，請在 Project Collector 頁面直接重新上傳新照片即可。")
        st.markdown('</div>', unsafe_allow_html=True)

    elif st.session_state.active_tab == "Project Collector":

        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            ub = st.file_uploader("Black Logo ✱ (Required)", type=['png'], key="l_b")
            if ub is not None: 
                st.session_state.logo_black = base64.b64encode(ub.read()).decode()
            
            if st.session_state.logo_black:
                preview_bg = "#1E2128" if is_dark else "#f9f9f9"
                st.markdown(f'''
                    <div style="margin-top: -10px; margin-bottom: 10px; padding: 10px; border: 1px dashed #ccc; border-radius: 8px; display: inline-block; background-color: {preview_bg}; text-align: center;">
                        <span style="font-size: 10px; color: #888; display: block; margin-bottom: 5px;">Preview</span>
                        <img src="data:image/png;base64,{st.session_state.logo_black}" style="max-height: 60px; max-width: 150px; object-fit: contain;">
                    </div>
                ''', unsafe_allow_html=True)

        with col2:
            uw = st.file_uploader("White Logo ✱ (Required)", type=['png'], key="l_w")
            if uw is not None: 
                st.session_state.logo_white = base64.b64encode(uw.read()).decode()
                
            if st.session_state.logo_white:
                st.markdown(f'''
                    <div style="margin-top: -10px; margin-bottom: 10px; padding: 10px; border: 1px dashed #ccc; border-radius: 8px; display: inline-block; background-color: #2D3436; text-align: center;">
                        <span style="font-size: 10px; color: #aaa; display: block; margin-bottom: 5px;">Preview</span>
                        <img src="data:image/png;base64,{st.session_state.logo_white}" style="max-height: 60px; max-width: 150px; object-fit: contain;">
                    </div>
                ''', unsafe_allow_html=True)

        b1, b2, b3 = st.columns(3)
        st.session_state.client_name = b1.text_input("Client", st.session_state.client_name)
        st.session_state.project_name = b2.text_input("Project", st.session_state.project_name)
        st.session_state.venue = b3.text_input("Venue", st.session_state.venue)

        b4, b5, b6 = st.columns(3)
        y_idx = YEAR_OPTIONS.index(st.session_state.event_year) if st.session_state.event_year in YEAR_OPTIONS else 0
        m_idx = MONTH_OPTIONS.index(st.session_state.event_month) if st.session_state.event_month in MONTH_OPTIONS else 1
        st.session_state.event_year = b4.selectbox("Event Year", YEAR_OPTIONS, index=y_idx)
        st.session_state.event_month = b5.selectbox("Event Month", MONTH_OPTIONS, index=m_idx)
        st.session_state.youtube = b6.text_input("YouTube Link (Optional)", st.session_state.youtube)

        st.markdown("<hr style='margin-top: 10px; margin-bottom: 10px;'>", unsafe_allow_html=True)

        ca, cb, cc = st.columns(3)
        with ca:
            st.markdown("##### Category")
            st.session_state.category = st.radio("Category", WHO_WE_HELP_OPTIONS, index=WHO_WE_HELP_OPTIONS.index(st.session_state.category) if st.session_state.category in WHO_WE_HELP_OPTIONS else 0, label_visibility="collapsed")
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
                        st.write("📸 正在提取並分析活動相片的視覺細節...")
                        vision_prompt = """
                        請使用繁體中文 (Traditional Chinese)，詳細掃描並提取這些活動相片中的實體事實 (Facts)。
                        請務必精準識別並描述以下五大細節，作為後續 PR 診斷之客觀依據：
                        1. Branding (品牌識別與曝光程度)
                        2. 現場佈置 (Decor & 氛圍)
                        3. 科技設備 (Tech & 互動裝置)
                        4. 人流規模 (Crowd & 參與度)
                        5. 餐飲細節 (F&B 服務水準)
                        """
                        # 圖片自動轉正後傳給 AI
                        facts = call_gemini_sdk(vision_prompt, image_files=st.session_state.project_photos)
                        
                        st.write("📊 視覺分析完成！正在消化 SOW 與客戶背景資料...")
                        time.sleep(1)
                        
                        st.write("📝 開始構思 15 條專業 PR 診斷題目...")
                        mc_prompt = f"""
請基於以下專案背景資料與相片分析事實，生成 15 題繁體中文的專業 PR 診斷選擇題 (MC)，以評估此專案的潛在挑戰與優化空間。
【專案背景資料】
- 客戶與專案名稱：{st.session_state.client_name} / {st.session_state.project_name}
- 產業類別 (Category)：{st.session_state.category}
- 活動時間與地點：{st.session_state.event_year} {st.session_state.event_month} 於 {st.session_state.venue}
- 核心服務形式 (What we do)：{", ".join(st.session_state.what_we_do)}
- 工作範圍 (Scope of Work)：{", ".join(st.session_state.scope)}

【現場/視覺相片分析事實】
{facts}

請確保題目具備深度，能引導出具體的痛點。
必須嚴格輸出為 JSON 陣列格式：[{{"id":1,"question":"問題內容...","options":["選項A","選項B"]}}]
"""
                        res = call_gemini_sdk(mc_prompt, is_json=True)
                        if res: 
                            st.session_state.mc_questions = json.loads(res)
                            status.update(label="✅ 分析與題目生成完畢！", state="complete", expanded=False)
                            time.sleep(1)
                            st.rerun()

            if st.session_state.mc_questions:
                if isinstance(st.session_state.mc_questions, list):
                    for q in st.session_state.mc_questions:
                        if isinstance(q, dict) and 'id' in q:
                            st.markdown(f"<div class='mc-question'>Q{q['id']}. {q['question']}</div>", unsafe_allow_html=True)
                            st.markdown("<div class='checkbox-group'>", unsafe_allow_html=True)
                            
                            ans_key = f"ans_{q['id']}"
                            current_selections = st.session_state.get(ans_key, [])
                            new_selections = []
                            
                            for opt in q['options']:
                                is_checked = opt in current_selections
                                if st.checkbox(opt, value=is_checked, key=f"chk_{q['id']}_{opt}"):
                                    new_selections.append(opt)
                            
                            st.session_state[ans_key] = new_selections
                            st.markdown("</div>", unsafe_allow_html=True)

                st.session_state.open_question_ans = st.text_area("最核心的概念？", st.session_state.open_question_ans)
            st.markdown('</div>', unsafe_allow_html=True)

        with cr:
            st.markdown('<div class="neu-card">', unsafe_allow_html=True)
            f_up = st.file_uploader("Upload 4-8 Photos", accept_multiple_files=True)
            if f_up: st.session_state.project_photos = f_up
            
            if st.session_state.project_photos:
                st.markdown("##### 📸 Photo Preview & Select Hero Banner")
                
                photo_names = [f"Photo {i+1}" for i in range(len(st.session_state.project_photos))]
                st.session_state.hero_photo_index = st.radio(
                    "請選擇一張作為 Website 的 Hero Banner (這張將會被設定為 Hero Photo Link):",
                    options=range(len(st.session_state.project_photos)),
                    format_func=lambda x: photo_names[x],
                    horizontal=True
                )
                
                g_cols = st.columns(4)
                for i, f in enumerate(st.session_state.project_photos):
                    with g_cols[i%4]:
                        try: 
                            if hasattr(f, "seek"): f.seek(0)
                            img = Image.open(f)
                            # 🚀 修復：在 UI 畫面上顯示前，先旋轉為正確方向
                            img = ImageOps.exif_transpose(img)
                            st.image(img, use_container_width=True)
                            if i == st.session_state.hero_photo_index:
                                st.markdown("🌟 **Hero**")
                        except: 
                            st.image(f, use_container_width=True)
                            
            st.markdown('</div>', unsafe_allow_html=True)

        # 進度計算
        filled_count = 0
        missing_items = []
        # ── 修復：Logo Black 與 White 兩個都必須上傳 ──
        logo_ok = bool(st.session_state.logo_black) and bool(st.session_state.logo_white)
        if logo_ok: filled_count += 1
        else:
            if not st.session_state.logo_black and not st.session_state.logo_white:
                missing_items.append("上傳 Black Logo 及 White Logo（兩個均為必填）")
            elif not st.session_state.logo_black:
                missing_items.append("上傳 Black Logo（必填）")
            else:
                missing_items.append("上傳 White Logo（必填）")
        if st.session_state.client_name.strip(): filled_count += 1
        else: missing_items.append("Client")
        if st.session_state.project_name.strip(): filled_count += 1
        else: missing_items.append("Project")
        if st.session_state.venue.strip(): filled_count += 1
        else: missing_items.append("Venue")
        if st.session_state.event_year: filled_count += 1
        if st.session_state.event_month: filled_count += 1
        if st.session_state.category: filled_count += 1
        if len(st.session_state.what_we_do) > 0: filled_count += 1
        else: missing_items.append("What we do (最少選一項)")
        if len(st.session_state.scope) > 0: filled_count += 1
        else: missing_items.append("Scope of work (最少選一項)")
        if len(st.session_state.project_photos) >= 4: filled_count += 1
        else: missing_items.append("上傳活動相片 (最少 4 張)")
        mc_answered_count = sum([1 for i in range(1, 16) if st.session_state.get(f"ans_{i}")])
        if mc_answered_count == 15: filled_count += 1
        else: missing_items.append(f"完成所有 15 題診斷 (目前進度: {mc_answered_count}/15)")
        if st.session_state.open_question_ans.strip(): filled_count += 1
        else: missing_items.append("最核心的概念 (文字不可留白)")

        final_percent = min(100, int((filled_count / 12) * 100))  # 總項目由 11 改為 12
        progress_placeholder.markdown(get_circle_progress_html(final_percent, is_dark), unsafe_allow_html=True)

        # ── Save Draft Button (visible at any progress) ──
        save_col1, save_col2 = st.columns([3, 1])
        with save_col1:
            if st.button("💾 儲存草稿到 Google Sheet (Raw_Input_DB)", use_container_width=True, help="將目前所有輸入儲存為草稿，方便日後重新載入再生成"):
                if not st.session_state.client_name.strip() or not st.session_state.project_name.strip():
                    st.warning("❗ 請至少填寫 Client 及 Project 名稱才能儲存草稿。")
                else:
                    with st.spinner("正在儲存草稿..."):
                        if save_draft_to_sheet():
                            st.success(f"✅ 草稿已儲存！ID: `{st.session_state.draft_project_id}`")
                        else:
                            st.error("❌ 儲存失敗，請檢查 Debug Terminal。")
        with save_col2:
            if st.session_state.get("draft_project_id"):
                st.markdown(f"✅ 草稿: `{st.session_state.draft_project_id}`")

        if final_percent < 100:
            with st.expander("📌 還差一點點！點擊查看未完成項目", expanded=False):
                for m in missing_items:
                    st.markdown(f"❌ **{m}**")
        else:
            st.markdown("<hr style='margin-top: 30px; margin-bottom: 30px; border: 2px solid #FF2A2A;'>", unsafe_allow_html=True)
            st.success("🎉 完美！進度達 100%！")
            if st.button("準備就緒，前往 Review & Multi-Sync 👉", type="primary", use_container_width=True):
                st.session_state.active_tab = "Review & Multi-Sync"
                st.rerun()

    elif st.session_state.active_tab == "Review & Multi-Sync":
        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        if st.button("生成六大平台對接文案"):
            with st.spinner("AI Strategist 正在構思文案..."):
                # ── 優化 B：智能壓縮診斷數據，分類「痛點」與「強項」──
                pain_points = []
                strengths = []
                for q in st.session_state.mc_questions:
                    if not isinstance(q, dict): continue
                    ans = st.session_state.get(f"ans_{q['id']}", [])
                    ans_str = "、".join(ans) if ans else "未作答"
                    q_text = q.get('question', '')
                    # 判斷答案是否含有負面/優化關鍵字
                    negative_keywords = ["優化", "改善", "不足", "欠缺", "低", "差", "未達", "問題", "挑戰", "弱", "缺乏"]
                    is_negative = any(kw in ans_str for kw in negative_keywords)
                    if is_negative:
                        pain_points.append(f"[痛點] {q_text} → {ans_str}")
                    else:
                        strengths.append(f"[強項] {q_text} → {ans_str}")

                pain_summary = "\n".join(pain_points) if pain_points else "診斷結果顯示整體表現良好，無明顯痛點。"
                strength_summary = "\n".join(strengths[:5]) if strengths else ""  # 只取前5條強項避免 token 過多

                prompt = f"""
分析專案: {st.session_state.project_name}. 生成 JSON。IG < 150 字。

【診斷痛點 (Pain Points from Diagnostic)】
{pain_summary}

【項目強項 (Top Strengths)】
{strength_summary}

請嚴格根據以上診斷數據與以下專案基本資料，歸納出痛點與解決方案，並撰寫 6_website 的雜誌級文章與其他社群文案：
### Input Data:
- [Basic Information]: Client Name: {st.session_state.client_name}, Project Name: {st.session_state.project_name}, Category: {st.session_state.category}, Scope of Work: {", ".join(st.session_state.scope)}
- [Event Details]: Event Date: {st.session_state.event_year} {st.session_state.event_month}, Venue: {st.session_state.venue}, What we do: {", ".join(st.session_state.what_we_do)}
- [Pain Point / Opportunity]: (請分析上方診斷痛點。若有明顯痛點，請用一句話精準總結；若整體偏正面，請將其轉化為「專案面臨的進階挑戰或突破機會」，字數控制在 30 字內) 補充背景: {st.session_state.open_question_ans}
- [Solution]: (請依據診斷數據與活動形式總結，說明此項目如何克服上述挑戰) 相關影片參考: {st.session_state.youtube}
"""
                res = call_gemini_sdk(prompt, is_json=True)
                if res:
                    try:
                        data = json.loads(res)
                        if isinstance(data, list) and len(data) > 0:
                            data = data[0]
                        if isinstance(data, dict):
                            # 🔧 Q&A FORMAT VALIDATION & CORRECTION
                            def fix_qa_format(content):
                                """Automatically fix Q&A format to ensure it's in Markdown with ### heading."""
                                if not content:
                                    return content

                                # Standardize the FAQ header first
                                content = re.sub(r'(<(h[1-6]|b|strong)[^>]*>\s*)?(?:Fast Recap\s*)?(?:FAQ|Q&A|Q & A|常見問題|よくある質問|快速回顧)(?:\s*</(h[1-6]|b|strong)>)?[:：]?', '### Fast Recap FAQ:', content, flags=re.IGNORECASE)

                                # Find the standardized FAQ section
                                qa_pattern = re.compile(r'(### Fast Recap FAQ:)(.*?)(?=(?:<h[1-6][^>]*>|###\s*[^#]|$))', re.DOTALL | re.IGNORECASE)
                                match = qa_pattern.search(content)

                                if match:
                                    qa_header = match.group(1)
                                    qa_raw_content = match.group(2).strip()
                                    content_before_qa = content[:match.start()]
                                    content_after_qa = content[match.end():]

                                    # Convert HTML lists to plain text lines
                                    qa_raw_content = re.sub(r'<ul[^>]*>|<ol[^>]*>|<\/ul>|<\/ol>', '', qa_raw_content, flags=re.IGNORECASE)
                                    qa_raw_content = re.sub(r'<li[^>]*>(.*?)<\/li>', r'\1\n', qa_raw_content, flags=re.IGNORECASE)
                                    qa_raw_content = re.sub(r'<p[^>]*>(.*?)<\/p>', r'\1\n', qa_raw_content, flags=re.IGNORECASE)
                                    qa_raw_content = re.sub(r'<br[^>]*>', '\n', qa_raw_content, flags=re.IGNORECASE)

                                    # Remove any remaining HTML tags
                                    qa_raw_content = re.sub(r'<[^>]*>', '', qa_raw_content)

                                    # Process lines into Qx: and Ax: format
                                    qa_lines = qa_raw_content.strip().split('\n')
                                    formatted_qa = []
                                    q_count = 1
                                    temp_q = ''

                                    for line in qa_lines:
                                        line = line.strip()
                                        if not line: continue

                                        is_q = line.upper().startswith('Q')
                                        is_a = line.upper().startswith('A')

                                        if is_q:
                                            if temp_q: # If there was a pending Q, finalize it
                                                formatted_qa.append(f"Q{q_count}: {temp_q}")
                                                q_count += 1
                                            temp_q = re.sub(r'^Q\d*[:.]?\s*', '', line, flags=re.IGNORECASE).strip()
                                        elif is_a:
                                            if temp_q:
                                                formatted_qa.append(f"Q{q_count}: {temp_q}")
                                                a_text = re.sub(r'^A\d*[:.]?\s*', '', line, flags=re.IGNORECASE).strip()
                                                formatted_qa.append(f"A{q_count}: {a_text}")
                                                q_count += 1
                                                temp_q = ''
                                        elif temp_q: # This line is a continuation of the previous Q
                                            temp_q += ' ' + line
                                    
                                    if temp_q: # Add any last pending question
                                        formatted_qa.append(f"Q{q_count}: {temp_q}")

                                    qa_content_formatted = '\n'.join(formatted_qa)

                                    return content_before_qa.strip() + '\n\n' + qa_header + '\n' + qa_content_formatted + '\n\n' + content_after_qa.strip()

                                return content
                            
                            # Apply Q&A format fixes to all language versions
                            if "6_website" in data and isinstance(data["6_website"], dict):
                                for lang in ["en", "tc", "jp"]:
                                    if lang in data["6_website"]:
                                        data["6_website"][lang] = fix_qa_format(data["6_website"][lang])
                                        log_debug(f"✅ Q&A 格式已自動修正 ({lang})", "success")
                            
                            st.session_state.ai_content = data
                            st.session_state.challenge = data.get("challenge_summary", "尚未生成")
                            st.session_state.solution = data.get("solution_summary", "尚未生成")
                            log_debug(f"✅ 文案生成成功，痛點數: {len(pain_points)}，強項數: {len(strengths)}", "success")
                            st.toast("✅ 策略與文案已成功生成！")
                            time.sleep(1)
                            st.rerun()
                    except json.JSONDecodeError as e:
                        log_debug(f"❌ 最終 JSON 解析失敗: {str(e)}", "error")
                        st.error("❌ AI 返回格式異常，請重新點擊生成按鈕再試一次。") 

        if st.session_state.ai_content:
            st.json(st.session_state.ai_content)
            if st.button("Confirm & Sync (Sheet + Slide + Drive)", type="primary", use_container_width=True):
                with st.spinner("🔄 同步中 (自動生成系統編號與日期)..."):
                    try:
                        # 🚀 新增：生成 Project_id 與 Sort_date
                        project_id, sort_date = generate_system_metadata()
                        
                        processed_imgs = []
                        for f in st.session_state.project_photos:
                            if hasattr(f, "seek"): f.seek(0) 
                            try:
                                img = Image.open(f).convert("RGB")
                                # 🚀 修復：在壓縮儲存前，先轉正
                                img = ImageOps.exif_transpose(img)
                                img.thumbnail((1600, 1600))
                                buf = io.BytesIO()
                                img.save(buf, format="JPEG", quality=85)
                                processed_imgs.append(base64.b64encode(buf.getvalue()).decode())
                            except Exception as e:
                                if hasattr(f, "seek"): f.seek(0)
                                processed_imgs.append(base64.b64encode(f.read()).decode())

                        hero_index = st.session_state.get("hero_photo_index", 0)
                        if processed_imgs and hero_index < len(processed_imgs):
                            hero_img = processed_imgs.pop(hero_index)
                            processed_imgs.insert(0, hero_img) 

                        payload = {
                            "action": "sync_project",
                            "project_id": project_id,      # 新增
                            "sort_date": sort_date,        # 新增
                            "client_name": st.session_state.client_name,
                            "project_name": st.session_state.project_name,
                            "venue": st.session_state.venue,
                            "date": f"{st.session_state.event_year} {st.session_state.event_month}",
                            "youtube": st.session_state.youtube,
                            "category": st.session_state.category, 
                            "category_what": ", ".join(st.session_state.what_we_do),
                            "scope": ", ".join(st.session_state.scope),       
                            "challenge": st.session_state.challenge,
                            "solution": st.session_state.solution,
                            "open_question": st.session_state.open_question_ans,
                            "logo_white": st.session_state.logo_white, 
                            "logo_black": st.session_state.logo_black,
                            "images": processed_imgs, 
                            "ai_content": st.session_state.ai_content
                        }
                        
                        r1 = requests.post(SHEET_SCRIPT_URL, json=payload, timeout=60)
                        r2 = requests.post(SLIDE_SCRIPT_URL, json=payload, timeout=60)
                        log_debug(f"Sync: {project_id}, Sheet {r1.status_code}, Slide {r2.status_code}", "success")
                        st.balloons()
                        st.success(f"✅ 全部數據同步對位成功！(編號: {project_id})")
                        st.session_state.sync_success = True
                        st.rerun()
                    except Exception as e: 
                        log_debug(f"Sync Fail: {str(e)}", "error")
                        st.error(f"同步失敗: {e}")

        # ── 同步成功後顯示「準備輸入下一個案例」按鈕 ──
        if st.session_state.get("sync_success", False):
            st.markdown("<br>", unsafe_allow_html=True)
            st.success("✅ 資料已成功同步至 Google Sheet！")
            st.markdown("""
                <div style='text-align:center; padding: 20px 0;'>
                    <p style='font-size: 16px; font-weight: 600; margin-bottom: 12px;'>🎉 案例已存檔完畢！</p>
                    <p style='font-size: 13px; color: #888;'>點擊下方按鈕開始輸入下一個案例，所有欄位將會清空重置。</p>
                </div>
            """, unsafe_allow_html=True)
            if st.button("➕ 準備輸入下一個案例", type="primary", use_container_width=True):
                reset_for_new_case()
                st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)

    # Debug Terminal
    st.markdown("<br><br>", unsafe_allow_html=True)
    with st.expander("🛠️ Debug Terminal & System Logs", expanded=False):
        if st.button("執行連線測試", use_container_width=True):
            with st.spinner("連線中..."):
                secret_key = st.secrets.get("GEMINI_API_KEY", "")
                if not secret_key: st.error("❌ 找不到 API Key")
                else:
                    try:
                        genai.configure(api_key=secret_key)
                        model = genai.GenerativeModel(STABLE_MODEL_ID)
                        res = model.generate_content("Reply SUCCESS")
                        st.success("✅ API Key 測試成功！")
                    except Exception as e: st.error(f"❌ 錯誤: {e}")

        logs = "".join([f"<div>[{l['time']}] {l['msg']}</div>" for l in reversed(st.session_state.get("debug_logs", []))])
        st.markdown(f"<div class='debug-terminal'>{logs}</div>", unsafe_allow_html=True)

if __name__ == "__main__": main()
