# VERSION: v18.6.5 (Advanced Diagnostic Methodology & Traditional Chinese)
# TIMESTAMP: 2026-04-06 08:55:00 HKT

import requests
import json

class AIDiagnostic:
    @staticmethod
    def get_questions(key, active_model, project, core_text, images):
        # Fallback in case active_model wasn't passed correctly
        if not active_model or active_model == "NONE":
            active_model = "gemini-1.5-flash"
            
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{active_model}:generateContent?key={key}"
        
        # UPDATED: Enforcing Traditional Chinese AND the v1.9 Hypothesis/Analysis Methodology
        sys_prompt = """Role: Firebean Strategic Consultant. 
        Task: Generate exactly 15 Multiple Choice (MC) diagnostic questions in Traditional Chinese (繁體中文) based on the event brief and photos.
        
        METHODOLOGY (CRITICAL):
        1. 假設性 (Hypothesis) - 5 to 7 questions: Propose hypothetical scenarios regarding the event's business impact and audience influence. Ask the user to verify the strategic direction.
        2. 分析性 (Analysis) - Remaining questions: Critically analyze the visual quality of the provided photos and contrast them with the stated "Strategic Core" goal. Ask sharp, execution-focused questions to find strategic gaps.
        
        Format: Return ONLY a RAW JSON array of 15 diagnostic questions matching this exact structure: 
        [{"q":"[Question in Traditional Chinese]", "opts":["[Option A]", "[Option B]", "[Option C]"]}]. 
        Do not wrap in markdown or ```json tags."""
        
        parts = [{"text": f"Project: {project}. Strategic Core Brief: {core_text}"}]
        
        if images:
            for b in images[:4]: 
                parts.append({"inlineData": {"mimeType": "image/jpeg", "data": b}})
        
        payload = {
            "contents": [{"role": "user", "parts": parts}],
            "systemInstruction": {"parts": [{"text": sys_prompt}]},
            "generationConfig": {"responseMimeType": "application/json"}
        }
        
        try:
            res = requests.post(url, json=payload, timeout=90)
            if res.status_code == 200:
                raw = res.json()['candidates'][0]['content']['parts'][0]['text']
                clean = raw.replace("```json", "").replace("```", "").strip()
                return json.loads(clean)
            else:
                return None
        except Exception: 
            return None
