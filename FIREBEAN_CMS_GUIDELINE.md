# Firebean CMS — Complete Technical Architecture Guideline
*Version: 7.4 — Last updated: Mar 2026*

This document is the **absolute source of truth** for the Firebean CMS pipeline. Any AI or developer modifying any part of the system must read and follow these rules in full before making any changes.

---

## 1. System Architecture Overview

The Firebean CMS is a **4-part pipeline** connecting Streamlit → Google Sheets → GitHub → Website:

```
[Streamlit app.py]
  → POST JSON payload to Apps Script (doPost)
  → Saves base64 images to Google Drive (Project Name folder)
  → Writes all 30 fields to Google Sheet "Basic Info" tab
  → Sets SYNC_STATUS = "Pending (images)"

[Google Sheet — Firebean CMS Menu]
  → "Sync Changed Only" or "Sync Selected Project"
  → Apps Script downloads images from Drive
  → MD5 hash check — skips unchanged images (fast)
  → Git Tree API — ONE batch commit to cs627/Firebean-Website:
      data/images/{pid}-hero.webp
      data/images/{pid}-hero-sm.webp
      data/images/{pid}-logo-black.webp
      data/images/{pid}-logo-white.webp
      data/images/{pid}-gallery-0.webp ... gallery-7.webp
      data/projects.json
      data/image-hashes.json

[GitHub Actions — cs627/Firebean-Website]
  → Triggered automatically on push to data/images/**
  → cwebp converts JPEG/PNG bytes to real WebP (30% smaller)
  → Commits "auto: convert images to real WebP [skip ci]"

[GitHub Pages — cs627.github.io/Firebean-Website]
  → cms.js loads data/projects.json
  → profile.html?id=fb2026010 matches project by lowercase id
  → interleave() injects gallery photos between article paragraphs
  → YouTube iframe embedded from youtube field
```

---

## 2. Repository Structure

| Repo | Purpose | Who writes to it |
|---|---|---|
| `dickson-crypto/Firebean-app` | Streamlit CMS app + Apps Script source | Developers only |
| `cs627/Firebean-Website` | Live website (GitHub Pages) | Apps Script sync only |

**NEVER manually edit files in `cs627/Firebean-Website/data/`** — these are managed exclusively by the Apps Script sync engine.

---

## 3. Google Drive Structure

### 3.1 Folder Hierarchy

```
My Drive
  └── Firebean Projects/          ← Parent folder ID: 1XT6c6zq-ipGN0sFRwpGl2GSVnaGsmSNg
        ├── 雅培保兒加營素3+成長關鍵Level Up攀石活動/   ← Named by PROJECT NAME
        │     ├── Logo_Black.png
        │     ├── Logo_White.png
        │     ├── Photo_1.jpg     ← Hero photo (index 0)
        │     ├── Photo_2.jpg
        │     └── ... Photo_8.jpg
        ├── ABC Online Conference/
        └── ...
```

### 3.2 Drive Naming Rules (CRITICAL)

- **Folder name = Project Name** (NOT Project ID — this is intentional)
- **Logo files:** Always named `Logo_Black.png` and `Logo_White.png` exactly
- **Photo files:** Always named `Photo_1.jpg` through `Photo_8.jpg` sequentially
- **Parent folder:** Always under `Firebean Projects` (ID: `1XT6c6zq-ipGN0sFRwpGl2GSVnaGsmSNg`)
- The Apps Script `getOrCreateProjectFolder_(pid, projectName)` handles creation automatically using the correct parent folder ID

### 3.3 Drive → GitHub Naming Conversion

When the sync script pushes to GitHub, it **renames** files using the Project ID:

| Google Drive filename | GitHub filename |
|---|---|
| `Photo_1.jpg` (hero, full size) | `fb2026010-hero.webp` |
| `Photo_1.jpg` (hero, small) | `fb2026010-hero-sm.webp` |
| `Logo_Black.png` | `fb2026010-logo-black.webp` |
| `Logo_White.png` | `fb2026010-logo-white.webp` |
| `Photo_2.jpg` | `fb2026010-gallery-0.webp` |
| `Photo_3.jpg` | `fb2026010-gallery-1.webp` |
| ... | ... |

> **This naming duality is intentional and correct.** Google Drive uses human-readable Project Names for organisation. GitHub uses Project IDs for programmatic URL references in `projects.json`. Never change this convention.

---

## 4. Data Flow & Field Mappings

### 4.1 The 30 Columns in Google Sheets (Master DB)

The Google Sheet `Basic Info` tab has exactly **30 columns**. Column order must never change without updating `CONFIG.COL` in the sync script simultaneously.

| Col # | Header | Source | Format / Notes |
|---|---|---|---|
| 1 | Timestamp | Auto | Date string |
| 2 | Client Name | Streamlit | String |
| 3 | Project Name | Streamlit | String |
| 4 | Event Date | Streamlit | String (e.g. "Feb 2026") |
| 5 | Venue | Streamlit | String |
| 6 | Category (Who we help) | Streamlit | String |
| 7 | What we do | Streamlit | Comma-separated string |
| 8 | Scope of Work | Streamlit | Comma-separated string |
| 9 | YouTube Link | Streamlit | Full YouTube URL |
| 10 | Open Question | Streamlit | String |
| 11 | Challenge | Streamlit AI | English only, max 50 words |
| 12 | Solution | Streamlit AI | English only, max 50 words |
| 13 | Google Slide | Streamlit (manual) | Google Slides URL — user must fill in "Google Slide" tab before syncing |
| 14 | LinkedIn | Streamlit AI | String |
| 15 | Facebook | Streamlit AI | String |
| 16 | Threads | Streamlit AI | String |
| 17 | Instagram | Streamlit AI | String |
| 18 | Web EN | Streamlit AI | HTML string — `<h3>` and `<p>` tags only |
| 19 | Web TC | Streamlit AI | HTML string — `<h3>` and `<p>` tags only |
| 20 | Web JP | Streamlit AI | HTML string — `<h3>` and `<p>` tags only |
| 21 | Sync Status | Auto | `"Pending"`, `"Pending (images)"`, or `"Synced [datetime]"` |
| 22 | Drive Folder Link | Auto | `https://drive.google.com/drive/folders/{id}` |
| 23 | Hero Photo Picker | Auto | `https://drive.google.com/file/d/{id}/view?usp=drivesdk` |
| 24 | Logo Black | Auto | `https://drive.google.com/file/d/{id}/view?usp=drivesdk` |
| 25 | Logo White | Auto | `https://drive.google.com/file/d/{id}/view?usp=drivesdk` |
| 26 | Project_id | Auto | Uppercase string (e.g. `FB2026010`) |
| 27 | Sort_date | Auto | ISO string `YYYY-MM-DD` |
| 28 | FAQ_EN | Streamlit AI | Stringified JSON array of `[{"Q1": "...", "A1": "..."}]` objects |
| 29 | FAQ_TC | Streamlit AI | Stringified JSON array |
| 30 | FAQ_JP | Streamlit AI | Stringified JSON array |

### 4.2 Streamlit `app.py` Payload to Apps Script

When the user clicks **"Sync to Master DB"**, `trigger_full_sync()` sends this JSON payload to the Apps Script `doPost` endpoint:

```json
{
  "action": "sync_project",
  "client_name": "Abbott",
  "project_name": "雅培保兒加營素3+成長關鍵Level Up攀石活動",
  "project_id": "FB2018408",
  "sort_date": "2018-06-01",
  "date": "Jun 2018",
  "venue": "Verm City",
  "youtube": "https://www.youtube.com/watch?v=l7HRUnttVV8",
  "category": "F&B & HOSPITALITY",
  "category_what": "SOCIAL & CONTENT, PR & MEDIA, EVENTS & CEREMONIES",
  "scope": "Event Coordination, Event Production, ...",
  "open_question": "...",
  "challenge": "...",
  "solution": "...",
  "faq_en": "[{\"Q1\": \"...\", \"A1\": \"...\"}]",
  "faq_tc": "[{\"Q1\": \"...\", \"A1\": \"...\"}]",
  "faq_jp": "[{\"Q1\": \"...\", \"A1\": \"...\"}]",
  "ai_content": {
    "1_google_slide": "https://docs.google.com/presentation/d/...",
    "2_facebook_post": "...",
    "3_threads_post": "...",
    "4_instagram_post": "...",
    "5_linkedin_post": "...",
    "6_website": {
      "en": "<h3>...</h3><p>...</p>",
      "tc": "<h3>...</h3><p>...</p>",
      "jp": "<h3>...</h3><p>...</p>"
    },
    "7_faq": {
      "en": [{"Q1": "...", "A1": "..."}],
      "tc": [],
      "jp": []
    },
    "challenge_summary": "...",
    "solution_summary": "..."
  },
  "logo_black": "<base64 string>",
  "logo_white": "<base64 string>",
  "hero_index": 0,
  "images": ["<base64>", "<base64>", ...]
}
```

**Critical Mapping Rules:**

- `ai_content['1_google_slide']` → Col 13 (Google Slide). **User must fill this in the "Google Slide" tab in Streamlit before clicking Sync — it is not auto-generated.**
- `ai_content['6_website']['en/tc/jp']` → Cols 18-20 (Web EN/TC/JP)
- `faq_en/faq_tc/faq_jp` → Cols 28-30 as stringified JSON arrays
- `logo_black` + `logo_white` (base64) → Saved as `Logo_Black.png` / `Logo_White.png` in Drive → Drive URL written to Cols 24-25
- `images[]` (base64 array) + `hero_index` → Saved as `Photo_1.jpg`...`Photo_8.jpg` in Drive → hero Drive URL written to Col 23
- `project_id` → Used as folder lookup key but **the Drive folder is named by `project_name`**
- `project_name` → Used as the Drive folder name (NOT project_id)

### 4.3 `projects.json` Structure (Output to Website)

Each project object in `data/projects.json` on GitHub:

```json
{
  "id": "fb2026010",
  "projectId": "FB2026010",
  "client": "Civil Service Bureau",
  "project": "《科技提升職業安全與健康》2025-26 巡迴展覽",
  "date": "Feb 2026",
  "sortDate": "2026-02-01",
  "venue": "Government Headquarters",
  "category": "GOVERNMENT & PUBLIC SECTOR",
  "filterSlugs": ["government-public-sector"],
  "whatWeDo": "ROVING EXHIBITIONS",
  "scope": "Event Coordination, Event Production, ...",
  "youtube": "https://www.youtube.com/watch?v=...",
  "openQuestion": "...",
  "challenge": "...",
  "solution": "...",
  "googleSlide": "https://docs.google.com/presentation/d/...",
  "linkedin": "...",
  "facebook": "...",
  "threads": "...",
  "instagram": "...",
  "webEN": "<h3>...</h3><p>...</p>",
  "webTC": "<h3>...</h3><p>...</p>",
  "webJP": "<h3>...</h3><p>...</p>",
  "heroPhoto": "data/images/fb2026010-hero.webp",
  "heroPhotoSm": "data/images/fb2026010-hero-sm.webp",
  "logoBlack": "data/images/fb2026010-logo-black.webp",
  "logoWhite": "data/images/fb2026010-logo-white.webp",
  "galleryPhotos": [
    "data/images/fb2026010-gallery-0.webp",
    "data/images/fb2026010-gallery-1.webp"
  ],
  "faqEN": "[{\"Q1\": \"...\", \"A1\": \"...\"}]",
  "faqTC": "[{\"Q1\": \"...\", \"A1\": \"...\"}]",
  "faqJP": "[{\"Q1\": \"...\", \"A1\": \"...\"}]"
}
```

> **Note on `id` vs `projectId`:** `id` is always **lowercase** (e.g. `fb2026010`) and is used for URL matching (`profile.html?id=fb2026010`). `projectId` is uppercase (`FB2026010`) and stored for reference. Both are written by the sync script.

---

## 5. The Sync Engine (`sync-to-github.gs`)

### 5.1 Configuration Constants

```javascript
var CONFIG = {
  SHEET_NAME: 'Basic Info',
  GITHUB_OWNER: 'cs627',
  GITHUB_REPO: 'Firebean-Website',
  GITHUB_BRANCH: 'main',
  IMAGES_PATH: 'data/images',
  JSON_PATH: 'data/projects.json',
  HASH_PATH: 'data/image-hashes.json',
  HERO_WIDTH: 1200,
  HERO_SM_WIDTH: 400,
  LOGO_WIDTH: 200,
  GALLERY_WIDTH: 1200
};
var FIREBEAN_PROJECTS_FOLDER_ID_ = '1XT6c6zq-ipGN0sFRwpGl2GSVnaGsmSNg';
```

### 5.2 Image Handling & MD5 Hash Cache

- Apps Script downloads images from Drive via Google CDN URLs (resized to configured widths)
- Each image is MD5-hashed. If the hash matches `data/image-hashes.json` on GitHub, the upload is **skipped** — this makes syncs fast
- Images are pushed to GitHub with `.webp` extension even though the bytes are JPEG/PNG — GitHub Actions converts them to real WebP
- `galleryPhotos` is populated by listing all non-hero, non-logo files in the Drive folder

### 5.3 GitHub Tree API Batch Push

All changes are pushed in **ONE single commit** using the Git Data API:
1. Get latest commit SHA from `refs/heads/main`
2. Get base tree SHA
3. Create blobs for all changed image files + `projects.json` + `image-hashes.json`
4. Create new tree with all blobs
5. Create new commit pointing to new tree
6. Update `refs/heads/main` to new commit SHA

### 5.4 Sync Status Flow

| Status | Meaning | What sync does |
|---|---|---|
| `Pending (images)` | Images changed — full sync needed | Downloads images from Drive, pushes to GitHub |
| `Pending` | Text only changed | Skips image download, rebuilds JSON only |
| `Synced [datetime]` | Up to date | Row is skipped entirely |

### 5.5 Drive Folder Creation Logic

The `getOrCreateProjectFolder_(pid, projectName)` function:
1. Opens parent folder by ID: `1XT6c6zq-ipGN0sFRwpGl2GSVnaGsmSNg` (Firebean Projects)
2. Searches for a subfolder named by **Project Name**
3. If not found, checks for a legacy folder named by Project ID and renames it
4. If still not found, creates a new folder with the Project Name
5. Returns the folder object for saving images

---

## 6. Website Frontend Architecture

### 6.1 Data Loading (`src/cms.js`)

- Fetches `data/projects.json` relative to the page base path
- `BASE_PATH` = `/Firebean-Website/` (set by `<base href="/Firebean-Website/">` in HTML)
- Prepends `BASE_PATH` to all relative image paths (`heroPhoto`, `logoBlack`, `galleryPhotos`)
- Dispatches `cmsDataReady` custom event when data is loaded

### 6.2 Profile Page (`profile.html`)

- URL format: `profile.html?id=fb2026010` (always lowercase Project ID)
- Matches by `p.id === queryId` using the lowercase `id` field in `projects.json`
- **Gallery Interleaving:** `interleave()` injects `<img>` tags between `<p>` and `<h3>` tags in the article HTML — there is no separate gallery grid section
- **YouTube:** Extracts 11-character video ID and embeds `<iframe src="youtube.com/embed/{id}">`
- **FAQ:** Parses stringified JSON from `faqEN/TC/JP` and renders Q&A pairs on the right sidebar

### 6.3 Index Page (`index.html`)

- Renders project cards using `heroPhoto`, `logoBlack`, `client`, `project`, `date`, `category`
- Filters by `filterSlugs` array (derived from `category` field by `categoryToSlugs_()` function)
- Sorts by `sortDate` field using `localeCompare` — requires `YYYY-MM-DD` format

### 6.4 GitHub Actions WebP Converter

File: `.github/workflows/convert-to-webp.yml` in `cs627/Firebean-Website`

- **Trigger:** `push` event on `data/images/**`
- **Tool:** `cwebp` (Google's WebP encoder), quality 85 for photos, lossless for logos
- **Scope:** Only processes files in `data/images/` — **never touches any code files**
- **Commit message:** `"auto: convert images to real WebP [skip ci]"` (prevents infinite loop)

---

## 7. Strict Coding Rules for AI and Developers

1. **DO NOT change column order** in Google Sheets or `sync-to-github.gs` without updating both simultaneously. Column indices are hardcoded in `CONFIG.COL`.

2. **DO NOT change image file extensions.** GitHub images must always use `.webp` extension, even if the bytes are JPEG. GitHub Actions handles the actual conversion.

3. **DO NOT remove `id: pid`** from the `projects.json` builder. The profile page matches `?id=fb2026010` using the lowercase `id` field.

4. **DO NOT send JS Date strings** to `projects.json`. `sortDate` must always be `YYYY-MM-DD` format. Use `formatSortDate_()` helper.

5. **DO NOT change the HTML structure** of `WEB_EN/TC/JP`. Must use `<h3>` and `<p>` tags only. The `interleave()` function splits on these tags to inject gallery photos.

6. **DO NOT rename Drive folders manually.** The sync script finds folders by name. Manual renaming causes the script to create a new duplicate folder.

7. **Drive folder = Project Name. GitHub image = Project ID.** This duality is intentional. Never use Project ID as a Drive folder name.

8. **NEVER use the term "Firebean Brain"** in any public-facing content or code comments.

9. **DO NOT modify `data/projects.json` or `data/images/` directly** in `cs627/Firebean-Website`. These are managed exclusively by the Apps Script sync engine.

10. **The Google Slide URL must be filled manually** in the Streamlit "Google Slide" tab before syncing. It is not auto-generated by AI.

---

## 8. Version History

| Version | Date | Changes |
|---|---|---|
| v7.4 | Mar 2026 | Fixed Drive folder: uses Project Name + correct parent folder ID (`1XT6c6zq-ipGN0sFRwpGl2GSVnaGsmSNg`). Fixed hero photo URL format. Auto-renames legacy ID-named folders. Documented Google Slide manual entry. |
| v7.3 | Mar 2026 | Removed `setupTriggers` and `onEditTrigger` — manual sync only workflow. Menu shows only 2 items. |
| v7.2 | Mar 2026 | Fixed `galleryPhotos` fallback from existing `projects.json`. Fixed `sortDate` to `YYYY-MM-DD`. |
| v7.1 | Mar 2026 | Fixed `ai_content` vs `ai_generated` mismatch. Fixed FAQ flat vs nested fields. Added base64 Drive save helpers. Added `id: pid` lowercase to JSON. |
| v7.0 | Mar 2026 | Restored Git Tree API batch push. Targets `cs627/Firebean-Website`. |
| v4.4 | 2025 | Original working version with MD5 hash cache and batch push. |

---

*End of Document*
