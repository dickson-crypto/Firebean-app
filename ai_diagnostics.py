import requests
import json

class AIDiagnostic:
    @staticmethod
    def get_questions(model, key, project, core_text, images):
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
        sys_prompt = """
        Role: Firebean Strategic Consultant.
        Focus: Analysis of event impact & strategic consistency.
        Method: 
        1. Hypothesis: Scenarios testing event value.
        2. Analysis: Visual/strategic execution critiques.
        Output: JSON array of 15 diagnostic questions: [{'q':'...', 'opts':['A','B','C']}]
        Return raw JSON only.
        """
        parts = [{"text": f"Project: {project}. Goal: {core_text}"}]
        if images:
            for b in images[:4]: parts.append({"inlineData": {"mimeType": "image/png", "data": b}})
        
        try:
            res = requests.post(url, json={"contents": [{"role": "user", "parts": parts}], "systemInstruction": {"parts": [{"text": sys_prompt}]}, "generationConfig": {"responseMimeType": "application/json"}}, timeout=90)
            if res.status_code == 200:
                raw = res.json()['candidates'][0]['content']['parts'][0]['text']
                return json.loads(raw.replace("```json", "").replace("```", ""))
        except: return None
