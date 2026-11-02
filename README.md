# Firebean Streamlit Admin App

This repository contains the Streamlit application used for administering the Firebean CMS.

## AI provider fallback (2026-11-02)

All AI calls go through `ai_backend.py`:

1. **Google Gemini first** (the key in the "Gemini API Key" box / Streamlit Secrets).
2. **Automatic fal.ai fallback** (`fal-ai/any-llm` + `/any-llm/vision`, model
   `google/gemini-2.5-flash`) when Google answers with 402 *prepayment credits
   are depleted*, 429 rate-limit, or 404 *model retired*. The success banner tells
   you which provider answered.

To enable the fallback, add **one line** in Settings → Secrets:

```toml
FAL_KEY="<your fal.ai key>"
```

Get it from https://fal.ai/dashboard/keys — copy the key with the **copy button**; the
value is longer than the short id shown in the list (it contains a `:` — a truncated id
returns HTTP 401 "Authentication is required").

**No Gemini key is fine**: with `FAL_KEY` present the app runs entirely on fal.ai. Add
`GEMINI_API_KEYS = "AIza..."` back at any time and Gemini automatically becomes the primary
provider again — no code change needed.

## Recent Updates

- **2026-11-02: AI provider fallback (v19.4.1 / synthesis v20.3.0 / diagnostics v19.2.0)**
  - fal-only mode: with `FAL_KEY` in Secrets but no Gemini key the portal still generates
    (the Generate button used to stay disabled on an empty key — fixed).
  - New `ai_backend.py`: Google Gemini → automatic fal.ai fallback, defensive JSON
    parsing (fences, trailing commas, missing commas) + one firmer retry, and a
    normalizer that lifts `Challenge`/`Solution`/`FAQ` back to the top level if the
    model nests them inside `SocialMedia`.
  - Retired model `gemini-2.5-flash-lite` removed from the Model list (Google 404s it).
- **2026-03-16: CMS Guide Updates**
  - The CMS guide (v4.2) has been updated to reflect recent website design changes and will include details on new features such as Hero Photo Picker, Streamlit save/load, Q&A format standardization, and image sync optimization.
