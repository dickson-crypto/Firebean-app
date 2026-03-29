/**
 * ============================================================
 * SCRIPT 2 of 3 — MASTER DB SLIDE CREATOR  v10.0
 * ============================================================
 * Deploy URL:  https://script.google.com/macros/s/AKfycbx_7Xf8_HERQel93WJB2F_KjFOWHtCXzfvEkP9B_p7Kh4ImRAWRgWSXtLklvdbYsqbI/exec
 * app.py var:  SLIDE_DB_URL
 * Action:      create_slide
 *
 * v10.0 fixes vs v9.0:
 *   - Drive URL: thumbnail?sz=s4000 instead of uc?export=download (no redirect)
 *   - replaceAllText scoped to [newId1, newId2] only — never touches template slides
 *   - Grid cells overlap by 1pt on all sides — eliminates white gap between cells
 *   - Master deck is preserved: new project slides are appended to end of template
 * ============================================================
 */

var TEMPLATE_ID = '19rmqCzgKD8y2ZiLxkiAqhhkV6_t-8QAumZkSi0Eu9C0';
var SHEET_ID    = '1aTuqgmmSKMWgNCl2KR0QhK4Cj8G7W5yPsr4t39pi-yc';
var SHEET_NAME  = 'Basic Info';

// Photo grid positions in EMU (1pt = 12700 EMU)
// Right panel: x=210.6pt, y=0, w=509.4pt, h=405pt (confirmed from template API)
// 2 cols x 2 rows. Each cell: ~254.7pt wide x 202.5pt tall
// Bleed 5pt on every edge so images always overlap borders — zero white gaps
var PT = 12700;
var PHOTO_EMU = {
  'PHOTO1': {l:205*PT, t:-5*PT,    w:265*PT, h:213*PT},
  'PHOTO2': {l:460*PT, t:-5*PT,    w:265*PT, h:213*PT},
  'PHOTO3': {l:205*PT, t:197*PT,   w:265*PT, h:213*PT},
  'PHOTO4': {l:460*PT, t:197*PT,   w:265*PT, h:213*PT},
  'PHOTO5': {l:205*PT, t:-5*PT,    w:265*PT, h:213*PT},
  'PHOTO6': {l:460*PT, t:-5*PT,    w:265*PT, h:213*PT},
  'PHOTO7': {l:205*PT, t:197*PT,   w:265*PT, h:213*PT},
  'PHOTO8': {l:460*PT, t:197*PT,   w:265*PT, h:213*PT}
};
var LOGO_EMU = {l:24.3*PT, t:25.5*PT, w:166.2*PT, h:71.6*PT};

// ─── ENTRY POINT ─────────────────────────────────────────────────────────────

function doPost(e) {
  try {
    var data = JSON.parse(e.postData.contents);
    if (data.action === 'create_slide' || data.action === 'create_case_study') {
      return createCaseStudySlide_(data);
    }
    return ContentService
      .createTextOutput(JSON.stringify({status:'error', message:'Unknown action: '+data.action}))
      .setMimeType(ContentService.MimeType.JSON);
  } catch(err) {
    return ContentService
      .createTextOutput(JSON.stringify({status:'error', message:err.toString()}))
      .setMimeType(ContentService.MimeType.JSON);
  }
}

// ─── MAIN ────────────────────────────────────────────────────────────────────

function createCaseStudySlide_(data) {
  var token   = ScriptApp.getOAuthToken();
  var apiBase = 'https://slides.googleapis.com/v1/presentations/' + TEMPLATE_ID;
  // Master deck: new slides are appended here, so the URL always points to this file
  var slideUrl = 'https://docs.google.com/presentation/d/' + TEMPLATE_ID + '/edit';

  // ── STEP 1: Read template — get slide 1 & 2 objectIds ────────────────────────
  var getResp = UrlFetchApp.fetch(apiBase, {
    headers: {'Authorization': 'Bearer ' + token}, muteHttpExceptions: true
  });
  if (getResp.getResponseCode() !== 200) throw new Error('GET pres failed: ' + getResp.getResponseCode());

  var pres   = JSON.parse(getResp.getContentText());
  var tmpl1  = pres.slides[0];
  var tmpl2  = pres.slides[1];
  if (!tmpl1 || !tmpl2) throw new Error('Template must have at least 2 slides');

  // ── STEP 2: Duplicate slides 1 & 2, then move them to position 3 & 4 ──────────
  // duplicateObject always appends at end — we move them into position afterwards
  var dupResp = UrlFetchApp.fetch(apiBase + ':batchUpdate', {
    method: 'post', contentType: 'application/json',
    headers: {'Authorization': 'Bearer ' + token},
    payload: JSON.stringify({requests: [
      {duplicateObject: {objectId: tmpl1.objectId}},
      {duplicateObject: {objectId: tmpl2.objectId}}
    ]}),
    muteHttpExceptions: true
  });
  if (dupResp.getResponseCode() !== 200) throw new Error('Duplicate failed: ' + dupResp.getContentText().substring(0, 300));

  var dupResult = JSON.parse(dupResp.getContentText());
  var newId1    = dupResult.replies[0].duplicateObject.objectId;
  var newId2    = dupResult.replies[1].duplicateObject.objectId;
  Logger.log('New slide IDs: ' + newId1 + ', ' + newId2);

  // Move both new slides to index 2 (= position 3) right after the 2 template slides
  // Move newId1 to index 2 first, then newId2 to index 3
  Utilities.sleep(500);
  var moveResp = UrlFetchApp.fetch(apiBase + ':batchUpdate', {
    method: 'post', contentType: 'application/json',
    headers: {'Authorization': 'Bearer ' + token},
    payload: JSON.stringify({requests: [
      {updateSlidesPosition: {slideObjectIds: [newId1, newId2], insertionIndex: 2}}
    ]}),
    muteHttpExceptions: true
  });
  if (moveResp.getResponseCode() !== 200) Logger.log('Move warning: ' + moveResp.getContentText().substring(0,200));
  Logger.log('Moved new slides to position 3 & 4');

  // ── STEP 3: Re-read to get element IDs of the new slides ─────────────────────
  Utilities.sleep(1000);
  getResp = UrlFetchApp.fetch(apiBase, {
    headers: {'Authorization': 'Bearer ' + token}, muteHttpExceptions: true
  });
  pres = JSON.parse(getResp.getContentText());

  var newSlideData1 = null, newSlideData2 = null;
  pres.slides.forEach(function(s) {
    if (s.objectId === newId1) newSlideData1 = s;
    if (s.objectId === newId2) newSlideData2 = s;
  });
  if (!newSlideData1 || !newSlideData2) throw new Error('Could not find new slides: ' + newId1 + ', ' + newId2);

  // ── STEP 4: Collect image IDs + logo shape ID on the new slides ───────────────
  var deleteIds = [];
  var newLogoId = null;

  (newSlideData1.pageElements || []).forEach(function(el) {
    if (el.image) deleteIds.push(el.objectId);  // delete ALL images on new slide 1
    if (el.shape && (el.description === 'project_logo' || el.title === 'photo1_placeholder')) {
      newLogoId = el.objectId;
    }
  });
  (newSlideData2.pageElements || []).forEach(function(el) {
    if (el.image) deleteIds.push(el.objectId);  // delete ALL images on new slide 2
  });
  Logger.log('Deleting ' + deleteIds.length + ' images. Logo shape: ' + newLogoId);

  // ── STEP 5: Build mega batchUpdate ────────────────────────────────────────────
  var requests = [];

  // a) Delete all copied template images from new slides
  deleteIds.forEach(function(id) {
    requests.push({deleteObject: {objectId: id}});
  });

  // b) Delete logo placeholder shape (replaced with real logo image below)
  if (newLogoId) requests.push({deleteObject: {objectId: newLogoId}});

  // c) Replace text — scoped to new slides only so template originals are never touched
  var dateStr  = (data.date || ((data.event_month || '') + ' ' + (data.event_year || ''))).trim();
  var scopeStr = Array.isArray(data.scope) ? data.scope.join('\n') : String(data.scope || '').replace(/,\s*/g, '\n');
  var textPairs = [
    ['{{CLIENT_NAME}}',  data.client_name  || ''],
    ['{{PROJECT_NAME}}', data.project_name || ''],
    ['{{CATEGORY}}',     data.category     || ''],
    ['{{DATE}}',         dateStr],
    ['{{VENUE}}',        data.venue        || ''],
    ['{{SCOPE}}',        scopeStr],
    ['{{CHALLENGE}}',    data.challenge    || '(Challenge TBC)'],
    ['{{SOLUTION}}',     data.solution     || '(Solution TBC)']
  ];
  textPairs.forEach(function(pair) {
    requests.push({replaceAllText: {
      containsText: {text: pair[0], matchCase: true},
      replaceText:  pair[1],
      pageObjectIds: [newId1, newId2]   // ← only new slides, template untouched
    }});
  });

  // d) Upload photos — size image to COVER cell, centred (true object-fit:cover)
  var photos      = data.photos || data.images || [];
  var photoResults = [];
  var tempFolder  = getOrCreateTempFolder_();

  for (var i = 0; i < Math.min(photos.length, 8); i++) {
    var photoNum = i + 1;
    var altText  = 'PHOTO' + photoNum;
    var slideId  = photoNum <= 4 ? newId1 : newId2;
    var pos      = PHOTO_EMU[altText];

    try {
      var imgDims = getBase64ImageDimensions_(photos[i]);
      var url     = saveBase64ToPublicDrive_(tempFolder, 'ph' + photoNum + '.jpg', photos[i], 'image/jpeg');
      // Cover transform: scale image so it fills cell on BOTH axes, centre it
      // The image extends beyond cell edges — clipped naturally by slide bounds
      var cover = calcCoverTransform_(imgDims.w, imgDims.h, pos.w, pos.h, pos.l, pos.t);
      requests.push({createImage: {
        url:      url,
        objectId: 'NEWPHOTO_' + photoNum + '_' + newId1.replace(/[^a-z0-9]/gi, ''),
        elementProperties: {
          pageObjectId: slideId,
          size:      {width:  {magnitude: cover.w, unit: 'EMU'},
                      height: {magnitude: cover.h, unit: 'EMU'}},
          transform: {scaleX: 1, scaleY: 1,
                      translateX: cover.x, translateY: cover.y, unit: 'EMU'}
        }
      }});
      photoResults.push(altText + ':OK');
    } catch(pe) {
      Logger.log('Photo ' + photoNum + ' error: ' + pe.message);
      photoResults.push(altText + ':FAIL:' + pe.message);
    }
  }

  // e) Logo image
  var logoResult = 'no_logo';
  var logoBase64 = data.logo_white_base64 || data.logo_white || '';
  if (logoBase64) {
    try {
      var logoUrl = saveBase64ToPublicDrive_(tempFolder, 'logo_white.png', logoBase64, 'image/png');
      requests.push({createImage: {
        url:      logoUrl,
        objectId: 'NEWLOGO_' + newId1.replace(/[^a-z0-9]/gi, ''),
        elementProperties: {
          pageObjectId: newId1,
          size:      {width:  {magnitude: LOGO_EMU.w, unit: 'EMU'},
                      height: {magnitude: LOGO_EMU.h, unit: 'EMU'}},
          transform: {scaleX: 1, scaleY: 1,
                      translateX: LOGO_EMU.l, translateY: LOGO_EMU.t, unit: 'EMU'}
        }
      }});
      logoResult = 'OK';
    } catch(le) {
      Logger.log('Logo error: ' + le.message);
      logoResult = 'FAIL:' + le.message;
    }
  }

  // ── STEP 6: Execute the mega batchUpdate ──────────────────────────────────────
  Utilities.sleep(500);
  var batchResp = UrlFetchApp.fetch(apiBase + ':batchUpdate', {
    method: 'post', contentType: 'application/json',
    headers: {'Authorization': 'Bearer ' + token},
    payload: JSON.stringify({requests: requests}),
    muteHttpExceptions: true
  });
  if (batchResp.getResponseCode() !== 200) {
    Logger.log('batchUpdate FAILED: ' + batchResp.getContentText().substring(0, 500));
    throw new Error('batchUpdate failed: ' + batchResp.getResponseCode() + ': ' + batchResp.getContentText().substring(0, 200));
  }
  Logger.log('batchUpdate OK: ' + requests.length + ' requests');

  // ── STEP 7: Write slide URL to Master DB col M ────────────────────────────────
  updateSheetWithSlideUrl_(data.project_id, slideUrl);

  return ContentService.createTextOutput(JSON.stringify({
    status: 'success', slide_url: slideUrl,
    photos: photoResults, logo: logoResult,
    requests_sent: requests.length,
    new_slides: [newId1, newId2]
  })).setMimeType(ContentService.MimeType.JSON);
}

// ─── COVER TRANSFORM (object-fit:cover equivalent) ─────────────────────────
// Scales image so it fully covers the cell on both axes, centred.
// Image is placed larger than cell — slide boundary clips the overflow.
// Works correctly even when imgW/imgH are 0 (unknown dims).
function calcCoverTransform_(imgW, imgH, cellW, cellH, cellX, cellY) {
  var w, h, x, y;
  if (!imgW || !imgH) {
    // Unknown dimensions: just fill the cell exactly (no crop, may stretch slightly)
    return {w: cellW, h: cellH, x: cellX, y: cellY};
  }
  var scaleW = cellW / imgW;   // scale needed to fill width
  var scaleH = cellH / imgH;   // scale needed to fill height
  var scale  = Math.max(scaleW, scaleH);  // cover = use the LARGER scale
  w = imgW * scale;
  h = imgH * scale;
  x = cellX - (w - cellW) / 2;  // centre horizontally
  y = cellY - (h - cellH) / 2;  // centre vertically
  return {w: w, h: h, x: x, y: y};
}

// ─── CROP MATH (kept for reference) ──────────────────────────────────────────

function calcCropCentre_(imgW, imgH, frameW, frameH) {
  if (!imgW || !imgH) return {leftOffset: 0, rightOffset: 0, topOffset: 0, bottomOffset: 0};
  var ia = imgW / imgH, fa = frameW / frameH;
  var l = 0, r = 0, t = 0, b = 0;
  if (ia > fa) { var sw = imgW * (frameH / imgH), f = (sw - frameW) / sw; l = f / 2; r = f / 2; }
  else if (ia < fa) { var sh = imgH * (frameW / imgW), f = (sh - frameH) / sh; t = f / 2; b = f / 2; }
  return {
    leftOffset:   Math.max(0, Math.min(0.49, l)),
    rightOffset:  Math.max(0, Math.min(0.49, r)),
    topOffset:    Math.max(0, Math.min(0.49, t)),
    bottomOffset: Math.max(0, Math.min(0.49, b))
  };
}

// ─── IMAGE DIMENSIONS ─────────────────────────────────────────────────────────

function getBase64ImageDimensions_(base64Data) {
  try {
    var clean = String(base64Data).replace(/^data:[^;]+;base64,/, '').replace(/\s/g, '');
    var bytes = Utilities.base64Decode(clean.substring(0, 32));
    if (bytes[0] === 0xFF && bytes[1] === 0xD8) {
      var fb = Utilities.base64Decode(clean.substring(0, 600));
      for (var i = 2; i < fb.length - 9; i++) {
        if (fb[i] === 0xFF && (fb[i+1] === 0xC0 || fb[i+1] === 0xC1 || fb[i+1] === 0xC2 || fb[i+1] === 0xC3))
          return {w: (fb[i+7] << 8) | fb[i+8], h: (fb[i+5] << 8) | fb[i+6]};
      }
    }
    if (bytes[0] === 0x89 && bytes[1] === 0x50) {
      var pb = Utilities.base64Decode(clean.substring(0, 64));
      return {w: (pb[16]<<24)|(pb[17]<<16)|(pb[18]<<8)|pb[19],
              h: (pb[20]<<24)|(pb[21]<<16)|(pb[22]<<8)|pb[23]};
    }
  } catch(e) { Logger.log('dims err: ' + e.message); }
  return {w: 0, h: 0};
}

// ─── DRIVE HELPERS ────────────────────────────────────────────────────────────

function getOrCreateTempFolder_() {
  var name = '_Firebean_SlideTemp';
  var it = DriveApp.getFoldersByName(name);
  var f  = it.hasNext() ? it.next() : DriveApp.createFolder(name);
  f.setSharing(DriveApp.Access.ANYONE_WITH_LINK, DriveApp.Permission.VIEW);
  return f;
}

function saveBase64ToPublicDrive_(folder, filename, base64Data, mimeType) {
  var clean    = String(base64Data).replace(/^data:[^;]+;base64,/, '').replace(/\s/g, '');
  var bytes    = Utilities.base64Decode(clean);
  var blob     = Utilities.newBlob(bytes, mimeType, filename);
  var existing = folder.getFilesByName(filename);
  while (existing.hasNext()) { existing.next().setTrashed(true); }
  var file = folder.createFile(blob);
  file.setSharing(DriveApp.Access.ANYONE_WITH_LINK, DriveApp.Permission.VIEW);
  // thumbnail URL — reliable for createImage API (no redirect / consent page)
  return 'https://drive.google.com/thumbnail?id=' + file.getId() + '&sz=s4000';
}

// ─── MASTER DB ────────────────────────────────────────────────────────────────

function updateSheetWithSlideUrl_(projectId, slideUrl) {
  if (!projectId) return;
  var sheet = SpreadsheetApp.openById(SHEET_ID).getSheetByName(SHEET_NAME);
  var data  = sheet.getDataRange().getValues();
  for (var i = 1; i < data.length; i++) {
    if (String(data[i][25]).toUpperCase() === String(projectId).toUpperCase()) {
      sheet.getRange(i + 1, 13).setValue(slideUrl);
      break;
    }
  }
}
