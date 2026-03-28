# Firebean Apps Script — 3 Deployments

Each `.gs` file is a **separate Apps Script project** deployed as a Web App.
Copy each file's content into its own Apps Script editor and redeploy when updated.

---

## Script 1 — `1_MasterDB_SyncSheet.gs`
**Paste into:** Google Sheet → Extensions > Apps Script  
**Sheet:** [Firebean_Master_DB](https://docs.google.com/spreadsheets/d/1aTuqgmmSKMWgNCl2KR0QhK4Cj8G7W5yPsr4t39pi-yc)  
**Deployed URL:** `https://script.google.com/macros/s/AKfycbxy6JwJpmclJOBerKJO4EJ50oKyL86Ux1Qci2oHx1RQiw8ruL_Um6qVYsWydyEsLawQ/exec`  
**app.py variable:** `SHEET_SCRIPT_URL`  
**Listens for action:** `sync_project`  

**What it writes to the sheet:**
| Column | Field |
|--------|-------|
| A | Timestamp |
| B | Client Name |
| C | Project Name |
| D | Event Date |
| E | Venue |
| F | Category |
| G | What We Do |
| H | Scope of Work |
| I | YouTube Link |
| J | Open Question |
| K | Challenge |
| L | Solution |
| M | Google Slide URL |
| N | LinkedIn Post |
| O | Facebook Post |
| P | Threads Post |
| Q | Instagram Post |
| R | Web EN (HTML article) |
| S | Web TC (HTML article) |
| T | Web JP (HTML article) |
| U | Sync Status |
| V | Drive Folder Link |
| W | Hero Photo |
| X | Logo Black |
| Y | Logo White |
| Z | Project ID |
| AA | Sort Date |
| AB | FAQ EN |
| AC | FAQ TC |
| AD | FAQ JP |

---

## Script 2 — `2_MasterDB_SlideCreator.gs`
**Paste into:** separate Apps Script project  
**Deployed URL:** `https://script.google.com/macros/s/AKfycbx_7Xf8_HERQel93WJB2F_KjFOWHtCXzfvEkP9B_p7Kh4ImRAWRgWSXtLklvdbYsqbI/exec`  
**app.py variable:** `SLIDE_DB_URL`  
**Listens for action:** `create_slide`  

**What it does:**
- Opens `Firebean_CaseStudy_Template` Google Slides (`19rmqCzgKD8y2ZiLxkiAqhhkV6_t-8QAumZkSi0Eu9C0`)
- Duplicates template slides 1+2 to end of presentation
- Inserts project photos (base64 JPEG) into 2×3 photo grid on cover slide
- Inserts white logo (base64 PNG) replacing `{{WHITE_LOGO}}` placeholder
- Fills text: `{{CLIENT_NAME}}`, `{{PROJECT_NAME}}`, `{{VENUE}}`, `{{DATE}}`, `{{CATEGORY}}`, `{{SCOPE}}`, `{{CHALLENGE}}`, `{{SOLUTION}}`
- Updates Master DB col M (Google Slide URL)

---

## Script 3 — `3_CaseStudy_SlideCreator.gs`
**Paste into:** separate Apps Script project  
**Deployed URL:** `https://script.google.com/macros/s/AKfycbxKP-8Xrvy6hblPqTmtXn76rO3DFOeU6jYQtLw5QDfDP1-adNDk02bhoKihfvp_Xsvy/exec`  
**app.py variable:** `CASE_STUDY_URL`  
**Listens for action:** `create_case_study`  

Same logic as Script 2 — standalone case study deck per project.

---

## Template Placeholders (in Google Slides)

Make sure your template slides contain these text placeholders:

**Slide 1 (Cover):**
- `{{CLIENT_NAME}}`
- `{{PROJECT_NAME}}`
- `{{WHITE_LOGO}}` ← replaced with actual logo image
- Right half of slide = photo grid (images inserted automatically)

**Slide 2 (Detail):**
- `{{CLIENT_NAME}}`
- `{{PROJECT_NAME}}`
- `{{VENUE}}`
- `{{DATE}}`
- `{{CATEGORY}}`
- `{{SCOPE}}`
- `{{CHALLENGE}}`
- `{{SOLUTION}}`
