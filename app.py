import streamlit as st
from google import genai
import io
import base64
import time
import json

def format_faq_to_python_string(faq_list):
    """
    Safely converts a list of Q&A dicts into a standardized Python-style string for the Master DB.
    Handles both lists (from AI generation) and existing strings (from project loading).
    """
    if not faq_list:
        return "[]"
    
    # If it's already a string (e.g. from a previous load or already formatted), just return it
    if isinstance(faq_list, str):
        if faq_list.strip().startswith('['):
            return faq_list
        return "[]"

    if not isinstance(faq_list, list):
        return "[]"

    formatted_pairs = []
    for qa_pair in faq_list:
        if not isinstance(qa_pair, dict): continue
        
        # Extract keys dynamically (usually 'Q1', 'A1' etc.)
        keys = list(qa_pair.keys())
        if len(keys) < 2: continue
        q_key = keys[0]
        a_key = keys[1]
        
        # Escape single quotes and backslashes to prevent breaking the string literal
        question = str(qa_pair[q_key]).replace("\\", "\\\\").replace("'", "\\'")
        answer = str(qa_pair[a_key]).replace("\\", "\\\\").replace("'", "\\'")
        
        formatted_pairs.append(f"{{'{q_key}': '{question}', '{a_key}': '{answer}'}}")
    
    return f"[" + ", ".join(formatted_pairs) + "]"

import requests
import re
from PIL import Image, ImageDraw, ImageOps # 確保匯入 ImageOps
from datetime import datetime

# --- 1. 核心配置 ---
SHEET_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbzhcI7mHa1gDczg94SskPJDs6hECG8ohHllYz4kN4ouBs4gtxYpVJ--rP2YJm-fruy3/exec"
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
    # 如果已經載入了現有的 Project ID，優先使用它，避免重複生成
    if st.session_state.get("draft_project_id"):
        return st.session_state.draft_project_id, sort_date

    try:
        # 這裡會觸發 Google Sheet Script 的 action=get_row_count 
        count_res = requests.get(SHEET_SCRIPT_URL + "?action=get_row_count", timeout=10)
        if count_res.status_code == 200 and count_res.text.isdigit():
            next_index = int(count_res.text) + 1
        else:
            # 如果回應不是數字，使用隨機數作為備案
            import random
            next_index = random.randint(100, 999)
    except Exception as e:
        import random
        next_index = random.randint(100, 999)
    
    # 格式：FB + 年份 + 三位序號 (如 FB2026005)
    project_id = f"FB{st.session_state.event_year}{str(next_index).zfill(3)}"
    
    return project_id, sort_date

FIREBEAN_SYSTEM_PROMPT = """
You are a Lead PR Strategist and Chief Editor for a premium B2B/B2C communications agency.
Task: Transform diagnostic data into a professional PR strategy JSON.
Always return a valid JSON object with keys: challenge_summary, solution_summary, 1_google_slide, 2_facebook_post, 3_threads_post, 4_instagram_post, 5_linkedin_post, 6_website, 7_faq.

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

**CRITICAL INSTRUCTION FOR 'challenge_summary' AND 'solution_summary'**:
BOTH 'challenge_summary' AND 'solution_summary' MUST be written in ENGLISH ONLY. Do NOT use Chinese, Japanese, or any other language for these two fields.
You MUST keep the client's pain points and challenges extremely concise. Use only 1 to 2 short, punchy sentences (maximum 50 words) to define the core challenge. Do not elaborate excessively on the negative impacts.
Similarly, 'solution_summary' must be 1 to 2 concise English sentences (maximum 50 words) summarising how the challenge was resolved.

**CRITICAL INSTRUCTION FOR '6_website' (Magazine Feature Article)**:
The '6_website' key MUST be a nested JSON object containing exactly four keys: "angle_chosen", "en", "tc", and "jp".
Write a highly engaging, 500-word POST-EVENT feature article. This is a case study showcase for the agency's portfolio website, intended to impress prospective clients — NOT to promote a future event.

**IMPORTANT: EXCLUDE FAQ FROM WEBSITE ARTICLE**
The '6_website' article content MUST NOT contain any FAQ, Q&A, or "Fast Recap" section. The FAQ content is handled separately in the '7_faq' field. DO NOT repeat it in the '6_website' body text.

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
    - The Punch Line: The final paragraph must be a single, bolded, highly memorable concluding sentence about the project's impact.
    
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
    
    STRICT RULES FOR HTML:
    1. Use ONLY <h1>, <h3>, and <p> tags for main content.
    2. DO NOT use <h2>, <h4>, or any other heading tags.
    3. DO NOT use <span>, <div>, <b>, <strong>, or any style attributes (no inline colors).
    
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

**CRITICAL INSTRUCTION FOR '7_faq' (Dedicated FAQ — Separate from Website Article)**:
The '7_faq' key MUST be a nested JSON object containing exactly three keys: "en", "tc", and "jp".
This FAQ is SEPARATE from the article body in '6_website'. It will be stored in its own dedicated database column and displayed in the website sidebar.

Each language version must contain exactly 5 Q&A pairs covering:
1. What was the core challenge or brief?
2. How did the agency's creative concept address this challenge?
3. What was the most impactful or innovative element of the project?
4. How did the audience or client react to the final result?
5. What long-term value or industry benchmark did this project establish?

FAQ Formatting Rules:
- Return a simple list of 5 Q&A pairs.
- Each language must have its own 5 pairs.
- Language: 'en' (English), 'tc' (Traditional Chinese), 'jp' (Japanese).
"""

# --- 2. 輔助函數 ---
def log_debug(msg, type="info"):
    """將日誌存入 session_state"""
    ts = datetime.now().strftime("%H:%M:%S")
    if "debug_logs" not in st.session_state: st.session_state.debug_logs = []
    st.session_state.debug_logs.append(f"[{ts}] [{type.upper()}] {msg}")

def clean_field(text):
    """移除 Google Sheet 剪貼板帶來的噪音"""
    if not text: return ""
    noise = ["Basic Info", "Firebean_Master_DB", "100%", "Explore", "Summarize this data", "Explore this data"]
    for n in noise: text = text.replace(n, "")
    return text.strip()

def call_gemini_sdk(prompt, image_files=None, is_json=False):
    """呼叫 Google Gemini SDK (支援 Vision)"""
    try:
        client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
        
        contents = [FIREBEAN_SYSTEM_PROMPT, prompt]
        if image_files:
            for f in image_files:
                if hasattr(f, "seek"): f.seek(0)
                img = Image.open(f)
                img.load() # Force loading the image data to catch broken PNG errors early
                if img.mode in ('RGBA', 'P'):
                    # Create a white background image and paste the transparent image on it
                    background = Image.new("RGB", img.size, (255, 255, 255))
                    background.paste(img, mask=img.split()[3] if img.mode == 'RGBA' else None)
                    img = background
                else:
                    img = img.convert('RGB')
                # 🚀 修復：在傳給 AI 之前，先旋轉為正確方向
                img = ImageOps.exif_transpose(img)
                contents.append(img)
        
        config = None
        if is_json:
            config = genai.types.GenerateContentConfig(response_mime_type="application/json")
            
        response = client.models.generate_content(
            model=STABLE_MODEL_ID,
            contents=contents,
            config=config
        )
        return response.text
    except Exception as e:
        log_debug(f"Gemini API Error: {str(e)}", "error")
        return None

# --- 3. UI 樣式 (Neumorphism) ---
def get_is_dark_mode():
    """根據用戶設定或時間自動決定深淺色模式"""
    if st.session_state.get("user_dark_mode") is not None:
        return st.session_state.user_dark_mode
    # 預設：晚上 7 點到早上 7 點為深色模式
    hour = datetime.now().hour
    return hour >= 19 or hour < 7

def get_circle_progress_html(percent, is_dark):
    """生成圓形進度條 HTML"""
    color = "#FF2A2A" # Firebean Red
    bg = "#333" if is_dark else "#eee"
    text = "#fff" if is_dark else "#333"
    return f'''
    <div style="display: flex; flex-direction: column; align-items: center; justify-content: center;">
        <div style="position: relative; width: 100px; height: 100px; border-radius: 50%; background: conic-gradient({color} {percent*3.6}deg, {bg} 0deg); display: flex; align-items: center; justify-content: center; box-shadow: 6px 6px 12px {'#1a1d23' if is_dark else '#d1d9e6'}, -6px -6px 12px {'#2a2f38' if is_dark else '#ffffff'};">
            <div style="position: absolute; width: 80px; height: 80px; border-radius: 50%; background: {'#21252B' if is_dark else '#E0E5EC'}; display: flex; align-items: center; justify-content: center;">
                <span style="font-size: 22px; font-weight: 800; color: {text};">{percent}%</span>
            </div>
        </div>
        <span style="margin-top: 10px; font-size: 12px; font-weight: 700; color: {text};">COMPLETION</span>
    </div>
    '''

def apply_styles(is_dark):
    """套用 Neumorphism 樣式"""
    bg_color = "#21252B" if is_dark else "#E0E5EC"
    text_color = "#FFFFFF" if is_dark else "#31344B"
    card_bg = "#21252B" if is_dark else "#E0E5EC"
    input_bg = "#21252B" if is_dark else "#E0E5EC"
    input_border = "#3E4451" if is_dark else "#D1D9E6"
    shadow_dark = "#1a1d23" if is_dark else "#a3b1c6"
    shadow_light = "#2a2f38" if is_dark else "#ffffff"
    toggle_bg = "#2D3436" if is_dark else "#D1D9E6"
    toggle_border = "#3E4451" if is_dark else "#BFC9D4"

    st.markdown(f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Google+Sans:wght@400;500;700&display=swap');
        
        html, body, [data-testid="stAppViewContainer"] {{
            background-color: {bg_color} !important;
            font-family: 'Google Sans', sans-serif !important;
            color: {text_color} !important;
        }}

        /* ── Neumorphic 卡片 ── */
        .neu-card {{
            background-color: {card_bg};
            border-radius: 20px;
            padding: 25px;
            box-shadow: 9px 9px 18px {shadow_dark}, -9px -9px 18px {shadow_light};
            margin-bottom: 25px;
            border: 1px solid {input_border};
        }}

        /* ── 輸入框 ── */
        .stTextInput input, .stTextArea textarea {{
            background-color: {input_bg} !important;
            color: {text_color} !important;
            border: 1px solid {input_border} !important;
            border-radius: 12px !important;
            padding: 12px !important;
            box-shadow: inset 4px 4px 8px {shadow_dark}, inset -4px -4px 8px {shadow_light} !important;
            transition: all 0.3s ease !important;
        }}
        .stTextInput input:focus, .stTextArea textarea:focus {{
            border: 1px solid #FF2A2A !important;
            box-shadow: inset 2px 2px 4px {shadow_dark}, inset -2px -2px 4px {shadow_light} !important;
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

# --- 4. Auto-save Helper Function ---

def should_autosave():
    """檢查是否應該執行自動保存 (防抖機制，最少間隔 3 秒)"""
    current_time = time.time()
    last_save = st.session_state.get("last_autosave_time", 0)
    if current_time - last_save >= 3:
        st.session_state.last_autosave_time = current_time
        return True
    return False

def trigger_autosave_draft():
    """自動保存草稿到 Google Sheet (如果有基本信息)"""
    # Autosave removed as it is not supported by Apps Script
    pass

# --- 5. Main App ---

# ── Draft Save / Load Helper Functions ──

def init_session_state():
    """初始化所有變量"""
    defaults = {
        "active_tab": "Project Collector",
        "client_name": "", "project_name": "", "venue": "",
        "event_year": str(CURRENT_YEAR), "event_month": "JAN",
        "youtube": "", "category": WHO_WE_HELP_OPTIONS[0],
        "what_we_do": [], "scope": [], "project_photos": [],
        "mc_questions": None, "open_question_ans": "",
        "ai_content": None, "debug_logs": [], "draft_project_id": None,
        "user_dark_mode": None, "last_autosave_time": 0,
        "logo_black": None, "logo_white": None, "hero_photo_index": 0,
        "sync_success": False
    }
    for k, v in defaults.items():
        if k not in st.session_state: st.session_state[k] = v

def reset_for_new_case():
    """完全重置所有輸入，準備處理下一個案例"""
    st.session_state.client_name = ""
    st.session_state.project_name = ""
    st.session_state.venue = ""
    st.session_state.youtube = ""
    st.session_state.what_we_do = []
    st.session_state.scope = []
    st.session_state.project_photos = []
    st.session_state.mc_questions = None
    st.session_state.open_question_ans = ""
    st.session_state.ai_content = None
    st.session_state.draft_project_id = None
    st.session_state.sync_success = False
    st.session_state.active_tab = "Project Collector"
    # 清除所有動態生成的 MC 答案
    for k in list(st.session_state.keys()):
        if k.startswith("ans_") or k.startswith("chk_"):
            del st.session_state[k]

# Draft functions removed as Apps Script no longer supports them

def main():
    st.set_page_config(page_title="Firebean Brain Collector", layout="wide")
    init_session_state()

    # 自動偵測時間決定模式
    is_dark = get_is_dark_mode()
    apply_styles(is_dark)

    c1, c2, c3 = st.columns([1, 1, 0.5])
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
    with c3:
        # ── Dark Mode Toggle ──
        current_mode = st.session_state.user_dark_mode
        is_dark = get_is_dark_mode()
        
        col_dm1, col_dm2 = st.columns(2)
        with col_dm1:
            if st.button("☀️" if is_dark else "🌙", key="toggle_dark", help="切換深色/淺色模式"):
                if st.session_state.user_dark_mode is None:
                    st.session_state.user_dark_mode = not is_dark
                else:
                    st.session_state.user_dark_mode = not st.session_state.user_dark_mode
                st.rerun()
        with col_dm2:
            if st.button("🔄", key="reset_dark", help="重置為自動模式"):
                st.session_state.user_dark_mode = None
                st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    
    nav_cols = st.columns(3)
    if nav_cols[0].button("Project Collector", use_container_width=True, type="primary" if st.session_state.active_tab == "Project Collector" else "secondary"):
        st.session_state.active_tab = "Project Collector"
        st.rerun()
    if nav_cols[1].button("Review & Multi-Sync", use_container_width=True, type="primary" if st.session_state.active_tab == "Review & Multi-Sync" else "secondary"):
        st.session_state.active_tab = "Review & Multi-Sync"
        st.rerun()
    if nav_cols[2].button("📂 Load Project", use_container_width=True, type="primary" if st.session_state.active_tab == "Load Project" else "secondary"):
        st.session_state.active_tab = "Load Project"
        st.rerun()

    st.markdown("<hr style='margin-top: 5px; margin-bottom: 20px;'>", unsafe_allow_html=True)

    # --- TAB 分頁內容 ---
    if st.session_state.active_tab == "Project Collector":

        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            ub = st.file_uploader("Black Logo ✱ (Required)", type=['png'], key="l_b")
            if ub is not None: 
                # 確保是乾淨的 base64 字符串
                st.session_state.logo_black = base64.b64encode(ub.read()).decode('utf-8')
            
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
                # 確保是乾淨的 base64 字符串
                st.session_state.logo_white = base64.b64encode(uw.read()).decode('utf-8')
                
            if st.session_state.logo_white:
                st.markdown(f'''
                    <div style="margin-top: -10px; margin-bottom: 10px; padding: 10px; border: 1px dashed #ccc; border-radius: 8px; display: inline-block; background-color: #2D3436; text-align: center;">
                        <span style="font-size: 10px; color: #aaa; display: block; margin-bottom: 5px;">Preview</span>
                        <img src="data:image/png;base64,{st.session_state.logo_white}" style="max-height: 60px; max-width: 150px; object-fit: contain;">
                    </div>
                ''', unsafe_allow_html=True)

        b1, b2, b3 = st.columns(3)
        # 🚀 使用 key 綁定 session_state，避免輸入時 refresh 丟失
        st.session_state.client_name = clean_field(b1.text_input("Client", value=st.session_state.client_name, key="client_name_input"))
        st.session_state.project_name = clean_field(b2.text_input("Project", value=st.session_state.project_name, key="project_name_input"))
        st.session_state.venue = clean_field(b3.text_input("Venue", value=st.session_state.venue, key="venue_input"))

        b4, b5, b6 = st.columns(3)
        y_idx = YEAR_OPTIONS.index(st.session_state.event_year) if st.session_state.event_year in YEAR_OPTIONS else 0
        m_idx = MONTH_OPTIONS.index(st.session_state.event_month) if st.session_state.event_month in MONTH_OPTIONS else 1
        st.session_state.event_year = b4.selectbox("Event Year", YEAR_OPTIONS, index=y_idx, key="year_select")
        st.session_state.event_month = b5.selectbox("Event Month", MONTH_OPTIONS, index=m_idx, key="month_select")
        st.session_state.youtube = b6.text_input("YouTube Link (Optional)", value=st.session_state.youtube, key="youtube_input")

        st.markdown("<hr style='margin-top: 10px; margin-bottom: 10px;'>", unsafe_allow_html=True)

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

                st.session_state.open_question_ans = st.text_area("最核心的概念？", value=st.session_state.open_question_ans, key="open_question_input")
            st.markdown('</div>', unsafe_allow_html=True)

        with cr:
            st.markdown('<div class="neu-card">', unsafe_allow_html=True)
            f_up = st.file_uploader("Upload 4-8 Photos", accept_multiple_files=True, key="photo_uploader")
            if f_up: st.session_state.project_photos = f_up
            
            if st.session_state.project_photos:
                st.markdown("##### 📸 Photo Preview & Select Hero Banner")
                
                photo_names = [f"Photo {i+1}" for i in range(len(st.session_state.project_photos))]
                st.session_state.hero_photo_index = st.radio(
                    "請選擇一張作為 Website 的 Hero Banner (這張將會被設定為 Hero Photo Link):",
                    options=range(len(st.session_state.project_photos)),
                    format_func=lambda x: photo_names[x],
                    horizontal=True,
                    key="hero_radio"
                )
                
                g_cols = st.columns(4)
                for i, f in enumerate(st.session_state.project_photos):
                    with g_cols[i%4]:
                        try: 
                            if hasattr(f, "seek"): f.seek(0)
                            img = Image.open(f)
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

        final_percent = min(100, int((filled_count / 12) * 100))
        progress_placeholder.markdown(get_circle_progress_html(final_percent, is_dark), unsafe_allow_html=True)

        # ── Draft ID Status (Automatic) ──
        if st.session_state.get("draft_project_id"):
            st.markdown(f"✅ **Auto-save Active**: Draft ID `{st.session_state.draft_project_id}`")

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
        
        # --- Gemini API Key 連線測試 ---
        with st.expander("🔑 Gemini API Key 連線測試", expanded=False):
            if st.button("測試 API Key 連線", key="test_api_key"):
                try:
                    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
                    test_response = client.models.generate_content(
                        model=STABLE_MODEL_ID,
                        contents=["Reply with exactly: OK"]
                    )
                    if test_response and test_response.text:
                        st.success(f"✅ API Key 連線成功！模型回應：{test_response.text.strip()[:50]}")
                    else:
                        st.error("❌ API Key 連線失敗：模型無回應")
                except Exception as e:
                    err_msg = str(e)
                    if "API_KEY_INVALID" in err_msg or "PERMISSION_DENIED" in err_msg:
                        st.error(f"❌ API Key 無效或已被撤銷：{err_msg[:200]}")
                    elif "leaked" in err_msg.lower():
                        st.error(f"❌ API Key 已被 Google 標記為洩露，請立即更換新 Key！")
                    else:
                        st.error(f"❌ 連線錯誤：{err_msg[:200]}")
        
        if st.button("生成六大平台對接文案"):
            with st.spinner("AI Strategist 正在構思文案..."):
                pain_points = []
                strengths = []
                for q in st.session_state.mc_questions:
                    if not isinstance(q, dict): continue
                    ans = st.session_state.get(f"ans_{q['id']}", [])
                    ans_str = "、".join(ans) if ans else "未作答"
                    q_text = q.get('question', '')
                    negative_keywords = ["優化", "改善", "不足", "欠缺", "低", "差", "未達", "問題", "挑戰", "弱", "缺乏"]
                    is_negative = any(kw in ans_str for kw in negative_keywords)
                    if is_negative:
                        pain_points.append(f"[痛點] {q_text} → {ans_str}")
                    else:
                        strengths.append(f"[強項] {q_text} → {ans_str}")

                pain_summary = "\n".join(pain_points) if pain_points else "診斷結果顯示整體表現良好，無明顯痛點。"
                strength_summary = "\n".join(strengths[:5]) if strengths else ""

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
                        # Clean up potential markdown code blocks
                        clean_res = res.strip()
                        if clean_res.startswith("```json"):
                            clean_res = clean_res[7:]
                        if clean_res.startswith("```"):
                            clean_res = clean_res[3:]
                        if clean_res.endswith("```"):
                            clean_res = clean_res[:-3]
                        clean_res = clean_res.strip()
                        
                        # 🛠️ Robust JSON Repair Logic
                        def repair_json(s):
                            s = s.strip()
                            # Remove Markdown code blocks
                            if s.startswith("```"):
                                s = re.sub(r'^```(?:json)?\s*', '', s)
                                s = re.sub(r'\s*```$', '', s)
                            s = s.strip()
                            # Basic fixes for common AI mistakes
                            s = re.sub(r',\s*}', '}', s) # Trailing commas in dicts
                            s = re.sub(r',\s*]', ']', s) # Trailing commas in lists
                            # Fix common unescaped newlines inside strings
                            def fix_newlines(match):
                                return match.group(0).replace('\n', '\\n')
                            s = re.sub(r'":\s*"[^"]*"', fix_newlines, s)
                            return s

                        try:
                            clean_res = repair_json(res)
                            data = json.loads(clean_res)
                            if isinstance(data, list) and len(data) > 0:
                                data = data[0]
                            if isinstance(data, dict):
                                st.session_state.ai_content = data
                                st.rerun()
                            else:
                                raise ValueError("Result is not a dictionary")
                        except Exception as e:
                            # 🚨 Final fallback: Regex extraction for critical fields if JSON is totally broken
                            st.warning("⚠️ JSON 格式有誤，正在嘗試手動修復...")
                            log_debug(f"JSON Parse Error: {str(e)}", "warning")
                            
                            fallback_data = {
                                "challenge_summary": re.search(r'"challenge_summary":\s*"([^"]*)"', res).group(1) if re.search(r'"challenge_summary":\s*"([^"]*)"', res) else "",
                                "solution_summary": re.search(r'"solution_summary":\s*"([^"]*)"', res).group(1) if re.search(r'"solution_summary":\s*"([^"]*)"', res) else "",
                                "6_website": {"en": "", "tc": "", "jp": ""},
                                "7_faq": {"en": "[]", "tc": "[]", "jp": "[]"}
                            }
                            # Try to extract more if possible
                            for lang in ["en", "tc", "jp"]:
                                match = re.search(f'"{lang}":\\s*"([^"]*)"', res)
                                if match: fallback_data["6_website"][lang] = match.group(1)
                            
                            if fallback_data["challenge_summary"]:
                                st.session_state.ai_content = fallback_data
                                st.success("✅ 已從損壞的數據中救回部分內容，請檢查後再同步。")
                                st.rerun()
                            else:
                                st.error(f"❌ AI 返回數據格式嚴重錯誤，無法修復：{str(e)}")
                                log_debug(f"Critical JSON Error: {res}", "error")
                    except Exception as outer_err:
                        st.error(f"❌ AI 處理發生非預期錯誤：{str(outer_err)}")
                        log_debug(f"AI Outer Error: {str(outer_err)}", "error")

        if st.session_state.ai_content:
            st.markdown("### 📋 Review Content")
            c = st.session_state.ai_content
            
            # --- Challenge & Solution Summary ---
            col_s1, col_s2 = st.columns(2)
            with col_s1:
                st.session_state.ai_content["challenge_summary"] = st.text_area("Challenge Summary (EN)", c.get("challenge_summary", ""))
            with col_s2:
                st.session_state.ai_content["solution_summary"] = st.text_area("Solution Summary (EN)", c.get("solution_summary", ""))

            # --- 6_website ---
            st.markdown("#### 🌐 Website Article (Interleaved Layout)")
            web = c.get("6_website", {})
            st.info(f"Selected Angle: {web.get('angle_chosen', 'Standard')}")
            
            w_tab_en, w_tab_tc, w_tab_jp = st.tabs(["English", "繁中", "日本語"])
            with w_tab_en:
                st.session_state.ai_content["6_website"]["en"] = st.text_area("Article (EN)", web.get("en", ""), height=300)
            with w_tab_tc:
                st.session_state.ai_content["6_website"]["tc"] = st.text_area("Article (TC)", web.get("tc", ""), height=300)
            with w_tab_jp:
                st.session_state.ai_content["6_website"]["jp"] = st.text_area("Article (JP)", web.get("jp", ""), height=300)

            # --- 7_faq ---
            st.markdown("#### ❓ Sidebar FAQ (Structured Data)")
            faq = c.get("7_faq", {})
            f_tab_en, f_tab_tc, f_tab_jp = st.tabs(["FAQ EN", "FAQ TC", "FAQ JP"])
            with f_tab_en:
                faq_en_val = faq.get("en", "")
                faq_en_str = json.dumps(faq_en_val, ensure_ascii=False) if isinstance(faq_en_val, (list, dict)) else str(faq_en_val)
                st.session_state.ai_content["7_faq"]["en"] = st.text_area("FAQ List (EN)", faq_en_str, height=200)
            with f_tab_tc:
                faq_tc_val = faq.get("tc", "")
                faq_tc_str = json.dumps(faq_tc_val, ensure_ascii=False) if isinstance(faq_tc_val, (list, dict)) else str(faq_tc_val)
                st.session_state.ai_content["7_faq"]["tc"] = st.text_area("FAQ List (TC)", faq_tc_str, height=200)
            with f_tab_jp:
                faq_jp_val = faq.get("jp", "")
                faq_jp_str = json.dumps(faq_jp_val, ensure_ascii=False) if isinstance(faq_jp_val, (list, dict)) else str(faq_jp_val)
                st.session_state.ai_content["7_faq"]["jp"] = st.text_area("FAQ List (JP)", faq_jp_str, height=200)

            # --- Social Media ---
            st.markdown("#### 📱 Social Media Posts")
            col_sm1, col_sm2 = st.columns(2)
            with col_sm1:
                st.session_state.ai_content["2_facebook_post"] = st.text_area("Facebook", c.get("2_facebook_post", ""), height=150)
                st.session_state.ai_content["3_threads_post"] = st.text_area("Threads", c.get("3_threads_post", ""), height=100)
            with col_sm2:
                st.session_state.ai_content["4_instagram_post"] = st.text_area("Instagram", c.get("4_instagram_post", ""), height=150)
                st.session_state.ai_content["5_linkedin_post"] = st.text_area("LinkedIn", c.get("5_linkedin_post", ""), height=150)

            st.markdown("<hr style='border: 2px solid #FF2A2A;'>", unsafe_allow_html=True)
            
            if st.button("🚀 Confirm & Sync ALL to Master DB", type="primary", use_container_width=True):
                with st.spinner("正在將數據與圖片同步至 Google Master DB..."):
                    if trigger_full_sync():
                        st.session_state.sync_success = True
                        st.balloons()
                        st.success("🎉 同步成功！所有數據與圖片已安全存入 Master DB。")
                        st.info("💡 點擊上方 🏠 HOME 按鈕即可重置表單，開始處理下一個案例。")
                    else:
                        st.error("❌ 同步失敗，請查看 Debug Terminal。")
        st.markdown('</div>', unsafe_allow_html=True)

    # --- Load Project Tab ---
    elif st.session_state.active_tab == "Load Project":
        st.markdown('<div class="neu-card">', unsafe_allow_html=True)
        st.markdown("### 📂 載入已儲存的項目 (Load Existing Project)")
        st.info("輸入 **Project ID**（例如：`FB2026MAR001`）或 **Client Name** 的部分關鍵字，系統會從 Master DB 搜尋並載入所有資料。")

        load_col1, load_col2 = st.columns([3, 1])
        with load_col1:
            search_query = st.text_input("🔍 Project ID 或 Client Name", placeholder="例如：FB2026MAR001 或 Agnès b.", key="load_search_query")
        with load_col2:
            st.markdown("<br>", unsafe_allow_html=True)
            do_search = st.button("🔎 搜尋並載入", type="primary", use_container_width=True)

        if do_search and search_query.strip():
            query = search_query.strip()
            with st.spinner(f"正在搜尋 '{query}'..."):
                try:
                    # 1. First, get the list of all projects to support keyword search
                    list_resp = requests.post(SHEET_SCRIPT_URL, json={"action": "get_raw_input_list"}, timeout=30)
                    list_result = list_resp.json()
                    
                    if list_result.get("success"):
                        projects = list_result.get("projects", [])
                        # Filter by Project ID (exact) or Client Name (keyword)
                        matches = [p for p in projects if query.upper() == p['project_id'].upper() or query.lower() in p['client'].lower() or query.lower() in p['project_name'].lower()]
                        
                        if not matches:
                            st.error(f"❌ 找不到與 '{query}' 相關的項目。")
                        elif len(matches) > 1:
                            st.warning(f"🔍 找到多個相符項目，請選擇一個：")
                            for m in matches:
                                if st.button(f"📂 載入: {m['project_id']} — {m['client']} / {m['project_name']}", key=f"load_{m['project_id']}"):
                                    # This will trigger the next step in the next run
                                    st.session_state.load_target_id = m['project_id']
                                    st.rerun()
                        else:
                            # Exactly one match, load it directly
                            st.session_state.load_target_id = matches[0]['project_id']
                            st.rerun()
                    else:
                        st.error(f"❌ 搜尋失敗：{list_result.get('error', '未知錯誤')}")
                except Exception as load_err:
                    st.error(f"❌ 搜尋發生例外：{str(load_err)}")
                    log_debug(f"❌ Load Project Search 例外: {str(load_err)}", "error")

        # Handle the actual loading of project details if a target ID is set
        if st.session_state.get("load_target_id"):
            target_id = st.session_state.pop("load_target_id")
            with st.spinner(f"正在載入項目 {target_id}..."):
                try:
                    resp = requests.post(
                        SHEET_SCRIPT_URL,
                        json={"action": "get_raw_input_details", "project_id": target_id},
                        timeout=30
                    )
                    result = resp.json()
                    if result.get("success"):
                        d = result["project"]
                        # Load all fields into session state
                        st.session_state.client_name = d.get("client", "")
                        st.session_state.project_name = d.get("project_name", "")
                        st.session_state.venue = d.get("venue", "")
                        st.session_state.youtube = d.get("youtube", "")
                        
                        # Parse event date (e.g. "2024-APR")
                        date_str = d.get("date", "")
                        if "-" in date_str:
                            y, m = date_str.split("-")
                            if y in YEAR_OPTIONS: st.session_state.event_year = y
                            if m.upper() in MONTH_OPTIONS: st.session_state.event_month = m.upper()

                        # Parse category
                        cat = d.get("category", WHO_WE_HELP_OPTIONS[0])
                        st.session_state.category = cat if cat in WHO_WE_HELP_OPTIONS else WHO_WE_HELP_OPTIONS[0]
                        
                        # Parse what_we_do (comma-separated string)
                        cat_what_str = d.get("what_we_do", "")
                        st.session_state.what_we_do = [x.strip() for x in cat_what_str.split(",") if x.strip() in WHAT_WE_DO_OPTIONS] if cat_what_str else []
                        
                        # Parse scope (comma-separated string)
                        scope_str = d.get("scope", "")
                        st.session_state.scope = [x.strip() for x in scope_str.split(",") if x.strip() in SOW_OPTIONS] if scope_str else []
                        
                        st.session_state.open_question_ans = d.get("open_question", "")
                        st.session_state.draft_project_id = d.get("project_id", "")
                        
                        # Reconstruct AI content object for Review tab
                        ai_data = {
                            "challenge_summary": d.get("challenge", ""),
                            "solution_summary": d.get("solution", ""),
                            "1_google_slide": d.get("google_slide", ""),
                            "2_facebook_post": d.get("facebook", ""),
                            "3_threads_post": d.get("threads", ""),
                            "4_instagram_post": d.get("instagram", ""),
                            "5_linkedin_post": d.get("linkedin", ""),
                            "6_website": {
                                "en": d.get("web_en", ""),
                                "tc": d.get("web_tc", ""),
                                "jp": d.get("web_jp", "")
                            },
                            "7_faq": {
                                "en": d.get("faq_en", ""),
                                "tc": d.get("faq_tc", ""),
                                "jp": d.get("faq_jp", "")
                            }
                        }
                        st.session_state.ai_content = ai_data
                        
                        log_debug(f"✅ 已成功載入項目: {d.get('project_id')} — {d.get('client')}", "success")
                        st.success(f"✅ 成功載入：**{d.get('client')}** — {d.get('project_name')} (`{d.get('project_id')}`）")
                        st.info("💡 資料已載入！你可以切換到 **Project Collector** 修改基本資料，或直接到 **Review & Multi-Sync** 編輯 AI 文案後重新 Sync。")
                        st.warning("⚠️ 注意：Logo 和照片需要重新上傳，因為圖片不儲存在 Master DB 的文字欄位中。")
                    else:
                        st.error(f"❌ 載入失敗：{result.get('error', '未知錯誤')}")
                        log_debug(f"❌ Load Project Details 失敗: {result.get('error')}", "error")
                except Exception as load_err:
                    st.error(f"❌ 載入發生例外：{str(load_err)}")
                    log_debug(f"❌ Load Project Details 例外: {str(load_err)}", "error")

        # Show currently loaded project info
        if st.session_state.get("draft_project_id"):
            st.markdown("---")
            st.markdown(f"**目前已載入項目：** `{st.session_state.draft_project_id}` — {st.session_state.client_name} / {st.session_state.project_name}")
            col_nav1, col_nav2 = st.columns(2)
            if col_nav1.button("✏️ 前往 Project Collector 修改", use_container_width=True):
                st.session_state.active_tab = "Project Collector"
                st.rerun()
            if col_nav2.button("📝 前往 Review & Multi-Sync 編輯文案", use_container_width=True):
                st.session_state.active_tab = "Review & Multi-Sync"
                st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)

    # --- Debug Terminal (Collapsible) ---
    with st.expander("🛠️ Debug Terminal & System Logs", expanded=False):
        logs = st.session_state.get("debug_logs", [])
        log_text = "\n".join(logs) if logs else "No logs yet."
        st.markdown(f'<div class="debug-terminal">{log_text}</div>', unsafe_allow_html=True)

def trigger_full_sync():
    """執行完整同步到 Master DB (含圖片與 FAQ)"""
    try:
        # 1. 生成元數據
        project_id, sort_date = generate_system_metadata()
        
        # 2. 處理圖片 (base64)
        processed_imgs = []
        if st.session_state.project_photos:
            for i, f in enumerate(st.session_state.project_photos):
                if hasattr(f, "seek"): f.seek(0)
                try:
                    # Fix broken PNG error by handling image formats properly
                    img = Image.open(f)
                    img.load() # Force loading the image data to catch broken PNG errors early
                    if img.mode in ('RGBA', 'P'):
                        # Create a white background image and paste the transparent image on it
                        background = Image.new("RGB", img.size, (255, 255, 255))
                        background.paste(img, mask=img.split()[3] if img.mode == 'RGBA' else None)
                        img = background
                    else:
                        img = img.convert('RGB')
                    img = ImageOps.exif_transpose(img)
                    img.thumbnail((1200, 1200)) # Smaller size for better sync performance
                    buf = io.BytesIO()
                    img.save(buf, format="JPEG", quality=75) # Slightly lower quality for smaller payload
                    processed_imgs.append(base64.b64encode(buf.getvalue()).decode())
                except Exception as img_err:
                    log_debug(f"Image processing error: {str(img_err)}", "warning")
                    if hasattr(f, "seek"): f.seek(0)
                    processed_imgs.append(base64.b64encode(f.read()).decode())

        # 3. 準備 Payload
        ai = st.session_state.ai_content if st.session_state.ai_content else {}
        web = ai.get("6_website", {})
        faq = ai.get("7_faq", {})
        
        # 確保即使沒有點擊 AI 生成，社交媒體欄位也有預設值，避免傳送 None 導致錯誤
        if not ai:
            ai = {
                "1_google_slide": "",
                "2_facebook_post": "",
                "3_threads_post": "",
                "4_instagram_post": "",
                "5_linkedin_post": "",
                "6_website": {"en": "", "tc": "", "jp": ""},
                "7_faq": {"en": "", "tc": "", "jp": ""},
                "challenge_summary": "",
                "solution_summary": ""
            }
        
        # 準備 DATE 欄位 (e.g. "MAR 2026")
        display_date = f"{st.session_state.event_month} {st.session_state.event_year}"
        
        payload = {
            "action": "sync_project",
            "client_name": st.session_state.client_name,
            "project_name": st.session_state.project_name,
            "project_id": project_id,
            "sort_date": sort_date,
            "date": display_date,
            "venue": st.session_state.venue,
            "event_year": st.session_state.event_year,
            "event_month": st.session_state.event_month,
            "youtube": st.session_state.youtube,
            "category": st.session_state.category,
            "what_we_do": st.session_state.what_we_do,  # Fixed: changed category_what to what_we_do to match Apps Script
            "scope": st.session_state.scope,            # Fixed: pass array directly, Apps Script handles join
            "open_question": st.session_state.open_question_ans,
            
            "challenge": ai.get("challenge_summary", ""),
            "solution": ai.get("solution_summary", ""),
            
            "faq_en": format_faq_to_python_string(faq.get("en", [])),
            "faq_tc": format_faq_to_python_string(faq.get("tc", [])),
            "faq_jp": format_faq_to_python_string(faq.get("jp", [])),
            
            "ai_content": ai,
            
            "logo_black": st.session_state.logo_black,
            "logo_white": st.session_state.logo_white,
            "hero_photo_index": st.session_state.hero_photo_index, # Fixed: changed hero_index to hero_photo_index
            "images": processed_imgs
        }
        
        log_debug(f"📤 Sending payload to Master DB (Payload size: {len(json.dumps(payload))/1024:.1f} KB)...", "info")
        r = requests.post(SHEET_SCRIPT_URL, json=payload, timeout=120)
        
        # Handle both JSON response and plain text "Sync Success" from Apps Script
        is_success = False
        if r.status_code == 200:
            if "Sync Success" in r.text:
                is_success = True
            else:
                try:
                    resp_json = r.json()
                    is_success = resp_json.get("success") == True or resp_json.get("status") == "success"
                    if not is_success:
                        log_debug(f"❌ Apps Script error: {resp_json.get('error', 'Unknown error')}", "error")
                except:
                    pass
        else:
            log_debug(f"❌ HTTP Error {r.status_code}: {r.text[:200]}", "error")
        
        if is_success:
            # 觸發 Google Slide 生成
            try:
                # 傳送 base64 logo 和照片給 Slide Script (v3.7 格式)
                slide_payload = {
                    "client_name": st.session_state.client_name,
                    "project_name": st.session_state.project_name,
                    "category": st.session_state.category,
                    "date": display_date,
                    "venue": st.session_state.venue,
                    "scope": ", ".join(st.session_state.scope),
                    "challenge": ai.get("challenge_summary", ""),
                    "solution": ai.get("solution_summary", ""),
                    "logo_white": st.session_state.logo_white or "",
                    "logo_black": st.session_state.logo_black or "",
                    "images": processed_imgs if processed_imgs else []
                }
                slide_r = requests.post(SLIDE_SCRIPT_URL, json=slide_payload, timeout=120)
                if slide_r.status_code == 200:
                    resp_text = slide_r.text
                    if "Success" in resp_text or "success" in resp_text:
                        log_debug(f"✅ Google Slide 已生成成功", "success")
                    else:
                        log_debug(f"⚠️ Slide 生成回應: {resp_text[:200]}", "warning")
            except Exception as slide_err:
                log_debug(f"⚠️ Slide 生成失敗 (不影響主要同步): {str(slide_err)}", "warning")
            
            # 儲存 Raw Data 到 GitHub
            try:
                # 準備要儲存的完整原始資料
                raw_data = {
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "project_id": project_id,
                    "client_name": st.session_state.client_name,
                    "project_name": st.session_state.project_name,
                    "venue": st.session_state.venue,
                    "event_year": st.session_state.event_year,
                    "event_month": st.session_state.event_month,
                    "category": st.session_state.category,
                    "what_we_do": st.session_state.what_we_do,
                    "scope": st.session_state.scope,
                    "youtube": st.session_state.youtube,
                    "open_question": st.session_state.open_question_ans,
                    "mc_questions": st.session_state.mc_questions,
                    "mc_answers": {i: st.session_state.get(f"ans_{i}", []) for i in range(1, 16)},
                    "ai_content": st.session_state.ai_content
                }
                
                # 建立臨時檔案
                import tempfile
                import os
                import subprocess
                
                with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as temp_file:
                    json.dump(raw_data, temp_file, ensure_ascii=False, indent=2)
                    temp_path = temp_file.name
                
                # 取得當前年份和月份作為資料夾結構
                year_month = time.strftime("%Y-%m")
                github_path = f"raw_data/{year_month}/{project_id}.json"
                
                # 寫入一個簡單的 bash script 來執行 gh api 呼叫 (避免引號跳脫問題)
                script_content = f'''#!/bin/bash
REPO="dickson-crypto/Firebean-app"
FILE_PATH="{github_path}"
MESSAGE="Save raw data for {project_id}"
CONTENT=$(base64 -w 0 "{temp_path}")

# 檢查檔案是否已存在，以取得 SHA
SHA=$(gh api repos/$REPO/contents/$FILE_PATH -q .sha 2>/dev/null)

if [ -z "$SHA" ]; then
  # 建立新檔案
  gh api -X PUT repos/$REPO/contents/$FILE_PATH -f message="$MESSAGE" -f content="$CONTENT" > /dev/null
else
  # 更新現有檔案
  gh api -X PUT repos/$REPO/contents/$FILE_PATH -f message="$MESSAGE" -f content="$CONTENT" -f sha="$SHA" > /dev/null
fi
'''
                script_path = "/tmp/upload_raw_data.sh"
                with open(script_path, "w") as f:
                    f.write(script_content)
                
                os.chmod(script_path, 0o755)
                subprocess.run([script_path], check=True)
                
                log_debug(f"✅ 原始資料已成功備份至 GitHub ({github_path})", "success")
                
            except Exception as backup_err:
                log_debug(f"⚠️ 原始資料備份至 GitHub 失敗: {str(backup_err)}", "warning")
                
        return is_success
    except Exception as e:
        log_debug(f"❌ 同步失敗: {str(e)}", "error")
        return False

def fill_dummy_data():
    """一鍵填充測試數據"""
    st.session_state.client_name = "Agnès b. / New Balance / JILL STUART"
    st.session_state.project_name = "ABC Online Conference 2026"
    st.session_state.venue = "101 Studio"
    st.session_state.event_year = "2026"
    st.session_state.event_month = "MAR"
    st.session_state.youtube = "https://youtube.com/test"
    st.session_state.category = "LIFESTYLE & CONSUMER"
    st.session_state.what_we_do = ["SOCIAL & CONTENT", "PR & MEDIA", "INTERACTIVE & TECH"]
    st.session_state.scope = ["Event Planning", "Concept Development", "Social Media Management"]
    st.session_state.open_question_ans = "這是一個跨品牌的高端線上發佈會，旨在展示 2026 春夏系列。"
    st.info("✅ 已填充測試數據。")

if __name__ == "__main__":
    main()
