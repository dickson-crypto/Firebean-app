/**
 * ============================================================
 * FIREBEAN CMS → GITHUB SYNC PIPELINE  v7.3 (CLEAN MENU — manual sync only)
 * ============================================================
 * 
 * v7.4: Fixed Drive folder creation — uses Project Name, parent = Firebean Projects folder
 *       Fixed hero photo missing when images[] not sent (now uses hero_photo_url fallback)
 *       Fixed Google Slide: always written from ai_content['1_google_slide']
 * v7.3: Removed setupTriggers and onEditTrigger (not needed for manual-only workflow)
 * v7.1: Fixed syncProjectFromStreamlit to match app.py payload exactly
 *       - ai_content (app.py) now correctly read (was ai_generated)
 *       - faq_en/faq_tc/faq_jp flat fields now read (was nested faq_texts)
 *       - logo_black/logo_white base64 now saved to Drive correctly
 *       - images[] base64 array now saved to Drive as Photo_1.jpg etc.
 *       - Added id: pid (lowercase) to project JSON for profile page matching
 *       - Added getOrCreateProjectFolder_ and saveBase64ToDrive_ helpers
 * v7.0: Restored v4.4 image download + MD5 hash + GitHub Tree batch push logic
 *       - Targets cs627/Firebean-Website (the live website repo)
 *       - Supports Streamlit app (doPost, syncProjectFromStreamlit)
 *       - Supports "Sync Selected Project" (syncSelectedProjectToGitHub)
 *       - Fixes long running time by pushing everything in ONE commit via Git Tree API
 *       - Images are saved with .webp extension directly
 *
 * SETUP:
 *   1. Open Google Sheet → Extensions > Apps Script
 *   2. Paste this script
 *   3. Project Settings > Script Properties → add GITHUB_TOKEN
 *
 * ============================================================
 */

// ─── CONFIG ────────────────────────────────────────────────
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
  GALLERY_WIDTH: 1200,

  COL: {
    TIMESTAMP: 1,
    CLIENT: 2,
    PROJECT: 3,
    DATE: 4,
    VENUE: 5,
    CATEGORY: 6,
    WHAT_WE_DO: 7,
    SCOPE: 8,
    YOUTUBE: 9,
    OPEN_QUESTION: 10,
    CHALLENGE: 11,
    SOLUTION: 12,
    GOOGLE_SLIDE: 13,
    LINKEDIN: 14,
    FACEBOOK: 15,
    THREADS: 16,
    INSTAGRAM: 17,
    WEB_EN: 18,
    WEB_TC: 19,
    WEB_JP: 20,
    SYNC_STATUS: 21,
    DRIVE_FOLDER: 22,
    HERO_PHOTO: 23,
    LOGO_BLACK: 24,
    LOGO_WHITE: 25,
    PROJECT_ID: 26,
    SORT_DATE: 27,
    FAQ_EN: 28,
    FAQ_TC: 29,
    FAQ_JP: 30
  }
};

var IMAGE_COLUMNS_ = [
  CONFIG.COL.DRIVE_FOLDER,
  CONFIG.COL.HERO_PHOTO,
  CONFIG.COL.LOGO_BLACK,
  CONFIG.COL.LOGO_WHITE
];

// ─── MENU ──────────────────────────────────────────────────

function onOpen() {
  SpreadsheetApp.getUi().createMenu('🔥 Firebean CMS')
    .addItem('Sync Changed Only', 'syncChangedToGitHub')
    .addItem('⚡ Sync Selected Project', 'syncSelectedProjectToGitHub')
    .addToUi();
}


// ─── STREAMLIT AUTO-SAVE ENDPOINT ──────────────────────────

function doPost(e) {
  try {
    var data = JSON.parse(e.postData.contents);
    if (data.action === 'sync_project') return syncProjectFromStreamlit(data);
    if (data.action === 'save_raw_input') return saveRawInput(data);
    
    return ContentService.createTextOutput(JSON.stringify({status: 'error', message: 'Unknown action'}))
      .setMimeType(ContentService.MimeType.JSON);
  } catch (err) {
    return ContentService.createTextOutput(JSON.stringify({status: 'error', message: err.toString()}))
      .setMimeType(ContentService.MimeType.JSON);
  }
}

function saveRawInput(data) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName('Raw_Input_DB') || ss.insertSheet('Raw_Input_DB');
  
  if (sheet.getLastRow() === 0) {
    sheet.appendRow(['Timestamp', 'Client', 'Project', 'Venue', 'ID']);
  }
  
  sheet.appendRow([
    new Date(),
    cleanSheetValue_(data.client_name),
    cleanSheetValue_(data.project_name),
    data.venue,
    data.project_id
  ]);
  
  return ContentService.createTextOutput(JSON.stringify({status: 'success'}))
    .setMimeType(ContentService.MimeType.JSON);
}

function cleanSheetValue_(val) {
  if (!val) return '';
  return String(val).replace(/[\r\n]+/g, ' ').replace(/\s{2,}/g, ' ').trim();
}
function formatSortDate_(val) {
  // Convert any date value to YYYY-MM-DD for consistent sorting
  if (!val) return '';
  try {
    var d = (val instanceof Date) ? val : new Date(String(val));
    if (isNaN(d.getTime())) return String(val).substring(0, 10);
    var y = d.getFullYear();
    var m = String(d.getMonth() + 1).padStart(2, '0');
    var day = String(d.getDate()).padStart(2, '0');
    return y + '-' + m + '-' + day;
  } catch (e) {
    return String(val).substring(0, 10);
  }
}

function syncProjectFromStreamlit(data) {
  var sheet = SpreadsheetApp.getActive().getSheetByName(CONFIG.SHEET_NAME);
  var sheetData = sheet.getDataRange().getValues();

  // ── Find or create row ────────────────────────────────────
  var targetRow = -1;
  for (var i = 1; i < sheetData.length; i++) {
    if (String(sheetData[i][CONFIG.COL.PROJECT_ID - 1]).toUpperCase() === String(data.project_id || '').toUpperCase()) {
      targetRow = i + 1;
      break;
    }
  }
  if (targetRow === -1) {
    targetRow = sheet.getLastRow() + 1;
    sheet.getRange(targetRow, CONFIG.COL.PROJECT_ID).setValue((data.project_id || '').toUpperCase());
  }

  // ── Basic fields ──────────────────────────────────────────
  sheet.getRange(targetRow, CONFIG.COL.CLIENT).setValue(cleanSheetValue_(data.client_name || ''));
  sheet.getRange(targetRow, CONFIG.COL.PROJECT).setValue(cleanSheetValue_(data.project_name || ''));
  sheet.getRange(targetRow, CONFIG.COL.DATE).setValue(data.date || '');
  sheet.getRange(targetRow, CONFIG.COL.VENUE).setValue(cleanSheetValue_(data.venue || ''));
  sheet.getRange(targetRow, CONFIG.COL.CATEGORY).setValue(data.category || '');
  sheet.getRange(targetRow, CONFIG.COL.WHAT_WE_DO).setValue(data.category_what || '');
  sheet.getRange(targetRow, CONFIG.COL.SCOPE).setValue(data.scope || '');
  sheet.getRange(targetRow, CONFIG.COL.YOUTUBE).setValue(data.youtube || '');
  sheet.getRange(targetRow, CONFIG.COL.OPEN_QUESTION).setValue(data.open_question || '');
  sheet.getRange(targetRow, CONFIG.COL.SORT_DATE).setValue(data.sort_date || '');
  sheet.getRange(targetRow, CONFIG.COL.CHALLENGE).setValue(data.challenge || '');
  sheet.getRange(targetRow, CONFIG.COL.SOLUTION).setValue(data.solution || '');

  // ── AI content — app.py sends as 'ai_content' ────────────
  // Support both 'ai_content' (app.py v7+) and 'ai_generated' (legacy)
  var ai = data.ai_content || data.ai_generated || {};
  sheet.getRange(targetRow, CONFIG.COL.GOOGLE_SLIDE).setValue(ai['1_google_slide'] || '');
  sheet.getRange(targetRow, CONFIG.COL.LINKEDIN).setValue(ai['5_linkedin_post'] || '');
  sheet.getRange(targetRow, CONFIG.COL.FACEBOOK).setValue(ai['2_facebook_post'] || '');
  sheet.getRange(targetRow, CONFIG.COL.THREADS).setValue(ai['3_threads_post'] || '');
  sheet.getRange(targetRow, CONFIG.COL.INSTAGRAM).setValue(ai['4_instagram_post'] || '');

  // ── Website articles — from ai['6_website'] ──────────────
  // Support both 'website_texts' (legacy) and ai_content['6_website'] (app.py)
  var website = data.website_texts || (ai['6_website'] ? ai['6_website'] : {});
  if (typeof website === 'object' && website !== null) {
    sheet.getRange(targetRow, CONFIG.COL.WEB_EN).setValue(website['en'] || '');
    sheet.getRange(targetRow, CONFIG.COL.WEB_TC).setValue(website['tc'] || '');
    sheet.getRange(targetRow, CONFIG.COL.WEB_JP).setValue(website['jp'] || '');
  } else if (typeof website === 'string') {
    sheet.getRange(targetRow, CONFIG.COL.WEB_EN).setValue(website);
  }

  // ── FAQ — app.py sends as faq_en/faq_tc/faq_jp directly ──
  // Support both flat fields (app.py) and nested faq_texts (legacy)
  var faqEn = data.faq_en || (data.faq_texts && data.faq_texts.en ? data.faq_texts.en : '');
  var faqTc = data.faq_tc || (data.faq_texts && data.faq_texts.tc ? data.faq_texts.tc : '');
  var faqJp = data.faq_jp || (data.faq_texts && data.faq_texts.jp ? data.faq_texts.jp : '');
  sheet.getRange(targetRow, CONFIG.COL.FAQ_EN).setValue(faqEn);
  sheet.getRange(targetRow, CONFIG.COL.FAQ_TC).setValue(faqTc);
  sheet.getRange(targetRow, CONFIG.COL.FAQ_JP).setValue(faqJp);

  // ── Images — save base64 to Drive then store Drive URLs ───
  // app.py sends: logo_black (base64), logo_white (base64), images[] (base64 array), hero_index
  var needsImageSync = false;
  var pid = (data.project_id || '').toUpperCase();
  var projectName = cleanSheetValue_(data.project_name || pid);
  var driveFolder = getOrCreateProjectFolder_(pid, projectName);

  if (driveFolder) {
    var folderUrl = 'https://drive.google.com/drive/folders/' + driveFolder.getId();
    var currentFolder = String(sheet.getRange(targetRow, CONFIG.COL.DRIVE_FOLDER).getValue() || '');
    if (currentFolder !== folderUrl) {
      sheet.getRange(targetRow, CONFIG.COL.DRIVE_FOLDER).setValue(folderUrl);
      needsImageSync = true;
    }

    // Save logo_black base64 to Drive
    if (data.logo_black) {
      var lbFile = saveBase64ToDrive_(driveFolder, 'Logo_Black.png', data.logo_black, 'image/png');
      if (lbFile) {
        sheet.getRange(targetRow, CONFIG.COL.LOGO_BLACK).setValue('https://drive.google.com/file/d/' + lbFile.getId());
        needsImageSync = true;
      }
    } else if (data.logo_black_id) {
      sheet.getRange(targetRow, CONFIG.COL.LOGO_BLACK).setValue('https://drive.google.com/file/d/' + data.logo_black_id);
    }

    // Save logo_white base64 to Drive
    if (data.logo_white) {
      var lwFile = saveBase64ToDrive_(driveFolder, 'Logo_White.png', data.logo_white, 'image/png');
      if (lwFile) {
        sheet.getRange(targetRow, CONFIG.COL.LOGO_WHITE).setValue('https://drive.google.com/file/d/' + lwFile.getId());
        needsImageSync = true;
      }
    } else if (data.logo_white_id) {
      sheet.getRange(targetRow, CONFIG.COL.LOGO_WHITE).setValue('https://drive.google.com/file/d/' + data.logo_white_id);
    }

    // Save photo images (base64 array) to Drive as Photo_1.jpg, Photo_2.jpg...
    if (data.images && data.images.length > 0) {
      var heroIndex = parseInt(data.hero_index || 0, 10);
      for (var pi = 0; pi < data.images.length; pi++) {
        var photoFile = saveBase64ToDrive_(driveFolder, 'Photo_' + (pi + 1) + '.jpg', data.images[pi], 'image/jpeg');
        if (photoFile && pi === heroIndex) {
          sheet.getRange(targetRow, CONFIG.COL.HERO_PHOTO).setValue('https://drive.google.com/file/d/' + photoFile.getId() + '/view?usp=drivesdk');
          needsImageSync = true;
        }
      }
      needsImageSync = true;
    } else if (data.hero_photo_id) {
      sheet.getRange(targetRow, CONFIG.COL.HERO_PHOTO).setValue('https://drive.google.com/file/d/' + data.hero_photo_id + '/view?usp=drivesdk');
    } else if (data.hero_photo_url) {
      sheet.getRange(targetRow, CONFIG.COL.HERO_PHOTO).setValue(data.hero_photo_url);
    }
  } else {
    // Fallback: no Drive folder, use IDs directly if provided
    if (data.logo_black_id) sheet.getRange(targetRow, CONFIG.COL.LOGO_BLACK).setValue('https://drive.google.com/file/d/' + data.logo_black_id);
    if (data.logo_white_id) sheet.getRange(targetRow, CONFIG.COL.LOGO_WHITE).setValue('https://drive.google.com/file/d/' + data.logo_white_id);
    if (data.hero_photo_id) sheet.getRange(targetRow, CONFIG.COL.HERO_PHOTO).setValue('https://drive.google.com/file/d/' + data.hero_photo_id);
    if (data.drive_folder_id) {
      sheet.getRange(targetRow, CONFIG.COL.DRIVE_FOLDER).setValue('https://drive.google.com/drive/folders/' + data.drive_folder_id);
      needsImageSync = true;
    }
  }

  // ── Sync status ───────────────────────────────────────────
  var currentStatus = String(sheet.getRange(targetRow, CONFIG.COL.SYNC_STATUS).getValue() || '').trim();
  if (currentStatus !== 'Pending (images)') {
    sheet.getRange(targetRow, CONFIG.COL.SYNC_STATUS).setValue(needsImageSync ? 'Pending (images)' : 'Pending');
  }

  return ContentService.createTextOutput(JSON.stringify({
    status: 'success',
    row: targetRow,
    project_id: pid,
    message: 'Data + images saved to Drive. Run CMS Sync to push to GitHub.'
  })).setMimeType(ContentService.MimeType.JSON);
}

// ─── HELPER: Get or create project folder in Drive ─────────
// Folder is named by Project Name, placed under Firebean Projects parent folder
// Parent folder ID: 1XT6c6zq-ipGN0sFRwpGl2GSVnaGsmSNg (Firebean Projects)
var FIREBEAN_PROJECTS_FOLDER_ID_ = '1XT6c6zq-ipGN0sFRwpGl2GSVnaGsmSNg';

function getOrCreateProjectFolder_(projectId, projectName) {
  try {
    var folderName = projectName || projectId; // Use project name, fallback to ID
    var parent;
    try {
      parent = DriveApp.getFolderById(FIREBEAN_PROJECTS_FOLDER_ID_);
    } catch (e2) {
      // Fallback: create/find root folder if parent ID is inaccessible
      var rootFolders = DriveApp.getFoldersByName('Firebean Projects');
      parent = rootFolders.hasNext() ? rootFolders.next() : DriveApp.createFolder('Firebean Projects');
    }
    // Search by project name first, then by project ID (for legacy folders)
    var subFolders = parent.getFoldersByName(folderName);
    if (subFolders.hasNext()) return subFolders.next();
    // Check if a folder named by project ID already exists (legacy)
    if (projectId && projectId !== folderName) {
      var legacyFolders = parent.getFoldersByName(projectId);
      if (legacyFolders.hasNext()) {
        var legacy = legacyFolders.next();
        legacy.setName(folderName); // Rename legacy ID-named folder to project name
        return legacy;
      }
    }
    return parent.createFolder(folderName);
  } catch (e) {
    Logger.log('getOrCreateProjectFolder_ error: ' + e.message);
    return null;
  }
}

// ─── HELPER: Save base64 string to Drive file ──────────────
function saveBase64ToDrive_(folder, filename, base64Data, mimeType) {
  try {
    // Remove data URL prefix if present (e.g. data:image/png;base64,...)
    var cleanBase64 = base64Data.replace(/^data:[^;]+;base64,/, '');
    var bytes = Utilities.base64Decode(cleanBase64);
    var blob = Utilities.newBlob(bytes, mimeType, filename);
    // Delete existing file with same name first to avoid duplicates
    var existing = folder.getFilesByName(filename);
    while (existing.hasNext()) { existing.next().setTrashed(true); }
    return folder.createFile(blob);
  } catch (e) {
    Logger.log('saveBase64ToDrive_ error for ' + filename + ': ' + e.message);
    return null;
  }
}


function markSelectedRowForImageSync() {
  var sheet = SpreadsheetApp.getActive().getSheetByName(CONFIG.SHEET_NAME);
  if (!sheet) return;

  var selection = SpreadsheetApp.getActive().getSelection();
  var ranges = selection.getActiveRangeList().getRanges();
  var markedRows = [];

  for (var r = 0; r < ranges.length; r++) {
    var startRow = ranges[r].getRow();
    var numRows = ranges[r].getNumRows();
    for (var row = startRow; row < startRow + numRows; row++) {
      if (row <= 1) continue;
      var projectName = String(sheet.getRange(row, CONFIG.COL.PROJECT).getValue() || '').trim();
      if (!projectName) continue;
      sheet.getRange(row, CONFIG.COL.SYNC_STATUS).setValue('Pending (images)');
      markedRows.push(projectName);
    }
  }

  if (markedRows.length === 0) {
    SpreadsheetApp.getUi().alert('No valid project rows selected.\nPlease select one or more project rows first.');
    return;
  }

  SpreadsheetApp.getUi().alert(markedRows.length + ' project(s) marked for image re-sync:\n\n' + 
    markedRows.map(function(n) { return '• ' + n; }).join('\n') + 
    '\n\nNow click "Sync Changed Only" to push updates.');
}

// ─── MAIN SYNC FUNCTIONS ──────────────────────────────────

function syncAllToGitHub() {
  var ui = SpreadsheetApp.getUi();
  var result = ui.alert('Sync ALL projects to GitHub?',
    'This will rebuild projects.json and re-check all images. Continue?',
    ui.ButtonSet.YES_NO);
  if (result !== ui.Button.YES) return;
  doSync(false);
}

function syncChangedToGitHub() {
  doSync(true);
}

function syncSelectedProjectToGitHub() {
  var sheet = SpreadsheetApp.getActive().getSheetByName(CONFIG.SHEET_NAME);
  var activeRange = sheet.getActiveRange();
  var selectedRow = activeRange.getRow();
  
  if (selectedRow <= 1) {
    SpreadsheetApp.getUi().alert('Please select a valid project row (row 2 or below).');
    return;
  }
  
  var projectName = String(sheet.getRange(selectedRow, CONFIG.COL.PROJECT).getValue() || '').trim();
  if (!projectName) {
    SpreadsheetApp.getUi().alert('Selected row does not contain a valid project name.');
    return;
  }
  
  var ui = SpreadsheetApp.getUi();
  var result = ui.alert('⚡ Sync Selected Project',
    'Sync only project: "' + projectName + '" to GitHub?\n\nThis is much faster than syncing all changes.',
    ui.ButtonSet.YES_NO);
    
  if (result !== ui.Button.YES) return;
  
  sheet.getRange(selectedRow, CONFIG.COL.SYNC_STATUS).setValue('Pending (images)');
  doSync(true, selectedRow);
}

function showProgress_(message, title) {
  try {
    SpreadsheetApp.getActive().toast(message, title || '🔥 Syncing...', 30);
  } catch(e) {}
}

function doSync(changedOnly, targetRowOnly) {
  var syncStart = new Date();
  showProgress_('Starting sync...', '🔥 CMS Sync');

  var token = getGitHubToken_();
  if (!token) {
    try { SpreadsheetApp.getUi().alert('GitHub token not found.\nGo to Project Settings > Script Properties and add GITHUB_TOKEN.'); } catch(e) {}
    return;
  }

  var sheet = SpreadsheetApp.getActive().getSheetByName(CONFIG.SHEET_NAME);
  var data = sheet.getDataRange().getValues();
  var projects = [];
  var imagesToPush = [];

  showProgress_('Loading image hashes from GitHub...', '🔥 CMS Sync');
  var existingHashes = loadImageHashes_(token);
  var existingProjects_ = loadExistingProjects_(token); // keyed by pid for gallery fallback
  var newHashes = {};
  var processedCount = 0;

  for (var i = 1; i < data.length; i++) {
    var rowNum = i + 1;
    var row = data[i];
    var syncStatus = String(row[CONFIG.COL.SYNC_STATUS - 1] || '').trim();
    var projectName = String(row[CONFIG.COL.PROJECT - 1] || '').trim();

    if (!projectName) continue;

    var projectId = String(row[CONFIG.COL.PROJECT_ID - 1] || '').trim();
    if (!projectId) projectId = 'proj-' + i;
    var pid = projectId.toLowerCase().replace(/[^a-z0-9]/g, '');

    var category = String(row[CONFIG.COL.CATEGORY - 1] || '').toUpperCase().trim();
    var whatWeDo = String(row[CONFIG.COL.WHAT_WE_DO - 1] || '').toUpperCase().trim();
    var categories = [];
    var filterSlugs = [];
    if (category) {
      categories.push(category);
      filterSlugs = filterSlugs.concat(categoryToSlugs_(category));
    }
    if (whatWeDo) {
      whatWeDo.split(',').forEach(function(w) {
        var wt = w.trim();
        if (wt) {
          categories.push(wt);
          filterSlugs = filterSlugs.concat(categoryToSlugs_(wt));
        }
      });
    }

    var logoBlackFileId = extractDriveFileId_(row[CONFIG.COL.LOGO_BLACK - 1]);
    var logoWhiteFileId = extractDriveFileId_(row[CONFIG.COL.LOGO_WHITE - 1]);
    var driveFolderId = extractDriveFolderId_(row[CONFIG.COL.DRIVE_FOLDER - 1]);
    var heroColValue = String(row[CONFIG.COL.HERO_PHOTO - 1] || '').trim();

    var logoBlackPath = logoBlackFileId ? CONFIG.IMAGES_PATH + '/' + pid + '-logo-black.webp' : '';
    var logoWhitePath = logoWhiteFileId ? CONFIG.IMAGES_PATH + '/' + pid + '-logo-white.webp' : '';

    var needsImageSync = false;
    var needsTextSync = false;

    if (targetRowOnly && rowNum !== targetRowOnly) {
      needsImageSync = false;
      needsTextSync = false;
    } else if (!changedOnly) {
      needsImageSync = true;
      needsTextSync = true;
    } else if (syncStatus === 'Pending (images)' || syncStatus === '') {
      needsImageSync = true;
      needsTextSync = true;
    } else if (syncStatus === 'Pending') {
      needsTextSync = true;
      needsImageSync = false;
    }

    var allFolderFiles = [];
    var galleryFiles = [];
    var heroFileId = '';

    if (driveFolderId && needsImageSync) {
      try {
        var folder = DriveApp.getFolderById(driveFolderId);
        var files = folder.getFiles();
        while (files.hasNext()) {
          var file = files.next();
          var fileName = file.getName();
          var mime = file.getMimeType();
          if (mime.indexOf('image/') !== 0) continue;
          var entry = {
            name: fileName,
            id: file.getId(),
            updated: file.getLastUpdated().getTime(),
            isHero: !!fileName.match(/^Hero_/i),
            isLogo: !!fileName.match(/^Logo_/i)
          };
          allFolderFiles.push(entry);
          if (!entry.isHero && !entry.isLogo) {
            galleryFiles.push(entry);
          }
        }
        galleryFiles.sort(function(a, b) { return a.name.localeCompare(b.name); });
      } catch (e) {
        Logger.log('Error listing Drive folder for ' + projectName + ': ' + e.message);
      }
    }

    if (needsImageSync) {
      heroFileId = resolveHeroFileId_(heroColValue, allFolderFiles, galleryFiles, projectName);
    } else {
      heroFileId = extractDriveFileId_(heroColValue);
    }

    var heroPath = heroFileId ? CONFIG.IMAGES_PATH + '/' + pid + '-hero.webp' : '';
    var heroSmPath = heroFileId ? CONFIG.IMAGES_PATH + '/' + pid + '-hero-sm.webp' : '';

    if (needsImageSync) {
      processedCount++;
      showProgress_('Processing images: ' + projectName, '🔥 CMS Sync');

      if (heroFileId) {
        pushIfChanged_(imagesToPush, existingHashes, newHashes, heroPath, heroFileId, CONFIG.HERO_WIDTH);
        pushIfChanged_(imagesToPush, existingHashes, newHashes, heroSmPath, heroFileId, CONFIG.HERO_SM_WIDTH);
      }
      if (logoBlackFileId) pushIfChanged_(imagesToPush, existingHashes, newHashes, logoBlackPath, logoBlackFileId, CONFIG.LOGO_WIDTH);
      if (logoWhiteFileId) pushIfChanged_(imagesToPush, existingHashes, newHashes, logoWhitePath, logoWhiteFileId, CONFIG.LOGO_WIDTH);
    } else {
      [heroPath, heroSmPath, logoBlackPath, logoWhitePath].forEach(function(p) {
        if (p && existingHashes[p]) newHashes[p] = existingHashes[p];
      });
    }

    var galleryPhotos = [];
    if (driveFolderId) {
      if (needsImageSync) {
        for (var g = 0; g < galleryFiles.length; g++) {
          var galleryPath = CONFIG.IMAGES_PATH + '/' + pid + '-gallery-' + g + '.webp';
          galleryPhotos.push(galleryPath);
          pushIfChanged_(imagesToPush, existingHashes, newHashes, galleryPath, galleryFiles[g].id, CONFIG.GALLERY_WIDTH);
        }
      } else {
        // Restore gallery paths from hash cache OR from existing projects.json
        var gIdx = 0;
        while (true) {
          var gPath = CONFIG.IMAGES_PATH + '/' + pid + '-gallery-' + gIdx + '.webp';
          if (existingHashes[gPath]) {
            galleryPhotos.push(gPath);
            newHashes[gPath] = existingHashes[gPath];
            gIdx++;
          } else {
            // Fallback: check if this gallery path exists in the existing JSON
            var existsInJson = false;
            if (existingProjects_) {
              var ep = existingProjects_[pid];
              if (ep && ep.galleryPhotos && ep.galleryPhotos.indexOf(gPath) !== -1) {
                existsInJson = true;
              }
            }
            if (existsInJson) {
              galleryPhotos.push(gPath);
              gIdx++;
            } else {
              break;
            }
          }
        }
      }
    }

    var project = {
      id: pid,
      index: i - 1,
      client: String(row[CONFIG.COL.CLIENT - 1] || ''),
      project: projectName,
      date: String(row[CONFIG.COL.DATE - 1] || ''),
      venue: String(row[CONFIG.COL.VENUE - 1] || ''),
      category: category,
      whatWeDo: whatWeDo,
      scope: String(row[CONFIG.COL.SCOPE - 1] || ''),
      youtube: String(row[CONFIG.COL.YOUTUBE - 1] || ''),
      challenge: String(row[CONFIG.COL.CHALLENGE - 1] || ''),
      solution: String(row[CONFIG.COL.SOLUTION - 1] || ''),
      linkedin: String(row[CONFIG.COL.LINKEDIN - 1] || ''),
      facebook: String(row[CONFIG.COL.FACEBOOK - 1] || ''),
      threads: String(row[CONFIG.COL.THREADS - 1] || ''),
      instagram: String(row[CONFIG.COL.INSTAGRAM - 1] || ''),
      webEN: String(row[CONFIG.COL.WEB_EN - 1] || ''),
      webTC: String(row[CONFIG.COL.WEB_TC - 1] || ''),
      webJP: String(row[CONFIG.COL.WEB_JP - 1] || ''),
      faqEN: String(row[CONFIG.COL.FAQ_EN - 1] || ''),
      faqTC: String(row[CONFIG.COL.FAQ_TC - 1] || ''),
      faqJP: String(row[CONFIG.COL.FAQ_JP - 1] || ''),
      heroPhoto: heroPath,
      heroPhotoSmall: heroSmPath,
      logoBlack: logoBlackPath,
      logoWhite: logoWhitePath,
      galleryPhotos: galleryPhotos,
      projectId: projectId,
      sortDate: formatSortDate_(row[CONFIG.COL.SORT_DATE - 1]),
      driveFolderId: driveFolderId || '',
      categories: categories,
      filterSlugs: filterSlugs
    };

    projects.push(project);
  }

  projects.sort(function(a, b) { return (b.sortDate || '').localeCompare(a.sortDate || ''); });
  projects.forEach(function(p, idx) { p.index = idx; });

  var projectsJson = JSON.stringify({ lastSync: new Date().toISOString(), projects: projects }, null, 2);
  var hashesJson = JSON.stringify(newHashes, null, 2);

  showProgress_('Pushing to GitHub: ' + imagesToPush.length + ' image(s) + projects.json', '🔥 Uploading');

  try {
    var filesPushed = pushToGitHubBatch_(token, imagesToPush, projectsJson, hashesJson);
    Logger.log('Pushed ' + filesPushed + ' files in single commit');
  } catch (e) {
    Logger.log('Push failed: ' + e.message);
    try { SpreadsheetApp.getUi().alert('Sync failed: ' + e.message); } catch(e2) {}
    return;
  }

  showProgress_('Updating sync status...', '🔥 Almost done');
  for (var k = 1; k < data.length; k++) {
    var rowNum = k + 1;
    if (targetRowOnly && rowNum !== targetRowOnly) continue;
    
    var rowPN = String(data[k][CONFIG.COL.PROJECT - 1] || '').trim();
    if (!rowPN) continue;
    var rowSS = String(data[k][CONFIG.COL.SYNC_STATUS - 1] || '').trim();
    if (!changedOnly || rowSS === 'Pending' || rowSS === 'Pending (images)' || rowSS === '') {
      sheet.getRange(k + 1, CONFIG.COL.SYNC_STATUS).setValue('Synced ' + new Date().toLocaleString());
    }
  }

  var elapsed = Math.round((new Date() - syncStart) / 1000);
  var msg = 'Sync complete! (' + elapsed + ' seconds)\n\n' +
    '• Projects: ' + projects.length + '\n' +
    '• New/updated images pushed: ' + imagesToPush.length + '\n\n' +
    'Website updates in ~1 min:\nhttps://cs627.github.io/Firebean-Website/';

  try { SpreadsheetApp.getUi().alert(msg); } catch(e) {}
}

// ─── GIT TREE API BATCH PUSH ──────────────────────────────

function pushToGitHubBatch_(token, images, projectsJson, hashesJson) {
  var baseUrl = 'https://api.github.com/repos/' + CONFIG.GITHUB_OWNER + '/' + CONFIG.GITHUB_REPO;
  var headers = { 'Authorization': 'token ' + token, 'Accept': 'application/vnd.github.v3+json' };

  var refResp = ghGet_(baseUrl + '/git/ref/heads/' + CONFIG.GITHUB_BRANCH, headers);
  var headSha = refResp.object.sha;
  var commitResp = ghGet_(baseUrl + '/git/commits/' + headSha, headers);
  var baseTreeSha = commitResp.tree.sha;

  var treeItems = [];

  for (var i = 0; i < images.length; i++) {
    var img = images[i];
    var blobSha = createBlob_(baseUrl, headers, img.base64, 'base64');
    if (blobSha) {
      treeItems.push({ path: img.path, mode: '100644', type: 'blob', sha: blobSha });
    }
    if (i > 0 && i % 10 === 0) Utilities.sleep(200);
  }

  var jsonBlobSha = createBlob_(baseUrl, headers, projectsJson, 'utf-8');
  if (jsonBlobSha) treeItems.push({ path: CONFIG.JSON_PATH, mode: '100644', type: 'blob', sha: jsonBlobSha });

  var hashesBlobSha = createBlob_(baseUrl, headers, hashesJson, 'utf-8');
  if (hashesBlobSha) treeItems.push({ path: CONFIG.HASH_PATH, mode: '100644', type: 'blob', sha: hashesBlobSha });

  if (treeItems.length === 0) return 0;

  var treeResp = ghPost_(baseUrl + '/git/trees', headers, { base_tree: baseTreeSha, tree: treeItems });
  var newTreeSha = treeResp.sha;

  var commitMsg = 'CMS sync: ' + images.length + ' images, ' + new Date().toISOString().replace('T', ' ').substring(0, 19);
  var newCommitResp = ghPost_(baseUrl + '/git/commits', headers, { message: commitMsg, tree: newTreeSha, parents: [headSha] });
  var newCommitSha = newCommitResp.sha;

  ghPatch_(baseUrl + '/git/refs/heads/' + CONFIG.GITHUB_BRANCH, headers, { sha: newCommitSha });

  return treeItems.length;
}

// ─── CHANGE DETECTION ──────────────────────────────────────

function pushIfChanged_(imagesToPush, existingHashes, newHashes, path, fileId, width) {
  if (!path || !fileId) return;
  try {
    var blob = downloadDriveImage_(fileId, width);
    if (!blob) return;

    var bytes = blob.getBytes();
    var hash = computeHash_(bytes);
    newHashes[path] = hash;

    if (existingHashes[path] === hash) return;

    imagesToPush.push({ path: path, base64: Utilities.base64Encode(bytes) });
  } catch (e) {
    Logger.log('  [ERROR] ' + path + ': ' + e.message);
  }
}

function loadImageHashes_(token) {
  var url = 'https://api.github.com/repos/' + CONFIG.GITHUB_OWNER + '/' + CONFIG.GITHUB_REPO + '/contents/' + CONFIG.HASH_PATH + '?ref=' + CONFIG.GITHUB_BRANCH;
  try {
    var resp = UrlFetchApp.fetch(url, {
      headers: { 'Authorization': 'token ' + token, 'Accept': 'application/vnd.github.v3+json' },
      muteHttpExceptions: true
    });
    if (resp.getResponseCode() === 200) {
      var data = JSON.parse(resp.getContentText());
      var content = Utilities.newBlob(Utilities.base64Decode(data.content)).getDataAsString();
      return JSON.parse(content);
    }
  } catch (e) {}
  return {};
}

function loadExistingProjects_(token) {
  // Returns a map of pid -> project object from the current projects.json on GitHub
  var url = 'https://api.github.com/repos/' + CONFIG.GITHUB_OWNER + '/' + CONFIG.GITHUB_REPO + '/contents/' + CONFIG.JSON_PATH + '?ref=' + CONFIG.GITHUB_BRANCH;
  try {
    var resp = UrlFetchApp.fetch(url, {
      headers: { 'Authorization': 'token ' + token, 'Accept': 'application/vnd.github.v3+json' },
      muteHttpExceptions: true
    });
    if (resp.getResponseCode() === 200) {
      var data = JSON.parse(resp.getContentText());
      var content = Utilities.newBlob(Utilities.base64Decode(data.content)).getDataAsString();
      var json = JSON.parse(content);
      var map = {};
      (json.projects || []).forEach(function(p) {
        if (p.id) map[p.id] = p;
      });
      return map;
    }
  } catch (e) {}
  return {};
}
function computeHash_(bytes) {
  var digest = Utilities.computeDigest(Utilities.DigestAlgorithm.MD5, bytes);
  return digest.map(function(b) {
    var hex = (b < 0 ? b + 256 : b).toString(16);
    return hex.length === 1 ? '0' + hex : hex;
  }).join('');
}

// ─── IMAGE DOWNLOAD ────────────────────────────────────────

function downloadDriveImage_(fileId, width) {
  try {
    var url = 'https://lh3.googleusercontent.com/d/' + fileId + '=w' + width;
    var oauthToken = ScriptApp.getOAuthToken();
    var resp = UrlFetchApp.fetch(url, { headers: { 'Authorization': 'Bearer ' + oauthToken }, muteHttpExceptions: true, followRedirects: true });

    if (resp.getResponseCode() === 200 && resp.getBlob().getBytes().length > 1000) return resp.getBlob();

    url = 'https://drive.google.com/thumbnail?id=' + fileId + '&sz=w' + width;
    resp = UrlFetchApp.fetch(url, { headers: { 'Authorization': 'Bearer ' + oauthToken }, muteHttpExceptions: true, followRedirects: true });

    if (resp.getResponseCode() === 200 && resp.getBlob().getBytes().length > 1000) return resp.getBlob();

    return DriveApp.getFileById(fileId).getBlob();
  } catch (e) {
    try { return DriveApp.getFileById(fileId).getBlob(); } catch (e2) { return null; }
  }
}

// ─── GITHUB API HELPERS ────────────────────────────────────

function ghGet_(url, headers) {
  var resp = UrlFetchApp.fetch(url, { headers: headers, muteHttpExceptions: true });
  if (resp.getResponseCode() !== 200) throw new Error('GET ' + url + ' → ' + resp.getResponseCode());
  return JSON.parse(resp.getContentText());
}

function ghPost_(url, headers, payload) {
  var resp = UrlFetchApp.fetch(url, { method: 'post', headers: headers, contentType: 'application/json', payload: JSON.stringify(payload), muteHttpExceptions: true });
  var code = resp.getResponseCode();
  if (code !== 200 && code !== 201) throw new Error('POST ' + url + ' → ' + code + ': ' + resp.getContentText().substring(0, 300));
  return JSON.parse(resp.getContentText());
}

function ghPatch_(url, headers, payload) {
  var resp = UrlFetchApp.fetch(url, { method: 'patch', headers: headers, contentType: 'application/json', payload: JSON.stringify(payload), muteHttpExceptions: true });
  if (resp.getResponseCode() !== 200) throw new Error('PATCH ' + url + ' → ' + resp.getResponseCode());
  return JSON.parse(resp.getContentText());
}

function createBlob_(baseUrl, headers, content, encoding) {
  var resp = ghPost_(baseUrl + '/git/blobs', headers, { content: content, encoding: encoding });
  return resp.sha;
}

// ─── UTILITY FUNCTIONS ─────────────────────────────────────

function getGitHubToken_() {
  return PropertiesService.getScriptProperties().getProperty('GITHUB_TOKEN');
}

function resolveHeroFileId_(heroColValue, allFolderFiles, galleryFiles, projectName) {
  var val = String(heroColValue || '').trim();

  if (!val) {
    for (var i = 0; i < allFolderFiles.length; i++) {
      if (allFolderFiles[i].isHero) return allFolderFiles[i].id;
    }
    if (galleryFiles.length > 0) return galleryFiles[0].id;
    return '';
  }

  if (val.match(/^\d+$/)) {
    var idx = parseInt(val, 10) - 1;
    if (idx >= 0 && idx < galleryFiles.length) return galleryFiles[idx].id;
    return resolveHeroFileId_('', allFolderFiles, galleryFiles, projectName);
  }

  if (val.match(/\.[a-zA-Z]{2,4}$/)) {
    var lowerVal = val.toLowerCase();
    for (var j = 0; j < allFolderFiles.length; j++) {
      if (allFolderFiles[j].name.toLowerCase() === lowerVal) return allFolderFiles[j].id;
    }
    var baseVal = lowerVal.replace(/\.[a-zA-Z]{2,4}$/, '');
    for (var k = 0; k < allFolderFiles.length; k++) {
      if (allFolderFiles[k].name.toLowerCase().replace(/\.[a-zA-Z]{2,4}$/, '') === baseVal) return allFolderFiles[k].id;
    }
    return resolveHeroFileId_('', allFolderFiles, galleryFiles, projectName);
  }

  var fileId = extractDriveFileId_(val);
  if (fileId) return fileId;

  var lowerVal2 = val.toLowerCase();
  for (var m = 0; m < allFolderFiles.length; m++) {
    if (allFolderFiles[m].name.toLowerCase().replace(/\.[a-zA-Z]{2,4}$/, '') === lowerVal2) return allFolderFiles[m].id;
  }

  return resolveHeroFileId_('', allFolderFiles, galleryFiles, projectName);
}

function extractDriveFileId_(url) {
  if (!url) return '';
  url = String(url).trim();
  var match = url.match(/\/d\/([a-zA-Z0-9_-]+)/);
  if (match) return match[1];
  match = url.match(/[?&]id=([a-zA-Z0-9_-]+)/);
  if (match) return match[1];
  if (url.match(/^[a-zA-Z0-9_-]{10,}$/)) return url;
  return '';
}

function extractDriveFolderId_(url) {
  if (!url) return '';
  url = String(url).trim();
  var match = url.match(/\/folders\/([a-zA-Z0-9_-]+)/);
  if (match) return match[1];
  if (url.match(/^[a-zA-Z0-9_-]{10,}$/)) return url;
  return '';
}

function categoryToSlugs_(cat) {
  var map = {
    'GOVERNMENT & PUBLIC SECTOR': ['government'],
    'LIFESTYLE & CONSUMER': ['lifestyle'],
    'F&B & HOSPITALITY': ['hospitality'],
    'MALLS & VENUES': ['venues'],
    'ROVING EXHIBITIONS': ['exhibitions'],
    'SOCIAL & CONTENT': ['social'],
    'INTERACTIVE & TECH': ['tech'],
    'PR & MEDIA': ['pr'],
    'EVENTS & CEREMONIES': ['events']
  };
  var slugs = [];
  for (var key in map) {
    if (cat.indexOf(key) !== -1) slugs = slugs.concat(map[key]);
  }
  return slugs;
}
