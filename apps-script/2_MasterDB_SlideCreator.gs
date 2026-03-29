/**
 * ============================================================
 * SCRIPT 2 of 3 — MASTER DB SLIDE CREATOR  v14.0
 * ============================================================
 * Deploy URL:  https://script.google.com/macros/s/AKfycbx_7Xf8_HERQel93WJB2F_KjFOWHtCXzfvEkP9B_p7Kh4ImRAWRgWSXtLklvdbYsqbI/exec
 * app.py var:  SLIDE_DB_URL
 *
 * APPROACH (v14):
 *   - Use SlidesApp.insertSlide() to copy slides 1 & 2 directly at index 2 & 3
 *   - No REST position shuffling — atomic insert, no page number flicker
 *   - Then switch to REST API only for image/text operations on new slides
 * ============================================================
 */

var TEMPLATE_ID = '19rmqCzgKD8y2ZiLxkiAqhhkV6_t-8QAumZkSi0Eu9C0';
var SHEET_ID    = '1aTuqgmmSKMWgNCl2KR0QhK4Cj8G7W5yPsr4t39pi-yc';
var SHEET_NAME  = 'Basic Info';

// EMU from template API + 5pt bleed
var PT = 12700;
var B  = 5 * PT; // bleed
var PHOTO_EMU = {
  'PHOTO1': {l:210.6*PT-B, t:0-B,       w:254.7*PT+B*2, h:202.5*PT+B*2},
  'PHOTO2': {l:465.3*PT-B, t:0-B,       w:254.7*PT+B*2, h:202.5*PT+B*2},
  'PHOTO3': {l:210.6*PT-B, t:202.5*PT-B,w:254.7*PT+B*2, h:202.5*PT+B*2},
  'PHOTO4': {l:465.3*PT-B, t:202.5*PT-B,w:254.7*PT+B*2, h:202.5*PT+B*2},
  'PHOTO5': {l:210.5*PT-B, t:0-B,       w:254.8*PT+B*2, h:202.5*PT+B*2},
  'PHOTO6': {l:465.2*PT-B, t:0-B,       w:254.8*PT+B*2, h:202.5*PT+B*2},
  'PHOTO7': {l:210.5*PT-B, t:202.5*PT-B,w:254.8*PT+B*2, h:202.5*PT+B*2},
  'PHOTO8': {l:465.2*PT-B, t:202.5*PT-B,w:254.8*PT+B*2, h:202.5*PT+B*2}
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
  // Prevent duplicate execution from redirect-follows
  var lock = LockService.getScriptLock();
  if (!lock.tryLock(30000)) {
    return resp_({status:'error', message:'Script is busy, please retry'});
  }
  try {
    return createSlideInner_(data);
  } finally {
    lock.releaseLock();
  }
}

function createSlideInner_(data) {
  var token    = ScriptApp.getOAuthToken();
  var apiBase  = 'https://slides.googleapis.com/v1/presentations/' + TEMPLATE_ID;
  var slideUrl = 'https://docs.google.com/presentation/d/' + TEMPLATE_ID + '/edit';

  // ── DOUBLE-CHECK IDEMPOTENCY (prevents wait-chain duplicates) ───────────────
  if (data.project_id) {
    var sheet = SpreadsheetApp.openById(SHEET_ID).getSheetByName(SHEET_NAME);
    var vals  = sheet.getDataRange().getValues();
    var targetRow = -1;
    for (var r = 1; r < vals.length; r++) {
      if (String(vals[r][25]).toUpperCase() === String(data.project_id).toUpperCase()) {
        targetRow = r + 1; // 1-based row number
        // Already done — return existing URL
        if (vals[r][12] && String(vals[r][12]).indexOf('http') === 0) {
          Logger.log('Already exists: ' + data.project_id);
          return resp_({status:'success', slide_url:vals[r][12], skipped:true});
        }
        // Already processing — another instance is working on it
        if (vals[r][12] === 'PROCESSING') {
          Logger.log('Already processing: ' + data.project_id);
          return resp_({status:'error', message:'Already processing, please wait'});
        }
        break;
      }
    }
    // Mark as PROCESSING immediately and flush so other instances see it
    if (targetRow > 0) {
      sheet.getRange(targetRow, 13).setValue('PROCESSING');
      SpreadsheetApp.flush(); // force immediate write
      Logger.log('Marked PROCESSING: ' + data.project_id);
    }
  }

  // ── STEP 1: Snapshot existing slide IDs, then insert 2 new slides ────────────
  // We snapshot BEFORE insert so we can identify new slides by diff afterwards
  var presSnap = apiGet_(apiBase, token);
  var existingIds = {};
  presSnap.slides.forEach(function(s) { existingIds[s.objectId] = true; });
  Logger.log('Existing slides: ' + presSnap.slides.length);

  // Use SlidesApp to insert copies of template slides 1 & 2 at position 3 & 4
  var deck   = SlidesApp.openById(TEMPLATE_ID);
  var slides = deck.getSlides();
  if (slides.length < 2) throw new Error('Need at least 2 template slides');
  // Insert slide2-copy at index 2, then slide1-copy at index 2 (pushes slide2-copy to 3)
  deck.insertSlide(2, slides[1]);
  deck.insertSlide(2, slides[0]);
  Logger.log('insertSlide done');

  // ── STEP 2: Re-read and find the 2 NEW slides by comparing against snapshot ──
  // Retry up to 5 times with increasing delay — SlidesApp commits may lag REST API
  var newSlides = [];
  var delays = [2000, 3000, 4000, 5000, 6000];
  for (var attempt = 0; attempt < delays.length; attempt++) {
    Utilities.sleep(delays[attempt]);
    var pres = apiGet_(apiBase, token);
    newSlides = [];
    pres.slides.forEach(function(s, i) {
      if (!existingIds[s.objectId]) {
        newSlides.push({slide: s, index: i});
        Logger.log('Attempt '+(attempt+1)+': New slide at pos '+(i+1)+': '+s.objectId);
      }
    });
    Logger.log('Attempt '+(attempt+1)+': found '+newSlides.length+' new slides (total '+pres.slides.length+')');
    if (newSlides.length >= 2) break;
  }
  if (newSlides.length < 2)
    throw new Error('Expected 2 new slides after retries, found: ' + newSlides.length);

  // Sort by index so slide1 (lower index = position 3) comes first
  newSlides.sort(function(a,b){ return a.index - b.index; });
  var newSlideData1 = newSlides[0].slide;
  var newSlideData2 = newSlides[1].slide;
  var newId1 = newSlideData1.objectId;
  var newId2 = newSlideData2.objectId;
  Logger.log('New slides confirmed: pos '+(newSlides[0].index+1)+' & '+(newSlides[1].index+1));

  // ── STEP 3: Delete template images from new slides (non-fatal) ───────────────
  var deleteReqs = [];
  var newLogoId  = null;
  (newSlideData1.pageElements || []).forEach(function(el) {
    if (el.image) deleteReqs.push({deleteObject: {objectId: el.objectId}});
    if (el.shape && (el.description === 'project_logo' || el.title === 'photo1_placeholder'))
      newLogoId = el.objectId;
  });
  (newSlideData2.pageElements || []).forEach(function(el) {
    if (el.image) deleteReqs.push({deleteObject: {objectId: el.objectId}});
  });
  if (newLogoId) deleteReqs.push({deleteObject: {objectId: newLogoId}});
  Logger.log('Deleting ' + deleteReqs.length + ' images, logo: ' + newLogoId);

  if (deleteReqs.length > 0) {
    var delResp = UrlFetchApp.fetch(apiBase + ':batchUpdate', {
      method:'post', contentType:'application/json',
      headers:{'Authorization':'Bearer ' + token},
      payload: JSON.stringify({requests: deleteReqs}),
      muteHttpExceptions: true
    });
    Logger.log('Delete: ' + delResp.getResponseCode());
  }
  Utilities.sleep(800);

  // ── STEP 4: Build requests — text + photos + logo ─────────────────────────
  var requests = [];

  // Text — scoped to new slides only
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
      pageObjectIds: [newId1, newId2]
    }});
  });

  // Photos — object-fit:cover
  var photos       = data.photos || data.images || [];
  var photoResults = [];
  var tempFolder   = getOrCreateTempFolder_();

  for (var i = 0; i < Math.min(photos.length, 8); i++) {
    var num     = i + 1;
    var key     = 'PHOTO' + num;
    var slideId = num <= 4 ? newId1 : newId2;
    var pos     = PHOTO_EMU[key];
    try {
      var dims  = getBase64ImageDimensions_(photos[i]);
      var url   = saveBase64ToPublicDrive_(tempFolder, 'ph'+num+'.jpg', photos[i], 'image/jpeg');
      var cover = calcCoverTransform_(dims.w, dims.h, pos.w, pos.h, pos.l, pos.t);
      requests.push({createImage: {
        url: url,
        objectId: 'PH'+num+'_'+newId1.replace(/[^a-z0-9]/gi,'').substring(0,20),
        elementProperties: {
          pageObjectId: slideId,
          size:      {width:{magnitude:cover.w,unit:'EMU'}, height:{magnitude:cover.h,unit:'EMU'}},
          transform: {scaleX:1, scaleY:1, translateX:cover.x, translateY:cover.y, unit:'EMU'}
        }
      }});
      photoResults.push(key+':OK');
    } catch(pe) {
      Logger.log('Photo '+num+': '+pe.message);
      photoResults.push(key+':FAIL');
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
        objectId: 'LOGO_'+newId1.replace(/[^a-z0-9]/gi,'').substring(0,20),
        elementProperties: {
          pageObjectId: newId1,
          size:      {width:{magnitude:LOGO_EMU.w,unit:'EMU'}, height:{magnitude:LOGO_EMU.h,unit:'EMU'}},
          transform: {scaleX:1, scaleY:1, translateX:LOGO_EMU.l, translateY:LOGO_EMU.t, unit:'EMU'}
        }
      }});
      logoResult = 'OK';
    } catch(le) {
      Logger.log('Logo: '+le.message);
      logoResult = 'FAIL';
    }
  }

  // ── STEP 5: Execute batchUpdate ──────────────────────────────────────────────
  Utilities.sleep(500);
  var batchResp = UrlFetchApp.fetch(apiBase+':batchUpdate', {
    method:'post', contentType:'application/json',
    headers:{'Authorization':'Bearer '+token},
    payload: JSON.stringify({requests: requests}),
    muteHttpExceptions: true
  });
  if (batchResp.getResponseCode() !== 200) {
    Logger.log('FAILED: '+batchResp.getContentText().substring(0,500));
    throw new Error('batchUpdate failed '+batchResp.getResponseCode()+': '+batchResp.getContentText().substring(0,200));
  }
  Logger.log('batchUpdate OK — '+requests.length+' requests');

  // ── STEP 6: Write URL to Master DB ──────────────────────────────────────────
  updateSheetWithSlideUrl_(data.project_id, slideUrl);

  return resp_({
    status:'success', slide_url:slideUrl,
    new_slides:[newId1,newId2],
    photos:photoResults, logo:logoResult,
    requests_sent:requests.length
  });
}

// ─── COVER TRANSFORM ─────────────────────────────────────────────────────────
function calcCoverTransform_(imgW, imgH, cellW, cellH, cellX, cellY) {
  if (!imgW || !imgH) return {w:cellW, h:cellH, x:cellX, y:cellY};
  var scale = Math.max(cellW/imgW, cellH/imgH);
  var w = imgW*scale, h = imgH*scale;
  return {w:w, h:h, x:cellX-(w-cellW)/2, y:cellY-(h-cellH)/2};
}

// ─── IMAGE DIMENSIONS ────────────────────────────────────────────────────────
function getBase64ImageDimensions_(base64Data) {
  try {
    var clean=String(base64Data).replace(/^data:[^;]+;base64,/,'').replace(/\s/g,'');
    var bytes=Utilities.base64Decode(clean.substring(0,32));
    if (bytes[0]===0xFF&&bytes[1]===0xD8) {
      var fb=Utilities.base64Decode(clean.substring(0,600));
      for (var i=2;i<fb.length-9;i++)
        if (fb[i]===0xFF&&(fb[i+1]===0xC0||fb[i+1]===0xC1||fb[i+1]===0xC2||fb[i+1]===0xC3))
          return {w:(fb[i+7]<<8)|fb[i+8], h:(fb[i+5]<<8)|fb[i+6]};
    }
    if (bytes[0]===0x89&&bytes[1]===0x50) {
      var pb=Utilities.base64Decode(clean.substring(0,64));
      return {w:(pb[16]<<24)|(pb[17]<<16)|(pb[18]<<8)|pb[19],
              h:(pb[20]<<24)|(pb[21]<<16)|(pb[22]<<8)|pb[23]};
    }
  } catch(e) { Logger.log('dims: '+e.message); }
  return {w:0,h:0};
}

// ─── DRIVE HELPERS ───────────────────────────────────────────────────────────
function getOrCreateTempFolder_() {
  var name='_Firebean_SlideTemp';
  var it=DriveApp.getFoldersByName(name);
  var f=it.hasNext()?it.next():DriveApp.createFolder(name);
  f.setSharing(DriveApp.Access.ANYONE_WITH_LINK,DriveApp.Permission.VIEW);
  return f;
}

function saveBase64ToPublicDrive_(folder,filename,base64Data,mimeType) {
  var clean=String(base64Data).replace(/^data:[^;]+;base64,/,'').replace(/\s/g,'');
  var bytes=Utilities.base64Decode(clean);
  var blob=Utilities.newBlob(bytes,mimeType,filename);
  var it=folder.getFilesByName(filename);
  while(it.hasNext()){it.next().setTrashed(true);}
  var file=folder.createFile(blob);
  file.setSharing(DriveApp.Access.ANYONE_WITH_LINK,DriveApp.Permission.VIEW);
  return 'https://drive.google.com/thumbnail?id='+file.getId()+'&sz=s4000';
}

// ─── API HELPERS ─────────────────────────────────────────────────────────────
function apiGet_(url,token) {
  var r=UrlFetchApp.fetch(url,{headers:{'Authorization':'Bearer '+token},muteHttpExceptions:true});
  if(r.getResponseCode()!==200) throw new Error('GET failed '+r.getResponseCode()+': '+r.getContentText().substring(0,200));
  return JSON.parse(r.getContentText());
}

// ─── MASTER DB ───────────────────────────────────────────────────────────────
function updateSheetWithSlideUrl_(projectId,slideUrl) {
  if(!projectId) return;
  var sheet=SpreadsheetApp.openById(SHEET_ID).getSheetByName(SHEET_NAME);
  var vals=sheet.getDataRange().getValues();
  for(var i=1;i<vals.length;i++) {
    if(String(vals[i][25]).toUpperCase()===String(projectId).toUpperCase()) {
      sheet.getRange(i+1,13).setValue(slideUrl); break;
    }
  }
}

function testAuth() {
  var r=UrlFetchApp.fetch('https://slides.googleapis.com/v1/presentations/'+TEMPLATE_ID,
    {headers:{'Authorization':'Bearer '+ScriptApp.getOAuthToken()},muteHttpExceptions:true});
  Logger.log(r.getResponseCode()+': '+r.getContentText().substring(0,300));
}
