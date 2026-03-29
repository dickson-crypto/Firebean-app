/**
 * ============================================================
 * SCRIPT 3 of 3 — FIREBEAN CASE STUDY SLIDE CREATOR  v18.0
 * ============================================================
 * Deploy URL:  https://script.google.com/macros/s/AKfycbxKP-8Xrvy6hblPqTmtXn76rO3DFOeU6jYQtLw5QDfDP1-adNDk02bhoKihfvp_Xsvy/exec
 * app.py var:  CASE_STUDY_URL
 *
 * v18: 3 separate sessions to avoid timing/linking issues
 *   Session 1: REST duplicateObject — creates 2 independent slides at end
 *   Session 2: REST re-read — confirm new slides exist, get their element IDs
 *   Session 3: REST replaceAllText + SlidesApp insertImage for photos
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
    // Fast dedup
    if (pid) {
      var ex = props.getProperty(pid);
      if (ex && ex.indexOf('http') === 0) return resp_({status:'success', slide_url:ex, skipped:true});
    }
    // Try async trigger first
    try {
      props.setProperty('PAYLOAD_'+(pid||Date.now()), JSON.stringify(data));
      if (pid) props.setProperty(pid, 'QUEUED');
      ScriptApp.newTrigger('processSlideTrigger_').timeBased().after(3000).create();
      return resp_({status:'queued', project_id:pid});
    } catch(te) {
      return createSlide_(data);
    }
  } catch(err) {
    return resp_({status:'error', message:err.toString()});
  }
}

function resp_(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON);
}

function processSlideTrigger_() {
  ScriptApp.getProjectTriggers().forEach(function(t) {
    if (t.getHandlerFunction()==='processSlideTrigger_') ScriptApp.deleteTrigger(t);
  });
  var props = PropertiesService.getScriptProperties();
  var all   = props.getProperties();
  Object.keys(all).forEach(function(key) {
    if (key.indexOf('PAYLOAD_')!==0) return;
    try {
      var data = JSON.parse(all[key]);
      props.deleteProperty(key);
      createSlide_(data);
    } catch(e) { Logger.log('Trigger err: '+e.message); }
  });
}

// ─── MAIN — 3 separate sessions ──────────────────────────────────────────────

function createSlide_(data) {
  var token   = ScriptApp.getOAuthToken();
  var apiBase = 'https://slides.googleapis.com/v1/presentations/'+TEMPLATE_ID;
  var slideUrl = 'https://docs.google.com/presentation/d/'+TEMPLATE_ID+'/edit';
  var props   = PropertiesService.getScriptProperties();
  var pid     = String(data.project_id || '');

  // ScriptLock for full execution
  var lock = LockService.getScriptLock();
  if (!lock.tryLock(30000)) return resp_({status:'error', message:'Busy'});

  try {
    if (pid) {
      var st = props.getProperty(pid);
      if (st && st.indexOf('http')===0) return resp_({status:'success', slide_url:st, skipped:true});
      if (st==='RUNNING') return resp_({status:'error', message:'Already running'});
      props.setProperty(pid, 'RUNNING');
    }

    // ════════════════════════════════════════════════════════
    // SESSION 1: Duplicate template slides 1 & 2 via REST
    // Creates truly independent copies appended at the end
    // ════════════════════════════════════════════════════════
    var pres1 = JSON.parse(UrlFetchApp.fetch(apiBase,
      {headers:{'Authorization':'Bearer '+token},muteHttpExceptions:true}).getContentText());
    var tmplId1 = pres1.slides[0].objectId;
    var tmplId2 = pres1.slides[1].objectId;
    var totalBefore = pres1.slides.length;
    Logger.log('SESSION 1 — Total before: '+totalBefore+', templates: '+tmplId1+', '+tmplId2);

    var dup = JSON.parse(UrlFetchApp.fetch(apiBase+':batchUpdate',{
      method:'post', contentType:'application/json',
      headers:{'Authorization':'Bearer '+token},
      payload:JSON.stringify({requests:[
        {duplicateObject:{objectId:tmplId1}},
        {duplicateObject:{objectId:tmplId2}}
      ]}), muteHttpExceptions:true
    }).getContentText());
    var newId1 = dup.replies[0].duplicateObject.objectId;
    var newId2 = dup.replies[1].duplicateObject.objectId;
    Logger.log('SESSION 1 done — new IDs: '+newId1+', '+newId2);

    // ════════════════════════════════════════════════════════
    // SESSION 2: Re-read & confirm new slides at end
    // ════════════════════════════════════════════════════════
    Utilities.sleep(2000);
    var pres2 = JSON.parse(UrlFetchApp.fetch(apiBase,
      {headers:{'Authorization':'Bearer '+token},muteHttpExceptions:true}).getContentText());
    var totalAfter = pres2.slides.length;
    Logger.log('SESSION 2 — Total after: '+totalAfter+' (added '+(totalAfter-totalBefore)+')');

    // Find the new slides
    var slide1data = null, slide2data = null;
    pres2.slides.forEach(function(s) {
      if (s.objectId===newId1) slide1data = s;
      if (s.objectId===newId2) slide2data = s;
    });
    if (!slide1data||!slide2data) throw new Error('New slides not found after re-read');
    Logger.log('SESSION 2 done — slides confirmed at positions');

    // ════════════════════════════════════════════════════════
    // SESSION 3: Fill in text + photos + logo
    // ════════════════════════════════════════════════════════
    Utilities.sleep(1000);

    // 3a) Replace text via REST (scoped to new slides only)
    var dateStr  = (data.date||((data.event_month||'')+' '+(data.event_year||''))).trim();
    var scopeStr = Array.isArray(data.scope)?data.scope.join('\n'):String(data.scope||'').replace(/,\s*/g,'\n');
    var textReqs = [];
    [['{{CLIENT_NAME}}',data.client_name||''],
     ['{{PROJECT_NAME}}',data.project_name||''],
     ['{{CATEGORY}}',data.category||''],
     ['{{DATE}}',dateStr],
     ['{{VENUE}}',data.venue||''],
     ['{{SCOPE}}',scopeStr],
     ['{{CHALLENGE}}',data.challenge||''],
     ['{{SOLUTION}}',data.solution||'']
    ].forEach(function(p) {
      textReqs.push({replaceAllText:{
        containsText:{text:p[0],matchCase:true},
        replaceText:p[1],
        pageObjectIds:[newId1,newId2]
      }});
    });
    var txtR = UrlFetchApp.fetch(apiBase+':batchUpdate',{
      method:'post',contentType:'application/json',
      headers:{'Authorization':'Bearer '+token},
      payload:JSON.stringify({requests:textReqs}),muteHttpExceptions:true
    });
    Logger.log('SESSION 3 text: '+txtR.getResponseCode());

    // 3b) Upload photos to Drive
    var photos     = data.photos || data.images || [];
    var tempFolder = getOrCreateTempFolder_();
    var photoUrls  = [];
    for (var i=0; i<Math.min(photos.length,8); i++) {
      try {
        var url = saveBase64ToPublicDrive_(tempFolder,'ph'+(i+1)+'.jpg',photos[i],'image/jpeg');
        photoUrls.push(url);
        Logger.log('Photo '+(i+1)+' uploaded');
      } catch(e) {
        photoUrls.push(null);
        Logger.log('Photo '+(i+1)+' upload err: '+e.message);
      }
    }

    // 3c) Insert photos via SlidesApp on the new independent slides
    Utilities.sleep(500);
    var presApp = SlidesApp.openById(TEMPLATE_ID);
    var appSlide1 = null, appSlide2 = null;
    presApp.getSlides().forEach(function(s) {
      if (s.getObjectId()===newId1) appSlide1 = s;
      if (s.getObjectId()===newId2) appSlide2 = s;
    });

    if (appSlide1 && appSlide2) {
      [appSlide1, appSlide2].forEach(function(slide) {
        slide.getPageElements().forEach(function(el) {
          var alt = '';
          try { alt = el.getTitle()||''; } catch(e) {}
          if (!alt) try { alt = el.getDescription()||''; } catch(e) {}
          var m = alt.match(/^PHOTO([1-8])$/);
          if (!m) return;
          var url = photoUrls[parseInt(m[1])-1];
          if (!url) return;
          try {
            var l=el.getLeft(), t=el.getTop(), w=el.getWidth(), h=el.getHeight();
            var img = slide.insertImage(url);
            img.setLeft(l); img.setTop(t); img.setWidth(w); img.setHeight(h);
            Logger.log('PHOTO'+m[1]+' inserted');
          } catch(pe) { Logger.log('Photo insert err: '+pe.message); }
        });
      });
      Logger.log('SESSION 3 photos done');

      // 3d) Logo
      var logoB64 = data.logo_white_base64||data.logo_white||'';
      if (logoB64) {
        try {
          var logoUrl = saveBase64ToPublicDrive_(tempFolder,'logo_white.png',logoB64,'image/png');
          appSlide1.getPageElements().forEach(function(el) {
            var d='';try{d=el.getDescription()||'';}catch(e){}
            var t='';try{t=el.getTitle()||'';}catch(e){}
            if (d==='project_logo'||t==='photo1_placeholder'||t==='logo_white') {
              try {
                var l=el.getLeft(),tp=el.getTop(),w=el.getWidth(),h=el.getHeight();
                var img=appSlide1.insertImage(logoUrl);
                img.setLeft(l);img.setTop(tp);img.setWidth(w);img.setHeight(h);
                Logger.log('Logo inserted');
              } catch(le){Logger.log('Logo err: '+le.message);}
            }
          });
        } catch(le){Logger.log('Logo err: '+le.message);}
      }
    } else {
      Logger.log('WARNING: Could not find new slides via SlidesApp');
    }

    // Write URL to sheet
    updateSheetWithSlideUrl_(pid, slideUrl);
    if (pid) props.setProperty(pid, slideUrl);
    Logger.log('ALL DONE: '+slideUrl);
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
      sheet.getRange(i+1,13).setValue(slideUrl);break;
    }
  }
}

function clearStaleProperties() {
  // Run this once manually to reset all stale RUNNING/QUEUED states
  var props = PropertiesService.getScriptProperties();
  var all   = props.getProperties();
  var cleared = [];
  Object.keys(all).forEach(function(key) {
    var val = String(all[key]);
    if (val === 'RUNNING' || val === 'QUEUED' || val.indexOf('PAYLOAD_') === 0 || key.indexOf('PAYLOAD_') === 0) {
      props.deleteProperty(key);
      cleared.push(key + '=' + val);
    }
  });
  Logger.log('Cleared ' + cleared.length + ' stale properties: ' + cleared.join(', '));
}

function testAuth() {
  var r=UrlFetchApp.fetch('https://slides.googleapis.com/v1/presentations/'+TEMPLATE_ID,
    {headers:{'Authorization':'Bearer '+ScriptApp.getOAuthToken()},muteHttpExceptions:true});
  Logger.log('Slides API: '+r.getResponseCode());
  Logger.log('SlidesApp: '+SlidesApp.openById(TEMPLATE_ID).getSlides().length+' slides');
  Logger.log('Drive: '+getOrCreateTempFolder_().getName());
  Logger.log('Sheet: '+SpreadsheetApp.openById(SHEET_ID).getName());
}
