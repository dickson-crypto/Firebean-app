# VERSION: v18.6.0
# TIMESTAMP: 2026-04-02 09:20:00 HKT

import requests
import json

class AIDiagnostic:
    @staticmethod
    def get_questions(key, project, core_text, images):
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-09-2025:generateContent?key={key}"
        sys_prompt = "Role: Firebean Strategic Consultant. Task: Generate 15 MC questions based on the event brief and photos. Format: JSON array of 15 diagnostic questions: [{'q':'...', 'opts':['A','B','C']}]. Return RAW JSON only."
        
        parts = [{"text": f"Project: {project}. Brief: {core_text}"}]
        
        if images:
            # FIXED: MimeType changed to image/jpeg to match our PIL compression settings
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
