/**
 * ============================================================
 * SCRIPT 2 of 3 — MASTER DB SLIDE CREATOR  v15.0 (Pure REST)
 * ============================================================
 * Deploy URL:  https://script.google.com/macros/s/AKfycbwAFo739fMIFwSYWaIZNw9ILiJk96tlnlVWlg8PdbrGYd1SzEGaAc4E_P4aLyNB3tnp/exec
 * app.py var:  SLIDE_DB_URL
 *
 * v15 — Pure REST only. No SlidesApp mixing.
 *   1. REST duplicateObject slides[0] & slides[1] → appended at end
 *   2. REST updateSlidesPosition → move BOTH to insertionIndex:2 (pages 3&4)
 *   3. REST re-read → find new slides by objectId (from duplicateObject reply)
 *   4. REST batchUpdate → delete old images, replace text, insert photos+logo
 *
 * IDEMPOTENCY: PROCESSING flag + SpreadsheetApp.flush() prevents duplicates
 * GRID: 720x405pt slide, panel at x=210.6pt, 5pt bleed on all edges
 * ============================================================
 */

var TEMPLATE_ID = '19rmqCzgKD8y2ZiLxkiAqhhkV6_t-8QAumZkSi0Eu9C0';
var SHEET_ID    = '1aTuqgmmSKMWgNCl2KR0QhK4Cj8G7W5yPsr4t39pi-yc';
var SHEET_NAME  = 'Basic Info';

var PT = 12700;
var B  = 5 * PT;
var PHOTO_EMU = {
  'PHOTO1': {l:210.6*PT-B, t:0-B,        w:254.7*PT+B*2, h:202.5*PT+B*2},
  'PHOTO2': {l:465.3*PT-B, t:0-B,        w:254.7*PT+B*2, h:202.5*PT+B*2},
  'PHOTO3': {l:210.6*PT-B, t:202.5*PT-B, w:254.7*PT+B*2, h:202.5*PT+B*2},
  'PHOTO4': {l:465.3*PT-B, t:202.5*PT-B, w:254.7*PT+B*2, h:202.5*PT+B*2},
  'PHOTO5': {l:210.5*PT-B, t:0-B,        w:254.8*PT+B*2, h:202.5*PT+B*2},
  'PHOTO6': {l:465.2*PT-B, t:0-B,        w:254.8*PT+B*2, h:202.5*PT+B*2},
  'PHOTO7': {l:210.5*PT-B, t:202.5*PT-B, w:254.8*PT+B*2, h:202.5*PT+B*2},
  'PHOTO8': {l:465.2*PT-B, t:202.5*PT-B, w:254.8*PT+B*2, h:202.5*PT+B*2}
};
var LOGO_EMU = {l:24.3*PT, t:25.5*PT, w:166.2*PT, h:71.6*PT};

// ─── ENTRY POINT ─────────────────────────────────────────────────────────────

function doPost(e) {
  try {
    var data = JSON.parse(e.postData.contents);
    if (data.action === 'create_slide' || data.action === 'create_case_study') {
      return createSlide_(data);
    }
    return resp_({status:'error', message:'Unknown action: '+data.action});
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
  var token   = ScriptApp.getOAuthToken();
  var apiBase = 'https://slides.googleapis.com/v1/presentations/' + TEMPLATE_ID;
  var slideUrl = 'https://docs.google.com/presentation/d/' + TEMPLATE_ID + '/edit';

  // ── IDEMPOTENCY: PropertiesService per-project dedup ────────────────────────
  var pid   = String(data.project_id || '');
  var props = PropertiesService.getScriptProperties();

  if (pid) {
    var existing = props.getProperty(pid);
    if (existing) {
      Logger.log('SKIP — already running/done: ' + pid + ' = ' + existing);
      if (existing.indexOf('http') === 0) return resp_({status:'success', slide_url:existing, skipped:true});
      return resp_({status:'error', message:'Already processing'});
    }
    // Claim this project_id immediately
    props.setProperty(pid, 'PROCESSING');
    Logger.log('Claimed: ' + pid);
  }

  // Also mark sheet col M as PROCESSING (for UI feedback)
  var targetRow = -1;
  if (pid) {
    var sheet = SpreadsheetApp.openById(SHEET_ID).getSheetByName(SHEET_NAME);
    var vals  = sheet.getDataRange().getValues();
    for (var r = 1; r < vals.length; r++) {
      if (String(vals[r][25]).toUpperCase() === pid.toUpperCase()) {
        targetRow = r + 1;
        var colM = String(vals[r][12] || '');
        if (colM.indexOf('http') === 0) {
          props.setProperty(pid, colM);
          return resp_({status:'success', slide_url:colM, skipped:true});
        }
        sheet.getRange(targetRow, 13).setValue('PROCESSING');
        SpreadsheetApp.flush();
        break;
      }
    }
  }

  // ── STEP 1: Read template — get slide 1 & 2 objectIds ────────────────────────
  var pres = apiGet_(apiBase, token);
  if (!pres.slides || pres.slides.length < 2) throw new Error('Need 2 template slides');
  var tmplId1 = pres.slides[0].objectId;
  var tmplId2 = pres.slides[1].objectId;
  Logger.log('Templates: '+tmplId1+', '+tmplId2+' | Total: '+pres.slides.length);

  // ── STEP 2: Duplicate both (REST) — appended at end ──────────────────────────
  var dupResult = apiBatch_(apiBase, token, [
    {duplicateObject: {objectId: tmplId1}},
    {duplicateObject: {objectId: tmplId2}}
  ]);
  var newId1 = dupResult.replies[0].duplicateObject.objectId;
  var newId2 = dupResult.replies[1].duplicateObject.objectId;
  Logger.log('Duplicated: '+newId1+', '+newId2);

  // ── STEP 3: Move BOTH to position 3 & 4 (insertionIndex:2) ───────────────────
  Utilities.sleep(1000);
  apiBatch_(apiBase, token, [
    {updateSlidesPosition: {slideObjectIds: [newId1, newId2], insertionIndex: 3}}
  ]);
  Logger.log('Moved to pos 3&4');

  // ── STEP 4: Re-read to get element IDs (REST sees its own changes immediately) -
  Utilities.sleep(1500);
  pres = apiGet_(apiBase, token);
  var newSlide1 = null, newSlide2 = null;
  pres.slides.forEach(function(s, i) {
    if (s.objectId === newId1) { newSlide1 = s; Logger.log('Slide1 at pos '+(i+1)); }
    if (s.objectId === newId2) { newSlide2 = s; Logger.log('Slide2 at pos '+(i+1)); }
  });
  if (!newSlide1 || !newSlide2) throw new Error('Cannot find new slides: '+newId1+', '+newId2);

  // ── STEP 5: Delete template images from new slides ────────────────────────────
  var deleteReqs = [], newLogoId = null;
  (newSlide1.pageElements || []).forEach(function(el) {
    if (el.image) deleteReqs.push({deleteObject:{objectId:el.objectId}});
    if (el.shape && (el.description==='project_logo' || el.title==='photo1_placeholder'))
      newLogoId = el.objectId;
  });
  (newSlide2.pageElements || []).forEach(function(el) {
    if (el.image) deleteReqs.push({deleteObject:{objectId:el.objectId}});
  });
  if (newLogoId) deleteReqs.push({deleteObject:{objectId:newLogoId}});
  Logger.log('Deleting '+deleteReqs.length+' elements');

  if (deleteReqs.length > 0) {
    var delResp = UrlFetchApp.fetch(apiBase+':batchUpdate', {
      method:'post', contentType:'application/json',
      headers:{'Authorization':'Bearer '+token},
      payload:JSON.stringify({requests:deleteReqs}),
      muteHttpExceptions:true
    });
    Logger.log('Delete: '+delResp.getResponseCode());
  }
  Utilities.sleep(800);

  // ── STEP 6: Text + photos + logo ─────────────────────────────────────────────
  var requests = [];

  var dateStr  = (data.date||((data.event_month||'')+' '+(data.event_year||''))).trim();
  var scopeStr = Array.isArray(data.scope) ? data.scope.join('\n') : String(data.scope||'').replace(/,\s*/g,'\n');
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
    requests.push({replaceAllText:{
      containsText:{text:pair[0],matchCase:true},
      replaceText:pair[1],
      pageObjectIds:[newId1,newId2]
    }});
  });

  var photos = data.photos || data.images || [];
  var photoResults = [];
  var tempFolder = getOrCreateTempFolder_();

  for (var i = 0; i < Math.min(photos.length, 8); i++) {
    var num = i+1, key = 'PHOTO'+num;
    var slideId = num <= 4 ? newId1 : newId2;
    var pos = PHOTO_EMU[key];
    try {
      var dims  = getBase64ImageDimensions_(photos[i]);
      var url   = saveBase64ToPublicDrive_(tempFolder, 'ph'+num+'.jpg', photos[i], 'image/jpeg');
      var cover = calcCoverTransform_(dims.w, dims.h, pos.w, pos.h, pos.l, pos.t);
      requests.push({createImage:{
        url:url,
        objectId:'PH'+num+'_'+newId1.replace(/[^a-z0-9]/gi,'').substring(0,20),
        elementProperties:{
          pageObjectId:slideId,
          size:{width:{magnitude:cover.w,unit:'EMU'},height:{magnitude:cover.h,unit:'EMU'}},
          transform:{scaleX:1,scaleY:1,translateX:cover.x,translateY:cover.y,unit:'EMU'}
        }
      }});
      photoResults.push(key+':OK');
    } catch(pe) { photoResults.push(key+':FAIL'); }
  }

  var logoResult = 'no_logo';
  var logoB64 = data.logo_white_base64 || data.logo_white || '';
  if (logoB64) {
    try {
      var logoUrl = saveBase64ToPublicDrive_(tempFolder, 'logo_white.png', logoB64, 'image/png');
      requests.push({createImage:{
        url:logoUrl,
        objectId:'LOGO_'+newId1.replace(/[^a-z0-9]/gi,'').substring(0,20),
        elementProperties:{
          pageObjectId:newId1,
          size:{width:{magnitude:LOGO_EMU.w,unit:'EMU'},height:{magnitude:LOGO_EMU.h,unit:'EMU'}},
          transform:{scaleX:1,scaleY:1,translateX:LOGO_EMU.l,translateY:LOGO_EMU.t,unit:'EMU'}
        }
      }});
      logoResult = 'OK';
    } catch(le) { logoResult = 'FAIL'; }
  }

  // ── STEP 7: Execute batchUpdate ───────────────────────────────────────────────
  Utilities.sleep(500);
  var batchResp = UrlFetchApp.fetch(apiBase+':batchUpdate', {
    method:'post', contentType:'application/json',
    headers:{'Authorization':'Bearer '+token},
    payload:JSON.stringify({requests:requests}),
    muteHttpExceptions:true
  });
  if (batchResp.getResponseCode() !== 200)
    throw new Error('batchUpdate failed '+batchResp.getResponseCode()+': '+batchResp.getContentText().substring(0,200));
  Logger.log('batchUpdate OK — '+requests.length+' requests');

  // ── STEP 8: Write URL to sheet ────────────────────────────────────────────────
  updateSheetWithSlideUrl_(data.project_id, slideUrl);

  return resp_({
    status:'success', slide_url:slideUrl,
    new_slides:[newId1,newId2],
    photos:photoResults, logo:logoResult,
    requests_sent:requests.length
  });
}

// ─── HELPERS ─────────────────────────────────────────────────────────────────

function calcCoverTransform_(imgW,imgH,cellW,cellH,cellX,cellY) {
  if (!imgW||!imgH) return {w:cellW,h:cellH,x:cellX,y:cellY};
  var scale=Math.max(cellW/imgW,cellH/imgH);
  var w=imgW*scale, h=imgH*scale;
  return {w:w,h:h,x:cellX-(w-cellW)/2,y:cellY-(h-cellH)/2};
}

function getBase64ImageDimensions_(b64) {
  try {
    var c=String(b64).replace(/^data:[^;]+;base64,/,'').replace(/\s/g,'');
    var b=Utilities.base64Decode(c.substring(0,32));
    if (b[0]===0xFF&&b[1]===0xD8) {
      var fb=Utilities.base64Decode(c.substring(0,600));
      for (var i=2;i<fb.length-9;i++)
        if (fb[i]===0xFF&&(fb[i+1]===0xC0||fb[i+1]===0xC1||fb[i+1]===0xC2||fb[i+1]===0xC3))
          return {w:(fb[i+7]<<8)|fb[i+8],h:(fb[i+5]<<8)|fb[i+6]};
    }
    if (b[0]===0x89&&b[1]===0x50) {
      var pb=Utilities.base64Decode(c.substring(0,64));
      return {w:(pb[16]<<24)|(pb[17]<<16)|(pb[18]<<8)|pb[19],h:(pb[20]<<24)|(pb[21]<<16)|(pb[22]<<8)|pb[23]};
    }
  } catch(e) {}
  return {w:0,h:0};
}

function getOrCreateTempFolder_() {
  var n='_Firebean_SlideTemp', it=DriveApp.getFoldersByName(n);
  var f=it.hasNext()?it.next():DriveApp.createFolder(n);
  try { f.setSharing(DriveApp.Access.ANYONE_WITH_LINK,DriveApp.Permission.VIEW); } catch(e) {}
  return f;
}

function saveBase64ToPublicDrive_(folder,filename,b64,mimeType) {
  var c=String(b64).replace(/^data:[^;]+;base64,/,'').replace(/\s/g,'');
  var blob=Utilities.newBlob(Utilities.base64Decode(c),mimeType,filename);
  var it=folder.getFilesByName(filename);
  while(it.hasNext()){it.next().setTrashed(true);}
  var file=folder.createFile(blob);
  // No setSharing needed — Slides API uses script OAuth token to fetch the image
  return 'https://drive.google.com/thumbnail?id='+file.getId()+'&sz=s4000&authuser=0';
}

function apiGet_(url,token) {
  var r=UrlFetchApp.fetch(url,{headers:{'Authorization':'Bearer '+token},muteHttpExceptions:true});
  if(r.getResponseCode()!==200) throw new Error('GET failed '+r.getResponseCode()+': '+r.getContentText().substring(0,200));
  return JSON.parse(r.getContentText());
}

function apiBatch_(base,token,reqs) {
  var r=UrlFetchApp.fetch(base+':batchUpdate',{
    method:'post',contentType:'application/json',
    headers:{'Authorization':'Bearer '+token},
    payload:JSON.stringify({requests:reqs}),muteHttpExceptions:true
  });
  if(r.getResponseCode()!==200) throw new Error('batch failed '+r.getResponseCode()+': '+r.getContentText().substring(0,200));
  return JSON.parse(r.getContentText());
}

function updateSheetWithSlideUrl_(projectId,slideUrl) {
  // Save to PropertiesService so retries know we're done
  if (projectId) {
    try { PropertiesService.getScriptProperties().setProperty(String(projectId), slideUrl); } catch(e) {}
  }
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
  Logger.log(r.getResponseCode()+': '+r.getContentText().substring(0,200));
}
