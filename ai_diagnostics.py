# VERSION: v19.2.0 (PROVIDER FALLBACK: questions now go through ai_backend — Google Gemini first, automatic fal.ai fallback when Google has no credit / is rate-limited / the model is retired)
# TIMESTAMP: 2026-11-02 12:00:00 HKT

import requests
import json
import ai_backend

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
    provider = ""  # "google" or "fal" — which provider actually answered last

    @staticmethod
    def get_questions(key, active_model, project, core_text, images):
        if not active_model or active_model == "NONE":
            active_model = "gemini-flash-latest"  # was gemini-1.5-flash (RETIRED, 404)

        styles_str = "; ".join(WRITING_STYLES)

        sys_prompt = f"""Role: Firebean Strategic Consultant (premium HK PR & event agency).
Task: Generate EXACTLY 15 multiple-choice (MC) diagnostic questions in Traditional Chinese (繁體中文，香港用語) based on the event brief and the provided photos.

PURPOSE: The user's answers will decide which of these 5 editorial writing angles best fits the project, and will reveal strategic gaps before we write the content:
{styles_str}

METHODOLOGY (CRITICAL):
1. 假設性 (Hypothesis) — 5 to 7 questions: Propose hypothetical scenarios about the event's business impact, target audience, and which editorial angle would resonate most. Ask the user to verify the strategic direction.
2. 分析性 (Analysis) — the remaining questions: Critically analyze the visual quality of the provided photos and contrast them with the stated strategic goal. Ask sharp, execution-focused questions to find strategic gaps (e.g. hero photo choice, brand visibility, mood).

Each question MUST have exactly 3 answer options.

MULTI-SELECT (IMPORTANT): The user is allowed to choose MORE THAN ONE option per question. Therefore design the options so that they can sensibly co-exist (the user may pick one, two, or all three). Avoid mutually-exclusive yes/no framings; prefer options that represent complementary angles, priorities, or attributes the user can combine. Where helpful, phrase the question so multiple selections make sense (e.g. 「以下哪些…（可多選）」).

Format: Return ONLY a RAW JSON array of EXACTLY 15 questions in this exact structure:
[{{"q":"[Question in Traditional Chinese]", "opts":["[Option A]", "[Option B]", "[Option C]"]}}]
Do NOT wrap in markdown or ```json tags. Return the array and nothing else."""

        payload_text = f"Project: {project}. Strategic Core Brief: {core_text}"
        # Route through ai_backend: Google Gemini first, automatic fal.ai fallback
        # (fal-ai/any-llm/vision) when Google has no credit / is rate-limited /
        # the model is retired. Photos are forwarded as base64 — fal accepts data URLs.
        raw, reason, err, provider = ai_backend.generate(
            key, active_model, sys_prompt, payload_text,
            images=(images or [])[:4], max_tokens=8192, temperature=0.9, json_mode=True,
        )
        AIDiagnostic.provider = provider
        if raw is None:
            AIDiagnostic.last_error = err or "Unknown generation error."
            return None
        questions = ai_backend.parse_json_loose(raw)
        if questions is None:
            AIDiagnostic.last_error = (
                f"Non-JSON from model (provider={provider}). First 300 chars: "
                f"{ai_backend._strip_fences(raw)[:300]}"
            )
            return None
        # Validate shape
        if not isinstance(questions, list) or not questions:
            AIDiagnostic.last_error = f"Expected a list of questions, got: {str(questions)[:300]}"
            return None
        return questions
