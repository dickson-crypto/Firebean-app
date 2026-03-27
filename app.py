/**
 * ============================================================
 * FIREBEAN CMS → GITHUB SYNC PIPELINE  v8.2 (Full Script Fix)
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

  // ── AI content ────────────────────────────────────────────
  var ai = data.ai_content || data.ai_generated || {};
  sheet.getRange(targetRow, CONFIG.COL.GOOGLE_SLIDE).setValue(ai['1_google_slide'] || '');
  sheet.getRange(targetRow, CONFIG.COL.LINKEDIN).setValue(ai['5_linkedin_post'] || '');
  sheet.getRange(targetRow, CONFIG.COL.FACEBOOK).setValue(ai['2_facebook_post'] || '');
  sheet.getRange(targetRow, CONFIG.COL.THREADS).setValue(ai['3_threads_post'] || '');
  sheet.getRange(targetRow, CONFIG.COL.INSTAGRAM).setValue(ai['4_instagram_post'] || '');

  // ── Website articles ──────────────────────────────────────
  var website = data.website_texts || (ai['6_website'] ? ai['6_website'] : {});
  if (typeof website === 'object' && website !== null) {
    sheet.getRange(targetRow, CONFIG.COL.WEB_EN).setValue(website['en'] || '');
    sheet.getRange(targetRow, CONFIG.COL.WEB_TC).setValue(website['tc'] || '');
    sheet.getRange(targetRow, CONFIG.COL.WEB_JP).setValue(website['jp'] || '');
  } else if (typeof website === 'string') {
    sheet.getRange(targetRow, CONFIG.COL.WEB_EN).setValue(website);
  }

  // ── FAQ — FIX: 確保安全寫入字串並防空 ──────────────────────
  var faqEn = data.faq_en ? String(data.faq_en) : '[]';
  var faqTc = data.faq_tc ? String(data.faq_tc) : '[]';
  var faqJp = data.faq_jp ? String(data.faq_jp) : '[]';
  
  sheet.getRange(targetRow, CONFIG.COL.FAQ_EN).setValue(faqEn);
  sheet.getRange(targetRow, CONFIG.COL.FAQ_TC).setValue(faqTc);
  sheet.getRange(targetRow, CONFIG.COL.FAQ_JP).setValue(faqJp);

  // ── Images — save base64 to Drive then store Drive URLs ───
  var needsImageSync = false;
  var pid = (data.project_id || '').toUpperCase();
  var projectName = cleanSheetValue_(data.project_name || (data.project_id ? data.project_id : pid));
  var driveFolder = getOrCreateProjectFolder_(pid, projectName);

  var allFolderFiles = [];
  var galleryFiles = [];

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

    // Save gallery images base64 to Drive
    if (data.images && data.images.length > 0) {
      data.images.forEach(function(b64, index) {
        var fileName = 'Photo_' + (index + 1) + '.webp';
        var file = saveBase64ToDrive_(driveFolder, fileName, b64, 'image/webp');
        if (file) {
          needsImageSync = true;
        }
      });
    }

    var driveFolderId = driveFolder.getId();
    var heroColValue = sheet.getRange(targetRow, CONFIG.COL.HERO_PHOTO).getValue();
    var heroFileId = '';

    if (driveFolderId) {
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

    // Resolve hero image
    if (data.images && data.images.length > 0) {
       heroFileId = resolveHeroFileId_(heroColValue, allFolderFiles, galleryFiles, projectName);
       if (heroFileId) {
          sheet.getRange(targetRow, CONFIG.COL.HERO_PHOTO).setValue('https://drive.google.com/file/d/' + heroFileId);
       }
    }
  }

  sheet.getRange(targetRow, CONFIG.COL.SYNC_STATUS).setValue('Pending (images)');

  return ContentService.createTextOutput(JSON.stringify({status: 'success'}))
    .setMimeType(ContentService.MimeType.JSON);
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
  var url = 'https://api.github.com/repos/' + CONFIG.GITHUB_OWNER + '/' + CONFIG.GITHUB_REPO + '/contents/' + CONFIG.JSON_PATH + '?ref=' + CONFIG.GITHUB_BRANCH;
  try {
    var resp = UrlFetchApp.fetch(url, {
      headers: { 'Authorization': 'token ' + token, 'Accept': 'application/vnd.github.v3+json' },
      muteHttpExceptions: true
    });
    if (resp.getResponseCode() === 200) {
      var data = JSON.parse(resp.getContentText());
      var content = Utilities.newBlob(Utilities.base64Decode(data.content)).getDataAsString();
      var projects = JSON.parse(content).projects;
      var projectMap = {};
      projects.forEach(function(p) { projectMap[p.id] = p; });
      return projectMap;
    }
  } catch (e) {}
  return {};
}

// ─── DRIVE HELPERS ─────────────────────────────────────────

function getOrCreateProjectFolder_(pid, projectName) {
  var parentFolder = DriveApp.getFoldersByName('Firebean Projects');
  if (!parentFolder.hasNext()) {
    throw new Error('Parent folder "Firebean Projects" not found in Google Drive.');
  }
  var firebeanProjectsFolder = parentFolder.next();

  var folders = firebeanProjectsFolder.getFoldersByName(projectName);
  if (folders.hasNext()) {
    return folders.next();
  } else {
    return firebeanProjectsFolder.createFolder(projectName);
  }
}

function saveBase64ToDrive_(folder, fileName, base64Data, mimeType) {
  try {
    // 🛡️ 安全清洗 Base64 (防止前綴崩潰)
    var rawStr = String(base64Data).indexOf('base64,') > -1 ? String(base64Data).split('base64,')[1] : base64Data;
    var blob = Utilities.newBlob(Utilities.base64Decode(rawStr), mimeType, fileName);
    var files = folder.getFilesByName(fileName);
    if (files.hasNext()) {
      var file = files.next();
      file.setContent(blob.getDataAsString()); // Update existing file
      return file;
    } else {
      return folder.createFile(blob);
    }
  } catch (e) {
    Logger.log('Error saving ' + fileName + ' to Drive: ' + e.message);
    return null;
  }
}

function downloadDriveImage_(fileId, width) {
  var oauthToken = ScriptApp.getOAuthToken();
  try {
    var url = 'https://drive.google.com/thumbnail?id=' + fileId + '&sz=w' + width;
    var resp = UrlFetchApp.fetch(url, { headers: { 'Authorization': 'Bearer ' + oauthToken }, muteHttpExceptions: true, followRedirects: true });
    if (resp.getResponseCode() === 200 && resp.getBlob().getBytes().length > 1000) return resp.getBlob();
    return DriveApp.getFileById(fileId).getBlob();
  } catch (e) {
    try { return DriveApp.getFileById(fileId).getBlob(); } catch (e2) { return null; }
  }
}

function extractDriveFileId_(url) {
  var match = url.match(/id=([a-zA-Z0-9_-]+)/) || url.match(/d\/([a-zA-Z0-9_-]+)/);
  return match ? match[1] : null;
}

function resolveHeroFileId_(heroColValue, allFolderFiles, galleryFiles, projectName) {
  var val = String(heroColValue || '').trim();
  var driveId = extractDriveFileId_(val);
  if (driveId) return driveId;

  if (val.match(/^\d+$/)) {
    var index = parseInt(val) - 1; // 1-based index
    if (index >= 0 && index < galleryFiles.length) {
      return galleryFiles[index].id;
    }
  }

  for (var i = 0; i < allFolderFiles.length; i++) {
    if (allFolderFiles[i].name.toLowerCase() === val.toLowerCase()) {
      return allFolderFiles[i].id;
    }
  }

  for (var i = 0; i < allFolderFiles.length; i++) {
    if (allFolderFiles[i].isHero) return allFolderFiles[i].id;
  }

  if (galleryFiles.length > 0) {
    return galleryFiles[0].id;
  }

  Logger.log('Could not resolve hero photo for project: ' + projectName + ' with value: ' + heroColValue);
  return '';
}

// ─── UI HELPERS ────────────────────────────────────────────

function showProgress_(title, msg) {
  try {
    SpreadsheetApp.getUi().showSidebar(HtmlService.createHtmlOutput('<p>' + msg + '</p>').setTitle(title));
  } catch (e) {
    Logger.log('Progress: ' + title + ' - ' + msg);
  }
}

function closeProgress_() {
  try {
    SpreadsheetApp.getUi().showSidebar(HtmlService.createHtmlOutput(''));
  } catch (e) {
    Logger.log('Progress closed.');
  }
}

// ─── SYNC FUNCTIONS ────────────────────────────────────────

function syncChangedToGitHub() {
  syncProjectsToGitHub_(true, null);
}

function syncSelectedProjectToGitHub() {
  var sheet = SpreadsheetApp.getActive().getSheetByName(CONFIG.SHEET_NAME);
  var activeRange = sheet.getActiveRange();
  var row = activeRange.getRow();
  syncProjectsToGitHub_(false, row);
}

function syncProjectsToGitHub_(changedOnly, targetRowOnly) {
  var token = getGitHubToken_();
  if (!token) {
    SpreadsheetApp.getUi().alert('GitHub token not set. Please go to Project Settings > Script Properties and add GITHUB_TOKEN.');
    return;
  }

  var syncStart = new Date();
  var sheet = SpreadsheetApp.getActive().getSheetByName(CONFIG.SHEET_NAME);
  var data = sheet.getDataRange().getValues();
  var headers = data[0];

  var projects = [];
  var imagesToPush = [];
  var existingHashes = loadImageHashes_(token);
  var newHashes = {};
  var existingProjects_ = loadExistingProjects_(token);
  var processedCount = 0;

  for (var i = 1; i < data.length; i++) {
    var row = data[i];
    var rowNum = i + 1;

    if (targetRowOnly && rowNum !== targetRowOnly) continue;

    var pid = String(row[CONFIG.COL.PROJECT_ID - 1] || '').toUpperCase();
    var projectName = cleanSheetValue_(row[CONFIG.COL.PROJECT - 1] || pid);
    if (!pid) continue; // Skip rows without Project ID

    var syncStatus = String(row[CONFIG.COL.SYNC_STATUS - 1] || '').trim();
    var needsImageSync = (syncStatus === 'Pending (images)' || syncStatus === '');

    if (changedOnly && syncStatus.indexOf('Pending') === -1 && syncStatus !== '') continue; // Only sync pending or new

    showProgress_('Processing: ' + projectName, '🔥 CMS Sync');

    var category = String(row[CONFIG.COL.CATEGORY - 1] || '').trim();
    var whatWeDo = String(row[CONFIG.COL.WHAT_WE_DO - 1] || '').trim();

    var categories = category ? category.split(',').map(function(s) { return s.trim(); }) : [];
    var whatWeDos = whatWeDo ? whatWeDo.split(',').map(function(s) { return s.trim(); }) : [];
    var filterSlugs = categories.concat(whatWeDos).map(function(s) { return s.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-*|-*$/g, ''); });

    var driveFolder = getOrCreateProjectFolder_(pid, projectName);
    var driveFolderId = driveFolder ? driveFolder.getId() : null;

    // Update DRIVE_FOLDER column with URL
    if (driveFolderId) {
      var folderUrl = 'https://drive.google.com/drive/folders/' + driveFolderId;
      sheet.getRange(rowNum, CONFIG.COL.DRIVE_FOLDER).setValue(folderUrl);
    }

    var allFolderFiles = [];
    var galleryFiles = [];
    if (driveFolderId) {
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

    // Save logo_black base64 to Drive
    var logoBlackFileId = null;
    if (row[CONFIG.COL.LOGO_BLACK - 1] && String(row[CONFIG.COL.LOGO_BLACK - 1]).startsWith('data:image')) {
      var lbFile = saveBase64ToDrive_(driveFolder, 'Logo_Black.png', String(row[CONFIG.COL.LOGO_BLACK - 1]).split(',')[1], 'image/png');
      if (lbFile) {
        logoBlackFileId = lbFile.getId();
        sheet.getRange(rowNum, CONFIG.COL.LOGO_BLACK).setValue('https://drive.google.com/file/d/' + logoBlackFileId);
        needsImageSync = true;
      }
    } else if (extractDriveFileId_(String(row[CONFIG.COL.LOGO_BLACK - 1] || ''))) {
      logoBlackFileId = extractDriveFileId_(String(row[CONFIG.COL.LOGO_BLACK - 1]));
    }
    var logoBlackPath = logoBlackFileId ? CONFIG.IMAGES_PATH + '/' + pid + '-logo-black.webp' : '';

    // Save logo_white base64 to Drive
    var logoWhiteFileId = null;
    if (row[CONFIG.COL.LOGO_WHITE - 1] && String(row[CONFIG.COL.LOGO_WHITE - 1]).startsWith('data:image')) {
      var lwFile = saveBase64ToDrive_(driveFolder, 'Logo_White.png', String(row[CONFIG.COL.LOGO_WHITE - 1]).split(',')[1], 'image/png');
      if (lwFile) {
        logoWhiteFileId = lwFile.getId();
        sheet.getRange(rowNum, CONFIG.COL.LOGO_WHITE).setValue('https://drive.google.com/file/d/' + logoWhiteFileId);
        needsImageSync = true;
      }
    } else if (extractDriveFileId_(String(row[CONFIG.COL.LOGO_WHITE - 1] || ''))) {
      logoWhiteFileId = extractDriveFileId_(String(row[CONFIG.COL.LOGO_WHITE - 1]));
    }
    var logoWhitePath = logoWhiteFileId ? CONFIG.IMAGES_PATH + '/' + pid + '-logo-white.webp' : '';

    // Resolve Hero Photo
    var heroPhotoFileId = null;
    var heroColValue = sheet.getRange(rowNum, CONFIG.COL.HERO_PHOTO).getValue();
    var heroPhotoUrl = "";

    if (heroColValue) {
      heroPhotoFileId = resolveHeroFileId_(heroColValue, allFolderFiles, galleryFiles, projectName);
      if (heroPhotoFileId && heroPhotoFileId !== '__CACHED__') {
        heroPhotoUrl = 'https://drive.google.com/file/d/' + heroPhotoFileId;
        needsImageSync = true;
      } else if (heroPhotoFileId === '__CACHED__') {
        heroPhotoUrl = String(sheet.getRange(rowNum, CONFIG.COL.HERO_PHOTO).getValue() || '');
      }
    }
    sheet.getRange(rowNum, CONFIG.COL.HERO_PHOTO).setValue(heroPhotoUrl);

    var heroPath = heroPhotoFileId && heroPhotoFileId !== '__CACHED__' ? CONFIG.IMAGES_PATH + '/' + pid + '-hero.webp' : '';
    var heroSmPath = heroPhotoFileId && heroPhotoFileId !== '__CACHED__' ? CONFIG.IMAGES_PATH + '/' + pid + '-hero-sm.webp' : '';

    if (needsImageSync) {
      processedCount++;
      showProgress_('Processing images: ' + projectName, '🔥 CMS Sync');

      if (heroPhotoFileId && heroPhotoFileId !== '__CACHED__') {
        pushIfChanged_(imagesToPush, existingHashes, newHashes, heroPath, heroPhotoFileId, CONFIG.HERO_WIDTH);
        pushIfChanged_(imagesToPush, existingHashes, newHashes, heroSmPath, heroPhotoFileId, CONFIG.HERO_SM_WIDTH);
      }
      if (logoBlackFileId) pushIfChanged_(imagesToPush, existingHashes, newHashes, logoBlackPath, logoBlackFileId, CONFIG.LOGO_WIDTH);
      if (logoWhiteFileId) pushIfChanged_(imagesToPush, existingHashes, newHashes, logoWhitePath, logoWhiteFileId, CONFIG.LOGO_WIDTH);
    } else {
      if (heroPhotoFileId === '__CACHED__') {
        heroPath = CONFIG.IMAGES_PATH + '/' + pid + '-hero.webp';
        heroSmPath = CONFIG.IMAGES_PATH + '/' + pid + '-hero-sm.webp';
      }
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
      }
      var gIdx = 0;
      while (true) {
        var gPath = CONFIG.IMAGES_PATH + '/' + pid + '-gallery-' + gIdx + '.webp';
        if (existingHashes[gPath]) {
          galleryPhotos.push(gPath);
          newHashes[gPath] = existingHashes[gPath];
          gIdx++;
        } else {
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
      faqEN: String(row[CONFIG.COL.FAQ_EN - 1] || '[]'),
      faqTC: String(row[CONFIG.COL.FAQ_TC - 1] || '[]'),
      faqJP: String(row[CONFIG.COL.FAQ_JP - 1] || '[]'),
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

function computeHash_(bytes) {
  var digest = Utilities.computeDigest(Utilities.DigestAlgorithm.MD5, bytes);
  var hexDigest = '';
  for (var i = 0; i < digest.length; i++) {
    var byte = digest[i];
    if (byte < 0) byte += 256;
    hexDigest += (byte < 16 ? '0' : '') + byte.toString(16);
  }
  return hexDigest;
}

function getMimeType(b64) {
  if (b64.startsWith('/9j/')) return 'image/jpeg';
  if (b64.startsWith('iVBORw')) return 'image/png';
  if (b64.startsWith('R0lGOD')) return 'image/gif';
  return 'image/png';
}
