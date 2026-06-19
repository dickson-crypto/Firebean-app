# VERSION: v19.0.0 (15 MC questions driven by Firebean writing styles + photos; error surfacing)
# TIMESTAMP: 2026-06-19 13:07:00 HKT

import requests
import json

try:
    from prompts_library import WRITING_STYLES
except ImportError:
    WRITING_STYLES = [
        "Thought Leadership (Why It Matters)",
        "Contrarian / Disruptor",
        "Human-Centric / Emotional Storytelling",
        "Analytical Problem-Solver (PAS)",
        "Insider / Behind-the-Scenes",
    ]


class AIDiagnostic:
    """Generates 15 MC diagnostic questions so the user's answers can steer the
    final content toward the right editorial angle and surface strategic gaps."""

    last_error = ""

    @staticmethod
    def get_questions(key, active_model, project, core_text, images):
        if not active_model or active_model == "NONE":
            active_model = "gemini-1.5-flash"

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{active_model}:generateContent?key={key}"

        styles_str = "; ".join(WRITING_STYLES)

        sys_prompt = f"""Role: Firebean Strategic Consultant (premium HK PR & event agency).
Task: Generate EXACTLY 15 multiple-choice (MC) diagnostic questions in Traditional Chinese (繁體中文，香港用語) based on the event brief and the provided photos.

PURPOSE: The user's answers will decide which of these 5 editorial writing angles best fits the project, and will reveal strategic gaps before we write the content:
{styles_str}

METHODOLOGY (CRITICAL):
1. 假設性 (Hypothesis) — 5 to 7 questions: Propose hypothetical scenarios about the event's business impact, target audience, and which editorial angle would resonate most. Ask the user to verify the strategic direction.
2. 分析性 (Analysis) — the remaining questions: Critically analyze the visual quality of the provided photos and contrast them with the stated strategic goal. Ask sharp, execution-focused questions to find strategic gaps (e.g. hero photo choice, brand visibility, mood).

Each question MUST have exactly 3 answer options.

Format: Return ONLY a RAW JSON array of EXACTLY 15 questions in this exact structure:
[{{"q":"[Question in Traditional Chinese]", "opts":["[Option A]", "[Option B]", "[Option C]"]}}]
Do NOT wrap in markdown or ```json tags. Return the array and nothing else."""

        parts = [{"text": f"Project: {project}. Strategic Core Brief: {core_text}"}]

        # Attach up to 4 photos (base64 JPEG) so the analysis questions reference real visuals
        if images:
            for b in images[:4]:
                parts.append({"inlineData": {"mimeType": "image/jpeg", "data": b}})

        payload = {
            "contents": [{"role": "user", "parts": parts}],
            "systemInstruction": {"parts": [{"text": sys_prompt}]},
            "generationConfig": {"responseMimeType": "application/json"},
        }

        try:
            res = requests.post(url, json=payload, timeout=120)
            if res.status_code == 200:
                data = res.json()
                cands = data.get("candidates") or []
                if not cands:
                    AIDiagnostic.last_error = f"No candidate returned. Raw: {json.dumps(data)[:500]}"
                    return None
                p = cands[0].get("content", {}).get("parts", [])
                if not p:
                    reason = cands[0].get("finishReason", "UNKNOWN")
                    AIDiagnostic.last_error = f"Empty content (finishReason={reason}). Raw: {json.dumps(data)[:500]}"
                    return None
                raw = p[0].get("text", "")
                clean = raw.replace("```json", "").replace("```", "").strip()
                try:
                    questions = json.loads(clean)
                except json.JSONDecodeError as je:
                    AIDiagnostic.last_error = f"Non-JSON from model: {je}. First 300 chars: {clean[:300]}"
                    return None
                # Validate shape
                if not isinstance(questions, list) or not questions:
                    AIDiagnostic.last_error = f"Expected a list of questions, got: {str(questions)[:300]}"
                    return None
                return questions
            else:
                AIDiagnostic.last_error = f"HTTP {res.status_code} from Gemini: {res.text[:600]}"
                return None
        except Exception as e:
            AIDiagnostic.last_error = f"Request exception: {type(e).__name__}: {e}"
            return None
