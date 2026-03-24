# Firebean CMS — Complete Technical Architecture Guideline
*Version: 7.2*

This document serves as the absolute source of truth for the Firebean CMS pipeline. Any AI or developer modifying the code must read and adhere to these rules to prevent breaking the end-to-end flow.

---

## 1. System Architecture Overview

The Firebean CMS is a 4-part pipeline:

1. **Frontend Input (Streamlit `app.py`)**: Collects user input, uploads images, generates AI content, and POSTs JSON to Google Apps Script.
2. **Master DB (Google Sheets)**: Stores all project data. Acts as the central source of truth.
3. **Sync Engine (Apps Script `sync-to-github.gs`)**: Downloads images from Drive, compares MD5 hashes, builds `projects.json`, and pushes everything to GitHub via the Git Tree API in a single batch commit.
4. **Website Display (GitHub Pages `cs627/Firebean-Website`)**: Static HTML/JS reads `projects.json` and renders the portfolio. GitHub Actions automatically converts pushed JPEG images to real WebP format for performance.

---

## 2. Data Flow & Field Mappings

### 2.1 The 30 Columns in Google Sheets (Master DB)
The Google Sheet `Basic Info` tab has exactly 30 columns. The Apps Script expects these exact column indices:

| Col # | Field Name | Source | Format / Notes |
|---|---|---|---|
| 1 | `TIMESTAMP` | Auto | Date string |
| 2 | `CLIENT` | Streamlit | String |
| 3 | `PROJECT` | Streamlit | String |
| 4 | `DATE` | Streamlit | String (e.g. "Feb 2026") |
| 5 | `VENUE` | Streamlit | String |
| 6 | `CATEGORY` | Streamlit | String |
| 7 | `WHAT_WE_DO` | Streamlit | Comma-separated string |
| 8 | `SCOPE` | Streamlit | Comma-separated string |
| 9 | `YOUTUBE` | Streamlit | URL string |
| 10 | `OPEN_QUESTION` | Streamlit | String |
| 11 | `CHALLENGE` | Streamlit AI | String (English only, max 50 words) |
| 12 | `SOLUTION` | Streamlit AI | String (English only, max 50 words) |
| 13 | `GOOGLE_SLIDE` | Streamlit | URL string |
| 14 | `LINKEDIN` | Streamlit AI | String |
| 15 | `FACEBOOK` | Streamlit AI | String |
| 16 | `THREADS` | Streamlit AI | String |
| 17 | `INSTAGRAM` | Streamlit AI | String |
| 18 | `WEB_EN` | Streamlit AI | HTML string (H1, H3, P tags only) |
| 19 | `WEB_TC` | Streamlit AI | HTML string |
| 20 | `WEB_JP` | Streamlit AI | HTML string |
| 21 | `SYNC_STATUS` | Auto | "Pending", "Pending (images)", "Synced" |
| 22 | `DRIVE_FOLDER` | Auto / Manual | Drive Folder URL |
| 23 | `HERO_PHOTO` | Auto / Manual | Drive File URL |
| 24 | `LOGO_BLACK` | Auto / Manual | Drive File URL |
| 25 | `LOGO_WHITE` | Auto / Manual | Drive File URL |
| 26 | `PROJECT_ID` | Auto | Uppercase string (e.g. "FB2026010") |
| 27 | `SORT_DATE` | Auto | ISO string `YYYY-MM-DD` |
| 28 | `FAQ_EN` | Streamlit AI | Stringified JSON array of Q&A objects |
| 29 | `FAQ_TC` | Streamlit AI | Stringified JSON array of Q&A objects |
| 30 | `FAQ_JP` | Streamlit AI | Stringified JSON array of Q&A objects |

### 2.2 Streamlit `app.py` Payload to Apps Script
When Streamlit syncs to the sheet, it sends a JSON payload to the Apps Script `doPost` function.
**Critical Mapping Rules:**
- `ai_content`: Must contain the full AI output dict (used for `web_en`, `web_tc`, `web_jp` etc.)
- `faq_en`, `faq_tc`, `faq_jp`: Must be sent as stringified JSON arrays.
- `logo_black`, `logo_white`, `images[]`: Must be sent as **base64 encoded strings**. The Apps Script decodes these and saves them to a Google Drive folder automatically.

---

## 3. The Sync Engine (`sync-to-github.gs`)

### 3.1 Image Handling & Hashes
- **Performance:** Apps Script cannot convert images to WebP natively. It downloads JPEGs from Drive and pushes them to GitHub named with a `.webp` extension (e.g. `fb2026010-hero.webp`).
- **MD5 Hash Cache:** The script reads `data/image-hashes.json` from GitHub. If the MD5 hash of the Drive image matches the GitHub hash, the upload is skipped. This makes syncs extremely fast.
- **Gallery Photos:** The script lists all files in the Drive folder. It finds the hero photo, then assigns the rest as `gallery-0`, `gallery-1`, etc.
- **Fallback Logic:** If `SYNC_STATUS` is not "Pending (images)", the script will NOT download images from Drive. Instead, it reads `image-hashes.json` and the existing `projects.json` to preserve the `galleryPhotos` array.

### 3.2 GitHub Tree API Batch Push
To avoid rate limits and slow syncs, the script uses the **Git Data API** to push everything in ONE commit:
1. Get latest commit SHA
2. Get base tree SHA
3. Create blobs for all changed images and JSON files
4. Create new tree
5. Create new commit
6. Update ref `heads/main`

---

## 4. Website Frontend Architecture

### 4.1 Data Loading (`cms.js`)
- Reads `data/projects.json`.
- Prepends the `BASE_PATH` (e.g., `/Firebean-Website/`) to all relative image URLs (`heroPhoto`, `logoBlack`, `galleryPhotos`).
- Dispatches `cmsDataReady` event when loaded.

### 4.2 Profile Page (`profile.html`)
- Matches the URL `?id=fb2026010` to the project object where `p.id === 'fb2026010'`.
- **Note on IDs:** `PROJECT_ID` in the sheet is uppercase (`FB2026010`). The sync script outputs `id: pid` (lowercase) into `projects.json` so it matches the URL exactly.
- **Gallery Interleaving (`interleave()` function):** The website does not have a separate gallery grid. Instead, it injects `<img class="interleaved-photo-pair">` tags directly between the `<p>` and `<h3>` tags of the article text (`WEB_EN`, `WEB_TC`, etc.).
- **YouTube:** Extracts the 11-character video ID from the `YOUTUBE` column and embeds an iframe.

### 4.3 GitHub Actions WebP Converter
- **Trigger:** Runs automatically on push to `data/images/**`.
- **Action:** Uses `cwebp` to convert the fake `.webp` files (which are actually JPEG/PNG bytes pushed by Apps Script) into **real WebP format**.
- **Why:** Reduces file size by 30% for faster loading. This workflow NEVER touches code files, only images.

---

## 5. Strict Coding Rules for AI/Developers

1. **DO NOT change column order** in Google Sheets or `sync-to-github.gs` without updating both simultaneously.
2. **DO NOT change image file extensions**. They must remain `.webp` in Apps Script, even if they are JPEG bytes. GitHub Actions handles the conversion.
3. **DO NOT remove `id: pid`** from the `projects.json` builder in Apps Script. The profile page relies on lowercase IDs.
4. **DO NOT send JS Date strings** to `projects.json`. The `SORT_DATE` must always be formatted as `YYYY-MM-DD` so `localeCompare` sorting works correctly on the website.
5. **DO NOT change the HTML structure** of `WEB_EN/TC/JP`. It must remain `<h3>` followed by `<p>` tags so the `interleave()` function can correctly inject gallery photos between paragraphs.
6. **NEVER use the term "Firebean Brain"** in any public-facing content.

---
*End of Document*
