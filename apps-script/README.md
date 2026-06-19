# Firebean Apps Script — Reference Notes

> ⚠️ **SOURCE OF TRUTH WARNING — READ FIRST**
>
> The **live, authoritative** Apps Script code is maintained **inside the Google Apps Script
> project** bound to the Master DB Google Sheet — **NOT in this repo.**
>
> As of June 2026 the live project contains:
> - **GitHub.gs** — `VERSION 12.2.0` (Self-Healing Paths + Fast Sync Selected Row).
>   Contains `doSync` / the "🔥 CMS Sync" menu that pushes `projects.json` + images to GitHub.
>   Has `listExistingImagesOnGitHub_()` + `reconstructFromGitHub_()` so a sync can never again
>   blank `heroPhoto` / `galleryPhotos`.
> - **handlers.gs** — `VERSION 12.1.0` — the `doPost` / `syncProjectFromStreamlit` web-app
>   endpoint that receives data from the Streamlit app.
>
> **Do NOT treat any `.gs` file that may appear in this repo as current.** Older v7.x copies
> previously lived here and caused confusion. To edit the sync logic, edit it in the Apps
> Script editor (Sheet → Extensions → Apps Script), then redeploy the Web App.

## Deployment

- **Web App `/exec` URL** used by the Streamlit app (`synthesis_sync.py` → `GAS_URL`):
  `https://script.google.com/macros/s/AKfycbw6UuXZqhoFYtEiGYPJmFAWCis9IN-M-NVYN8hEo-Ux6UKKloihhv4yScS6ocGEJ9Em/exec`
- The URL stays the same as long as you **edit the existing deployment** (Deploy → Manage
  deployments → ✏️) rather than creating a brand-new deployment.

## Files kept in this repo (reference only — slide generators)

- `2_MasterDB_SlideCreator.gs` (v18.0) — Master DB → Google Slides generator.
- `3_CaseStudy_SlideCreator.gs` (v18.0) — Case Study slide generator.
- `appsscript.json` — manifest reference.

## Live data location

The live website data (`data/projects.json`, `data/images/`) lives in the
**`cs627/Firebean-Website`** repo, which is what `firebean.net` serves. It is intentionally
**not** duplicated in this app repo (a stale copy here only goes out of date).
