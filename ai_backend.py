# ai_backend.py — provider-agnostic AI caller for the Firebean Portal
# VERSION: v1.0.0
# TIMESTAMP: 2026-11-02
# WHY: The portal's Gemini key can run out of prepaid credit (Google returns
#      HTTP 402 "Your prepayment credits are depleted") or a model can be retired
#      (HTTP 404). Instead of failing the whole generation, route the SAME request
#      through fal.ai (fal-ai/any-llm  /  fal-ai/any-llm/vision) which serves
#      google/gemini-2.5-flash with the Firebean fal account.
#
# Key resolution (never store secrets in this public repo):
#   1) Streamlit Secrets  ->  FAL_KEY   (preferred, enables silent auto-fallback)
#   2) The key typed in the "Gemini API Key" box, IF it does not look like a
#      Google key (i.e. it is not "AIza...") -> treated as the fal key.
#
# Public API:
#   generate(key, model, system, user_text, images=None, max_tokens=8192,
#            temperature=0.9, json_mode=False, fal_key=None)
#       -> (text, finish_reason, error)   # text is None on failure
#   is_fal_key(k) -> bool
#   moshi_model_for(model) -> fal model id

import json
import os
import re
import requests

FAL_TEXT_URL = "https://fal.run/fal-ai/any-llm"
FAL_VISION_URL = "https://fal.run/fal-ai/any-llm/vision"
GOOGLE_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"

# Google alias -> fal model id. fal serves the same Gemini models.
FAL_MODEL_MAP = {
    "gemini-flash-latest": "google/gemini-2.5-flash",
    "gemini-2.5-flash": "google/gemini-2.5-flash",
    "gemini-2.5-flash-lite": "google/gemini-2.5-flash",  # retired on Google; fal has no -lite
    "gemini-2.5-pro": "google/gemini-2.5-pro",
    "gemini-3.8-flash": "google/gemini-2.5-flash",
}
DEFAULT_FAL_MODEL = "google/gemini-2.5-flash"

# Errors that mean "this provider cannot serve you" -> worth a fal retry.
FALLBACK_STATUS = {400, 401, 402, 403, 404, 429, 500, 503}
FALLBACK_HINTS = ("prepayment credits are depleted", "quota", "no longer available",
                  "not valid", "RESOURCE_EXHAUSTED", "billing")


def is_fal_key(k):
    """True when the given key is NOT a Google key (fal keys are '<id>:<secret>')."""
    if not k:
        return False
    k = k.strip()
    return (not k.startswith("AIza")) and ((":" in k) or (len(k) > 20))


def moshi_model_for(model):
    return FAL_MODEL_MAP.get(model, DEFAULT_FAL_MODEL)


def resolve_fal_key(explicit=None):
    """Find the fal.ai key: explicit arg -> Streamlit Secrets -> env var."""
    if explicit and str(explicit).strip():
        return str(explicit).strip()
    try:
        import streamlit as st
        for name in ("FAL_KEY", "FAL_API_KEY"):
            v = st.secrets.get(name, "")
            if v:
                return str(v).strip()
    except Exception:
        pass
    return (os.environ.get("FAL_KEY") or "").strip()


def _strip_fences(raw):
    return (raw or "").replace("```json", "").replace("```", "").strip()


def _google_call(key, model, system, user_text, images, max_tokens, temperature, json_mode):
    """Direct Google Gemini call. Returns (text, finish_reason, error)."""
    url = GOOGLE_URL.format(model=model, key=key)
    parts = [{"text": user_text}]
    for img in (images or []):
        if isinstance(img, dict):
            data, mime = img.get("data"), img.get("mimeType", "image/jpeg")
        else:
            data, mime = img, "image/jpeg"
        if data:
            parts.append({"inlineData": {"mimeType": mime, "data": data}})
    gen_cfg = {"maxOutputTokens": max_tokens, "temperature": temperature,
               "thinkingConfig": {"thinkingBudget": 0}}
    if json_mode:
        gen_cfg["responseMimeType"] = "application/json"
    payload = {
        "contents": [{"role": "user", "parts": parts}],
        "systemInstruction": {"parts": [{"text": system}]},
        "generationConfig": gen_cfg,
    }
    try:
        res = requests.post(url, json=payload, timeout=120)
        # A model may reject thinkingConfig (or JSON mode) -> retry once without it.
        if res.status_code == 400 and ("thinkingConfig" in gen_cfg or json_mode):
            gen_cfg.pop("thinkingConfig", None)
            gen_cfg.pop("responseMimeType", None)
            res = requests.post(url, json=payload, timeout=120)
        if res.status_code != 200:
            return None, None, f"HTTP {res.status_code} from Gemini: {res.text[:600]}"
        data = res.json()
        cands = data.get("candidates") or []
        if not cands:
            return None, None, f"No candidate returned. Raw: {json.dumps(data)[:500]}"
        reason = cands[0].get("finishReason", "UNKNOWN")
        p = cands[0].get("content", {}).get("parts", [])
        if not p:
            return None, reason, f"Empty content (finishReason={reason}). Raw: {json.dumps(data)[:500]}"
        return p[0].get("text", ""), reason, None
    except Exception as e:
        return None, None, f"Request exception: {type(e).__name__}: {e}"


def _fal_call(fal_key, model, system, user_text, images, max_tokens, temperature):
    """fal.ai call (text or vision). Returns (text, finish_reason, error)."""
    use_vision = bool(images)
    url = FAL_VISION_URL if use_vision else FAL_TEXT_URL
    body = {
        "model": moshi_model_for(model),
        "prompt": user_text,
        "system_prompt": system,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    if use_vision:
        urls = []
        for img in images:
            if isinstance(img, dict):
                data, mime = img.get("data"), img.get("mimeType", "image/jpeg")
            else:
                data, mime = img, "image/jpeg"
            if data:
                urls.append(f"data:{mime};base64,{data}")
        body["image_urls"] = urls
    try:
        res = requests.post(url, json=body,
                            headers={"Authorization": "Key " + fal_key,
                                     "Content-Type": "application/json"},
                            timeout=300)
        if res.status_code != 200:
            hint = ""
            if res.status_code in (401, 403):
                hint = ("   <-- KEY REJECTED. A fal key is LONGER than the id shown in the "
                        "dashboard list and contains a ':' — copy the WHOLE value with the "
                        "copy button at https://fal.ai/dashboard/keys")
            return None, None, f"HTTP {res.status_code} from fal.ai: {res.text[:600]}{hint}"
        data = res.json()
        text = data.get("output")
        if not text:
            return None, None, f"fal.ai returned no output. Raw: {json.dumps(data)[:500]}"
        return text, "STOP", None
    except Exception as e:
        return None, None, f"fal.ai exception: {type(e).__name__}: {e}"


def _slice_json_block(t):
    """Return the outermost {..} or [..] block found in the text."""
    starts = [i for i in (t.find("{"), t.find("[")) if i >= 0]
    if not starts:
        return ""
    i = min(starts)
    j = max(t.rfind("}"), t.rfind("]"))
    return t[i:j + 1] if j > i else ""


def parse_json_loose(text):
    """Parse model JSON defensively: strips fences/prose, repairs the two mistakes
    models actually make (trailing commas, a missing comma between two adjacent
    objects/arrays) — the fal.ai path has no server-side JSON mode, so this is what
    keeps its output usable."""
    if not text:
        return None
    t = _strip_fences(text)
    for cand in (t, _slice_json_block(t)):
        if not cand:
            continue
        try:
            return json.loads(cand)
        except Exception:
            pass
        fixed = re.sub(r",(\s*[}\]])", r"\1", cand)     # trailing commas
        fixed = re.sub(r"}\s*{", "},{", fixed)          # missing comma between objects
        fixed = re.sub(r"]\s*\[", "],[", fixed)         # missing comma between arrays
        try:
            return json.loads(fixed)
        except Exception:
            continue
    return None


def normalize_content(d):
    """Repair the structural drift the model sometimes shows: Challenge / Solution /
    FAQ nested inside SocialMedia instead of at the top level (the app and the GAS
    handler read them as top-level keys)."""
    if not isinstance(d, dict):
        return d
    for sm_key in ("SocialMedia", "social_media"):
        sm = d.get(sm_key)
        if isinstance(sm, dict):
            for k in ("Challenge", "Solution", "FAQ", "challenge", "solution", "faq"):
                if k in sm:
                    val = sm.pop(k)
                    if k.capitalize() not in d and k not in d:
                        d[k.capitalize() if k[0].islower() else k] = val
    return d


def generate(key, model, system, user_text, images=None, max_tokens=8192,
             temperature=0.9, json_mode=False, fal_key=None):
    """Generate text with Google Gemini, silently falling back to fal.ai.

    Returns (text, finish_reason, error, provider_used).
    When json_mode is on and the answer does not parse as JSON, one automatic
    retry is made with a firmer "valid JSON only" instruction.
    """
    typed = (key or "").strip()
    fal_key = resolve_fal_key(fal_key) or (typed if is_fal_key(typed) else "")
    # A fal key typed into the key box may be tried as a backup for the stored one —
    # so a good key can be used immediately even while Streamlit Secrets still holds
    # a stale/truncated FAL_KEY (which happens in practice).
    alt_fal = typed if (is_fal_key(typed) and typed != fal_key) else ""
    key = "" if is_fal_key(key) else typed

    text = reason = err = provider = None
    for attempt in range(2):
        sys_msg = system
        temp = temperature
        if attempt == 1:
            sys_msg = (system + "\n\nCRITICAL: Your previous answer was not valid JSON. "
                                "Return ONLY valid raw JSON — no prose, no markdown, "
                                "no trailing commas.")
            temp = min(temperature, 0.6)

        def _try_fal():
            t, r, e = _fal_call(fal_key, model, sys_msg, user_text, images, max_tokens, temp)
            if t is None and alt_fal and ("401" in (e or "") or "403" in (e or "")):
                t2, r2, e2 = _fal_call(alt_fal, model, sys_msg, user_text, images, max_tokens, temp)
                if t2 is not None:
                    return t2, r2, None
            return t, r, e

        if key:
            text, reason, err = _google_call(key, model, sys_msg, user_text, images,
                                             max_tokens, temp, json_mode)
            provider = "google"
            if text is None:
                # Is fal worth trying? (out of credit / rate-limited / model retired)
                status = ("HTTP " + str(x) for x in FALLBACK_STATUS)
                retry = any(s in err for s in status) or any(h in err for h in FALLBACK_HINTS)
                if not (retry and fal_key):
                    return None, reason, err, "google"
                g_err = err
                text, reason, err = _try_fal()
                provider = "fal"
                if text is None:
                    return None, reason, ((err or "") + (" | Google said: " + (g_err or "") if g_err else "")), "fal"
        else:
            if not fal_key:
                return None, None, "No API key available (Google or fal.ai).", "none"
            text, reason, err = _try_fal()
            provider = "fal"
            if text is None:
                return None, reason, err, "fal"

        if json_mode and parse_json_loose(text) is None and attempt == 0:
            continue  # one firmer retry
        return text, reason, None, provider

    return text, reason, err, provider
