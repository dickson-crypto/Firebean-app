import requests
import json

class AIDiagnostic:
    @staticmethod
    def get_questions(key, project, core_text, images):
        url = f"[https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-09-2025:generateContent?key=](https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-09-2025:generateContent?key=){key}"
        sys_prompt = "Role: Firebean Strategic Consultant. Goal: Generate 15 MC questions based on event brief and photos. Take: Strategic Hypothesis. Format: JSON array of 15 diagnostic questions: [{'q':'...', 'opts':['A','B','C']}]. Return RAW JSON only."
        parts = [{"text": f"Project: {project}. Brief: {core_text}"}]
        if images:
            for b in images[:4]: parts.append({"inlineData": {"mimeType": "image/png", "data": b}})
        
        try:
            res = requests.post(url, json={"contents": [{"parts": parts}], "systemInstruction": {"parts": [{"text": sys_prompt}]}, "generationConfig": {"responseMimeType": "application/json"}}, timeout=90)
            if res.status_code == 200:
                raw = res.json()['candidates'][0]['content']['parts'][0]['text']
                # Strip backticks if present
                clean = raw.replace("```json", "").replace("```", "").strip()
                return json.loads(clean)
        except: return None
