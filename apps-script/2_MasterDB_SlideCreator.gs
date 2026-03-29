/**
 * ============================================================
 * SCRIPT 2 of 3 — MASTER DB SLIDE CREATOR  v11.0
 * ============================================================
 * Deploy URL:  https://script.google.com/macros/s/AKfycbx_7Xf8_HERQel93WJB2F_KjFOWHtCXzfvEkP9B_p7Kh4ImRAWRgWSXtLklvdbYsqbI/exec
 * app.py var:  SLIDE_DB_URL
 * Action:      create_slide
 *
 * HOW IT WORKS:
 *   - Slides 1 & 2 in the master deck are ALWAYS the template (never touched)
 *   - Every new project duplicates slides 1 & 2, then inserts them at position 3 & 4
 *   - Previous projects shift down (3&4 → 5&6 → 7&8 etc)
 *   - Photos use object-fit:cover — scaled to fill cell, centred, no distortion
 *   - Slide size: 960x540px = 720pt x 405pt
 * ============================================================
 */

var TEMPLATE_ID = '19rmqCzgKD8y2ZiLxkiAqhhkV6_t-8QAumZkSi0Eu9C0';
var SHEET_ID    = '1aTuqgmmSKMWgNCl2KR0QhK4Cj8G7W5yPsr4t39pi-yc';
var SHEET_NAME  = 'Basic Info';

// Photo grid — right panel starts at x=210.6pt, slide is 720x405pt
// Each cell: 254.7pt wide x 202.5pt tall. 5pt bleed on all edges.
var PT = 12700;
var PHOTO_EMU = {
  'PHOTO1': {l:205.6*PT, t:-5*PT,    w:264.7*PT, h:212.5*PT},
  'PHOTO2': {l:460.3*PT, t:-5*PT,    w:264.7*PT, h:212.5*PT},
  'PHOTO3': {l:205.6*PT, t:197.5*PT, w:264.7*PT, h:212.5*PT},
  'PHOTO4': {l:460.3*PT, t:197.5*PT, w:264.7*PT, h:212.5*PT},
  'PHOTO5': {l:205.5*PT, t:-5*PT,    w:264.8*PT, h:212.5*PT},
  'PHOTO6': {l:460.2*PT, t:-5*PT,    w:264.8*PT, h:212.5*PT},
  'PHOTO7': {l:205.5*PT, t:197.5*PT, w:264.8*PT, h:212.5*PT},
  'PHOTO8': {l:460.2*PT, t:197.5*PT, w:264.8*PT, h:212.5*PT}
};
var LOGO_EMU = {l:24.3*PT, t:25.5*PT, w:166.2*PT, h:71.6*PT};

// ─── ENTRY POINT ─────────────────────────────────────────────────────────────

function doPost(e) {
  try {
    var data = JSON.parse(e.postData.contents);
    if (data.action === 'create_slide' || data.action === 'create_case_study') {
      return createSlide_(data);
    }
    return resp_({status:'error', message:'Unknown action: ' + data.action});
  } catch(err) {
    return resp_({status:'error', message:err.toString()});
  }
}

function resp_(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}

// ─── MAIN ────────────────────────────────────────────────────────────────────

function createSlide_(data) {
  var token    = ScriptApp.getOAuthToken();
  var apiBase  = 'https://slides.googleapis.com/v1/presentations/' + TEMPLATE_ID;
  var slideUrl = 'https://docs.google.com/presentation/d/' + TEMPLATE_ID + '/edit';

  // ── STEP 1: Read master deck — always use slides[0] & slides[1] as template ──
  var pres = apiGet_(apiBase, token);
  if (!pres.slides || pres.slides.length < 2)
    throw new Error('Master deck must have at least 2 template slides');
  var tmplId1 = pres.slides[0].objectId;
  var tmplId2 = pres.slides[1].objectId;
  Logger.log('Template slide IDs: ' + tmplId1 + ', ' + tmplId2);

  // ── STEP 2: Duplicate template slides (appended at end) ───────────────────────
  var dupResult = apiBatch_(apiBase, token, [
    {duplicateObject: {objectId: tmplId1}},
    {duplicateObject: {objectId: tmplId2}}
  ]);
  var newId1 = dupResult.replies[0].duplicateObject.objectId;
  var newId2 = dupResult.replies[1].duplicateObject.objectId;
  Logger.log('Duplicated: ' + newId1 + ', ' + newId2);

  // ── STEP 3: Move new slides to position 3 & 4 (insertionIndex=2) ─────────────
  Utilities.sleep(800);
  apiBatch_(apiBase, token, [
    {updateSlidesPosition: {slideObjectIds: [newId1, newId2], insertionIndex: 2}}
  ]);
  Logger.log('Moved to position 3 & 4');

  // ── STEP 4: Re-read to get element IDs on the new slides ─────────────────────
  Utilities.sleep(2000);
  pres = apiGet_(apiBase, token);
  var newSlide1 = null, newSlide2 = null;
  pres.slides.forEach(function(s) {
    if (s.objectId === newId1) newSlide1 = s;
    if (s.objectId === newId2) newSlide2 = s;
  });
  if (!newSlide1 || !newSlide2)
    throw new Error('Cannot find new slides after move: ' + newId1 + ', ' + newId2);

  // ── STEP 5: Delete template images from new slides (non-fatal) ───────────────
  var deleteReqs = [];
  var newLogoId  = null;
  (newSlide1.pageElements || []).forEach(function(el) {
    if (el.image) deleteReqs.push({deleteObject: {objectId: el.objectId}});
    if (el.shape && (el.description === 'project_logo' || el.title === 'photo1_placeholder'))
      newLogoId = el.objectId;
  });
  (newSlide2.pageElements || []).forEach(function(el) {
    if (el.image) deleteReqs.push({deleteObject: {objectId: el.objectId}});
  });
  if (newLogoId) deleteReqs.push({deleteObject: {objectId: newLogoId}});
  Logger.log('Deleting ' + deleteReqs.length + ' elements');

  if (deleteReqs.length > 0) {
    var delResp = UrlFetchApp.fetch(apiBase + ':batchUpdate', {
      method:'post', contentType:'application/json',
      headers:{'Authorization':'Bearer ' + token},
      payload: JSON.stringify({requests: deleteReqs}),
      muteHttpExceptions: true
    });
    Logger.log('Delete result: ' + delResp.getResponseCode());
    // Non-fatal — continue even if some objects already gone
  }
  Utilities.sleep(800);

  // ── STEP 6: Replace text + insert photos + logo ───────────────────────────────
  var requests = [];

  // Text replacements — scoped to new slides only
  var dateStr  = (data.date || ((data.event_month||'') + ' ' + (data.event_year||''))).trim();
  var scopeStr = Array.isArray(data.scope)
    ? data.scope.join('\n')
    : String(data.scope||'').replace(/,\s*/g, '\n');
  [
    ['{{CLIENT_NAME}}',  data.client_name  || ''],
    ['{{PROJECT_NAME}}', data.project_name || ''],
    ['{{CATEGORY}}',     data.category     || ''],
    ['{{DATE}}',         dateStr],
    ['{{VENUE}}',        data.venue        || ''],
    ['{{SCOPE}}',        scopeStr],
    ['{{CHALLENGE}}',    data.challenge    || ''],
    ['{{SOLUTION}}',     data.solution     || '']
  ].forEach(function(pair) {
    requests.push({replaceAllText: {
      containsText: {text: pair[0], matchCase: true},
      replaceText:  pair[1],
      pageObjectIds: [newId1, newId2]   // template slides 1&2 never touched
    }});
  });

  // Photos — object-fit:cover using calcCoverTransform_
  var photos      = data.photos || data.images || [];
  var photoResults = [];
  var tempFolder  = getOrCreateTempFolder_();

  for (var i = 0; i < Math.min(photos.length, 8); i++) {
    var num     = i + 1;
    var key     = 'PHOTO' + num;
    var slideId = num <= 4 ? newId1 : newId2;
    var pos     = PHOTO_EMU[key];
    try {
      var dims  = getBase64ImageDimensions_(photos[i]);
      var url   = saveBase64ToPublicDrive_(tempFolder, 'ph' + num + '.jpg', photos[i], 'image/jpeg');
      var cover = calcCoverTransform_(dims.w, dims.h, pos.w, pos.h, pos.l, pos.t);
      requests.push({createImage: {
        url: url,
        objectId: 'PH' + num + '_' + newId1.replace(/[^a-z0-9]/gi, '').substring(0, 20),
        elementProperties: {
          pageObjectId: slideId,
          size:      {width:{magnitude:cover.w, unit:'EMU'}, height:{magnitude:cover.h, unit:'EMU'}},
          transform: {scaleX:1, scaleY:1, translateX:cover.x, translateY:cover.y, unit:'EMU'}
        }
      }});
      photoResults.push(key + ':OK');
    } catch(pe) {
      Logger.log('Photo ' + num + ' err: ' + pe.message);
      photoResults.push(key + ':FAIL');
    }
  }

  // Logo
  var logoResult = 'no_logo';
  var logoB64    = data.logo_white_base64 || data.logo_white || '';
  if (logoB64) {
    try {
      var logoUrl = saveBase64ToPublicDrive_(tempFolder, 'logo_white.png', logoB64, 'image/png');
      requests.push({createImage: {
        url: logoUrl,
        objectId: 'LOGO_' + newId1.replace(/[^a-z0-9]/gi, '').substring(0, 20),
        elementProperties: {
          pageObjectId: newId1,
          size:      {width:{magnitude:LOGO_EMU.w, unit:'EMU'}, height:{magnitude:LOGO_EMU.h, unit:'EMU'}},
          transform: {scaleX:1, scaleY:1, translateX:LOGO_EMU.l, translateY:LOGO_EMU.t, unit:'EMU'}
        }
      }});
      logoResult = 'OK';
    } catch(le) {
      Logger.log('Logo err: ' + le.message);
      logoResult = 'FAIL';
    }
  }

  // ── STEP 7: Execute create+text batchUpdate ───────────────────────────────────
  Utilities.sleep(500);
  var batchResp = UrlFetchApp.fetch(apiBase + ':batchUpdate', {
    method:'post', contentType:'application/json',
    headers:{'Authorization':'Bearer ' + token},
    payload: JSON.stringify({requests: requests}),
    muteHttpExceptions: true
  });
  if (batchResp.getResponseCode() !== 200) {
    Logger.log('batchUpdate FAILED: ' + batchResp.getContentText().substring(0, 500));
    throw new Error('batchUpdate failed ' + batchResp.getResponseCode() + ': ' + batchResp.getContentText().substring(0, 200));
  }
  Logger.log('batchUpdate OK — ' + requests.length + ' requests');

  // ── STEP 8: Write slide URL to Master DB col M ────────────────────────────────
  updateSheetWithSlideUrl_(data.project_id, slideUrl);

  return resp_({
    status: 'success',
    slide_url: slideUrl,
    new_slides: [newId1, newId2],
    photos: photoResults,
    logo: logoResult,
    requests_sent: requests.length
  });
}

// ─── COVER TRANSFORM (object-fit:cover) ──────────────────────────────────────
// Scale image to COVER the cell completely — no white, no distortion.
// Image is centred and bleeds beyond cell edges (clipped by slide boundary).
function calcCoverTransform_(imgW, imgH, cellW, cellH, cellX, cellY) {
  if (!imgW || !imgH) {
    // Unknown dims — fill cell exactly (slight stretch but no white)
    return {w:cellW, h:cellH, x:cellX, y:cellY};
  }
  var scale = Math.max(cellW / imgW, cellH / imgH); // cover = larger scale
  var w = imgW * scale;
  var h = imgH * scale;
  return {
    w: w,
    h: h,
    x: cellX - (w - cellW) / 2,  // centre horizontally
    y: cellY - (h - cellH) / 2   // centre vertically
  };
}

// ─── IMAGE DIMENSIONS ────────────────────────────────────────────────────────

function getBase64ImageDimensions_(base64Data) {
  try {
    var clean = String(base64Data).replace(/^data:[^;]+;base64,/, '').replace(/\s/g, '');
    var bytes = Utilities.base64Decode(clean.substring(0, 32));
    if (bytes[0] === 0xFF && bytes[1] === 0xD8) {
      var fb = Utilities.base64Decode(clean.substring(0, 600));
      for (var i = 2; i < fb.length - 9; i++) {
        if (fb[i]===0xFF && (fb[i+1]===0xC0||fb[i+1]===0xC1||fb[i+1]===0xC2||fb[i+1]===0xC3))
          return {w:(fb[i+7]<<8)|fb[i+8], h:(fb[i+5]<<8)|fb[i+6]};
      }
    }
    if (bytes[0] === 0x89 && bytes[1] === 0x50) {
      var pb = Utilities.base64Decode(clean.substring(0, 64));
      return {w:(pb[16]<<24)|(pb[17]<<16)|(pb[18]<<8)|pb[19],
              h:(pb[20]<<24)|(pb[21]<<16)|(pb[22]<<8)|pb[23]};
    }
  } catch(e) { Logger.log('dims err: ' + e.message); }
  return {w:0, h:0};
}

// ─── DRIVE HELPERS ───────────────────────────────────────────────────────────

function getOrCreateTempFolder_() {
  var name = '_Firebean_SlideTemp';
  var it   = DriveApp.getFoldersByName(name);
  var f    = it.hasNext() ? it.next() : DriveApp.createFolder(name);
  f.setSharing(DriveApp.Access.ANYONE_WITH_LINK, DriveApp.Permission.VIEW);
  return f;
}

function saveBase64ToPublicDrive_(folder, filename, base64Data, mimeType) {
  var clean = String(base64Data).replace(/^data:[^;]+;base64,/, '').replace(/\s/g, '');
  var bytes = Utilities.base64Decode(clean);
  var blob  = Utilities.newBlob(bytes, mimeType, filename);
  var it    = folder.getFilesByName(filename);
  while (it.hasNext()) { it.next().setTrashed(true); }
  var file  = folder.createFile(blob);
  file.setSharing(DriveApp.Access.ANYONE_WITH_LINK, DriveApp.Permission.VIEW);
  return 'https://drive.google.com/thumbnail?id=' + file.getId() + '&sz=s4000';
}

// ─── API HELPERS ─────────────────────────────────────────────────────────────

function apiGet_(url, token) {
  var r = UrlFetchApp.fetch(url, {
    headers:{'Authorization':'Bearer ' + token}, muteHttpExceptions:true
  });
  if (r.getResponseCode() !== 200) throw new Error('GET failed ' + r.getResponseCode() + ': ' + r.getContentText().substring(0,200));
  return JSON.parse(r.getContentText());
}

function apiBatch_(apiBase, token, requests) {
  var r = UrlFetchApp.fetch(apiBase + ':batchUpdate', {
    method:'post', contentType:'application/json',
    headers:{'Authorization':'Bearer ' + token},
    payload: JSON.stringify({requests: requests}),
    muteHttpExceptions:true
  });
  if (r.getResponseCode() !== 200) throw new Error('batchUpdate failed ' + r.getResponseCode() + ': ' + r.getContentText().substring(0,200));
  return JSON.parse(r.getContentText());
}

// ─── MASTER DB ───────────────────────────────────────────────────────────────

function updateSheetWithSlideUrl_(projectId, slideUrl) {
  if (!projectId) return;
  var sheet = SpreadsheetApp.openById(SHEET_ID).getSheetByName(SHEET_NAME);
  var vals  = sheet.getDataRange().getValues();
  for (var i = 1; i < vals.length; i++) {
    if (String(vals[i][25]).toUpperCase() === String(projectId).toUpperCase()) {
      sheet.getRange(i + 1, 13).setValue(slideUrl);
      break;
    }
  }
}

// ─── TEST HELPER (remove before prod) ────────────────────────────────────────

function testAuth() {
  var r = UrlFetchApp.fetch(
    'https://slides.googleapis.com/v1/presentations/' + TEMPLATE_ID,
    {headers:{'Authorization':'Bearer ' + ScriptApp.getOAuthToken()}, muteHttpExceptions:true}
  );
  Logger.log(r.getResponseCode() + ': ' + r.getContentText().substring(0, 300));
}
