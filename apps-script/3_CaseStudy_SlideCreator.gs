/**
 * ============================================================
 * SCRIPT 3 of 3 — FIREBEAN CASE STUDY SLIDE CREATOR  v17.0
 * ============================================================
 * Deploy URL:  https://script.google.com/macros/s/AKfycbxKP-8Xrvy6hblPqTmtXn76rO3DFOeU6jYQtLw5QDfDP1-adNDk02bhoKihfvp_Xsvy/exec
 * app.py var:  CASE_STUDY_URL
 *
 * v17: hybrid approach
 *   - doPost returns immediately (no retry trigger)
 *   - ScriptLock prevents concurrent execution
 *   - REST duplicateObject creates truly independent slides (appended at end)
 *   - SlidesApp used for replaceAllText + insertImage on the new slides
 *   - Photos inserted by matching PHOTO1-PHOTO8 alt-text, image placed on top
 * ============================================================
 */

var TEMPLATE_ID = '19rmqCzgKD8y2ZiLxkiAqhhkV6_t-8QAumZkSi0Eu9C0';
var SHEET_ID    = '1aTuqgmmSKMWgNCl2KR0QhK4Cj8G7W5yPsr4t39pi-yc';
var SHEET_NAME  = 'Basic Info';

// ─── ENTRY POINT ─────────────────────────────────────────────────────────────

function doPost(e) {
  try {
    var data = JSON.parse(e.postData.contents);
    if (data.action !== 'create_slide' && data.action !== 'create_case_study') {
      return resp_({status:'error', message:'Unknown action'});
    }

    var pid   = String(data.project_id || '');
    var props = PropertiesService.getScriptProperties();

    // Fast dedup check before lock
    if (pid) {
      var existing = props.getProperty(pid);
      if (existing && existing.indexOf('http') === 0) {
        return resp_({status:'success', slide_url:existing, skipped:true});
      }
    }

    // Try async trigger first; fall back to sync
    try {
      var key = 'PAYLOAD_' + (pid || String(new Date().getTime()));
      props.setProperty(key, JSON.stringify(data));
      if (pid) props.setProperty(pid, 'QUEUED');
      ScriptApp.newTrigger('processSlideTrigger_').timeBased().after(3000).create();
      return resp_({status:'queued', project_id:pid});
    } catch(triggerErr) {
      return createSlide_(data);
    }

  } catch(err) {
    return resp_({status:'error', message:err.toString()});
  }
}

function resp_(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}

function processSlideTrigger_() {
  ScriptApp.getProjectTriggers().forEach(function(t) {
    if (t.getHandlerFunction() === 'processSlideTrigger_') ScriptApp.deleteTrigger(t);
  });
  var props = PropertiesService.getScriptProperties();
  var all   = props.getProperties();
  Object.keys(all).forEach(function(key) {
    if (key.indexOf('PAYLOAD_') !== 0) return;
    try {
      var data = JSON.parse(all[key]);
      props.deleteProperty(key);
      createSlide_(data);
    } catch(e) { Logger.log('Trigger err: ' + e.message); }
  });
}

// ─── MAIN ────────────────────────────────────────────────────────────────────

function createSlide_(data) {
  var token    = ScriptApp.getOAuthToken();
  var apiBase  = 'https://slides.googleapis.com/v1/presentations/' + TEMPLATE_ID;
  var slideUrl = 'https://docs.google.com/presentation/d/' + TEMPLATE_ID + '/edit';
  var props    = PropertiesService.getScriptProperties();
  var pid      = String(data.project_id || '');

  // ScriptLock — held for full execution, prevents concurrent runs
  var lock = LockService.getScriptLock();
  if (!lock.tryLock(30000)) {
    Logger.log('Lock timeout for: ' + pid);
    return resp_({status:'error', message:'Another instance running'});
  }

  try {
    // Recheck after lock — another instance may have finished
    if (pid) {
      var state = props.getProperty(pid);
      if (state && state.indexOf('http') === 0) {
        return resp_({status:'success', slide_url:state, skipped:true});
      }
      if (state === 'RUNNING') {
        return resp_({status:'error', message:'Already processing'});
      }
      props.setProperty(pid, 'RUNNING');
    }

    // ── STEP 1: Read template slides ────────────────────────────────────────
    var getResp = UrlFetchApp.fetch(apiBase, {
      headers:{'Authorization':'Bearer '+token}, muteHttpExceptions:true
    });
    if (getResp.getResponseCode() !== 200) throw new Error('GET failed: '+getResp.getResponseCode());
    var pres   = JSON.parse(getResp.getContentText());
    var tmpl1  = pres.slides[0].objectId;
    var tmpl2  = pres.slides[1].objectId;
    Logger.log('Templates: '+tmpl1+', '+tmpl2+' | Total: '+pres.slides.length);

    // ── STEP 2: Duplicate via REST (truly independent copies, appended at end) ─
    var dupResp = UrlFetchApp.fetch(apiBase+':batchUpdate', {
      method:'post', contentType:'application/json',
      headers:{'Authorization':'Bearer '+token},
      payload:JSON.stringify({requests:[
        {duplicateObject:{objectId:tmpl1}},
        {duplicateObject:{objectId:tmpl2}}
      ]}), muteHttpExceptions:true
    });
    if (dupResp.getResponseCode() !== 200) throw new Error('Dup failed: '+dupResp.getContentText().substring(0,200));
    var dupResult = JSON.parse(dupResp.getContentText());
    var newId1    = dupResult.replies[0].duplicateObject.objectId;
    var newId2    = dupResult.replies[1].duplicateObject.objectId;
    Logger.log('New slides: '+newId1+', '+newId2);

    // ── STEP 3: Replace text via REST (scoped to new slides only) ────────────
    Utilities.sleep(1000);
    var dateStr  = (data.date||((data.event_month||'')+' '+(data.event_year||''))).trim();
    var scopeStr = Array.isArray(data.scope)?data.scope.join('\n'):String(data.scope||'').replace(/,\s*/g,'\n');
    var textReqs = [];
    [['{{CLIENT_NAME}}',data.client_name||''],['{{PROJECT_NAME}}',data.project_name||''],
     ['{{CATEGORY}}',data.category||''],['{{DATE}}',dateStr],['{{VENUE}}',data.venue||''],
     ['{{SCOPE}}',scopeStr],['{{CHALLENGE}}',data.challenge||''],['{{SOLUTION}}',data.solution||'']
    ].forEach(function(p){
      textReqs.push({replaceAllText:{containsText:{text:p[0],matchCase:true},replaceText:p[1],pageObjectIds:[newId1,newId2]}});
    });
    var txtResp = UrlFetchApp.fetch(apiBase+':batchUpdate',{
      method:'post',contentType:'application/json',
      headers:{'Authorization':'Bearer '+token},
      payload:JSON.stringify({requests:textReqs}),muteHttpExceptions:true
    });
    Logger.log('Text replace: '+txtResp.getResponseCode());

    // ── STEP 4: Insert photos via SlidesApp on the new independent slides ────
    Utilities.sleep(1500);
    var presApp  = SlidesApp.openById(TEMPLATE_ID);
    var allSlides = presApp.getSlides();
    var slide1 = null, slide2 = null;
    allSlides.forEach(function(s) {
      if (s.getObjectId() === newId1) slide1 = s;
      if (s.getObjectId() === newId2) slide2 = s;
    });
    if (!slide1||!slide2) throw new Error('Cannot find new slides via SlidesApp');

    var photos     = data.photos || data.images || [];
    var tempFolder = getOrCreateTempFolder_();
    var photoUrls  = [];
    for (var i=0; i<Math.min(photos.length,8); i++) {
      try {
        photoUrls.push(saveBase64ToPublicDrive_(tempFolder,'ph'+(i+1)+'.jpg',photos[i],'image/jpeg'));
      } catch(e) { photoUrls.push(null); Logger.log('Photo '+(i+1)+' err: '+e.message); }
    }

    [slide1, slide2].forEach(function(slide) {
      slide.getPageElements().forEach(function(el) {
        var altText = '';
        try { altText = el.getTitle()||''; } catch(e) {}
        if (!altText) try { altText = el.getDescription()||''; } catch(e) {}
        var m = altText.match(/^PHOTO([1-8])$/);
        if (!m) return;
        var idx = parseInt(m[1]) - 1;
        var url = photoUrls[idx];
        if (!url) return;
        try {
          var l=el.getLeft(), t=el.getTop(), w=el.getWidth(), h=el.getHeight();
          var img = slide.insertImage(url);
          img.setLeft(l); img.setTop(t); img.setWidth(w); img.setHeight(h);
          Logger.log('Photo '+(idx+1)+' inserted at '+l+','+t);
        } catch(pe) { Logger.log('Photo insert err: '+pe.message); }
      });
    });

    // Logo
    var logoB64 = data.logo_white_base64 || data.logo_white || '';
    if (logoB64) {
      try {
        var logoUrl = saveBase64ToPublicDrive_(tempFolder,'logo_white.png',logoB64,'image/png');
        slide1.getPageElements().forEach(function(el) {
          var d=''; try{d=el.getDescription()||'';}catch(e){}
          var t=''; try{t=el.getTitle()||'';}catch(e){}
          if (d==='project_logo'||t==='photo1_placeholder'||t==='logo_white') {
            try {
              var l=el.getLeft(),tp=el.getTop(),w=el.getWidth(),h=el.getHeight();
              var img=slide1.insertImage(logoUrl);
              img.setLeft(l);img.setTop(tp);img.setWidth(w);img.setHeight(h);
              Logger.log('Logo inserted');
            } catch(le){Logger.log('Logo err: '+le.message);}
          }
        });
      } catch(le){Logger.log('Logo err: '+le.message);}
    }

    // ── STEP 5: Write URL to sheet ───────────────────────────────────────────
    updateSheetWithSlideUrl_(pid, slideUrl);
    if (pid) props.setProperty(pid, slideUrl);
    Logger.log('Done: '+slideUrl);
    return resp_({status:'success', slide_url:slideUrl});

  } finally {
    lock.releaseLock();
  }
}

// ─── HELPERS ─────────────────────────────────────────────────────────────────

function getOrCreateTempFolder_() {
  var n='_Firebean_SlideTemp', it=DriveApp.getFoldersByName(n);
  var f=it.hasNext()?it.next():DriveApp.createFolder(n);
  try{f.setSharing(DriveApp.Access.ANYONE_WITH_LINK,DriveApp.Permission.VIEW);}catch(e){}
  return f;
}

function saveBase64ToPublicDrive_(folder,filename,b64,mimeType) {
  var clean=String(b64).replace(/^data:[^;]+;base64,/,'').replace(/\s/g,'');
  var bytes=Utilities.base64Decode(clean);
  var blob=Utilities.newBlob(bytes,mimeType,filename);
  var it=folder.getFilesByName(filename);
  while(it.hasNext()){it.next().setTrashed(true);}
  var file=folder.createFile(blob);
  try{file.setSharing(DriveApp.Access.ANYONE_WITH_LINK,DriveApp.Permission.VIEW);}catch(e){}
  return 'https://drive.google.com/thumbnail?id='+file.getId()+'&sz=s4000';
}

function updateSheetWithSlideUrl_(projectId,slideUrl) {
  if(!projectId) return;
  var sheet=SpreadsheetApp.openById(SHEET_ID).getSheetByName(SHEET_NAME);
  var vals=sheet.getDataRange().getValues();
  for(var i=1;i<vals.length;i++){
    if(String(vals[i][25]).toUpperCase()===String(projectId).toUpperCase()){
      sheet.getRange(i+1,13).setValue(slideUrl); break;
    }
  }
}

function testAuth() {
  var r=UrlFetchApp.fetch('https://slides.googleapis.com/v1/presentations/'+TEMPLATE_ID,
    {headers:{'Authorization':'Bearer '+ScriptApp.getOAuthToken()},muteHttpExceptions:true});
  Logger.log('Slides API: '+r.getResponseCode());
  Logger.log('Drive: '+getOrCreateTempFolder_().getName());
  Logger.log('Sheet: '+SpreadsheetApp.openById(SHEET_ID).getName());
}
