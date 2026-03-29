/**
 * ============================================================
 * SCRIPT 2 of 3 — MASTER DB SLIDE CREATOR  v16.0
 * ============================================================
 * Deploy URL:  https://script.google.com/macros/s/AKfycbwAFo739fMIFwSYWaIZNw9ILiJk96tlnlVWlg8PdbrGYd1SzEGaAc4E_P4aLyNB3tnp/exec
 * app.py var:  SLIDE_DB_URL
 *
 * v16 approach (back to basics — what worked):
 *   - doPost returns IMMEDIATELY with {status:'queued'} to stop Google retries
 *   - Stores payload in PropertiesService
 *   - Schedules a time trigger to do the real work asynchronously
 *   - processSlideTrigger_() duplicates last 2 template slides, appends at END
 *   - Uses SlidesApp only (no REST API mixing) — replaceAllText + image insertion
 *   - Photos inserted via replaceImage on PHOTO1-PHOTO8 placeholder alt-text shapes
 * ============================================================
 */

var TEMPLATE_ID = '19rmqCzgKD8y2ZiLxkiAqhhkV6_t-8QAumZkSi0Eu9C0';
var SHEET_ID    = '1aTuqgmmSKMWgNCl2KR0QhK4Cj8G7W5yPsr4t39pi-yc';
var SHEET_NAME  = 'Basic Info';

// ─── ENTRY POINT — returns immediately to prevent Google retries ──────────────

function doPost(e) {
  try {
    var data = JSON.parse(e.postData.contents);
    if (data.action !== 'create_slide' && data.action !== 'create_case_study') {
      return resp_({status:'error', message:'Unknown action'});
    }

    var pid   = String(data.project_id || '');
    var props = PropertiesService.getScriptProperties();

    // Fast dedup check
    if (pid) {
      var existing = props.getProperty(pid);
      if (existing) {
        if (existing.indexOf('http') === 0) return resp_({status:'success', slide_url:existing, skipped:true});
        return resp_({status:'queued', message:'Already processing'});
      }
      props.setProperty(pid, 'PROCESSING');
    }

    // Try async trigger first; fall back to sync if no permission
    try {
      var key = 'PAYLOAD_' + (pid || String(new Date().getTime()));
      props.setProperty(key, JSON.stringify(data));
      ScriptApp.newTrigger('processSlideTrigger_')
        .timeBased().after(3000).create();
      return resp_({status:'queued', project_id:pid, message:'Slide creation started'});
    } catch(triggerErr) {
      // No trigger permission — run synchronously
      Logger.log('Trigger failed, running sync: ' + triggerErr.message);
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

// ─── ASYNC TRIGGER — runs 3s after doPost, does the real work ─────────────────

function processSlideTrigger_() {
  // Delete all pending triggers of this type
  ScriptApp.getProjectTriggers().forEach(function(t) {
    if (t.getHandlerFunction() === 'processSlideTrigger_') ScriptApp.deleteTrigger(t);
  });

  var props = PropertiesService.getScriptProperties();
  var all   = props.getProperties();

  Object.keys(all).forEach(function(key) {
    if (key.indexOf('PAYLOAD_') !== 0) return;
    try {
      var data = JSON.parse(all[key]);
      props.deleteProperty(key); // delete before processing — prevents double-run
      createSlide_(data);
    } catch(e) {
      Logger.log('Trigger error for ' + key + ': ' + e.message);
    }
  });
}

// ─── MAIN SLIDE CREATOR ───────────────────────────────────────────────────────

function createSlide_(data) {
  var pres     = SlidesApp.openById(TEMPLATE_ID);
  var slides   = pres.getSlides();
  var slideUrl = 'https://docs.google.com/presentation/d/' + TEMPLATE_ID + '/edit';
  var props    = PropertiesService.getScriptProperties();
  var pid      = String(data.project_id || '');

  // Double-check dedup — in sync mode, retries may reach here concurrently
  if (pid) {
    var state = props.getProperty(pid);
    if (state && state !== 'PROCESSING') {
      // Already done or in progress by another instance
      Logger.log('SKIP in createSlide_: ' + pid + ' = ' + state);
      if (state.indexOf('http') === 0) return resp_({status:'success', slide_url:state, skipped:true});
      return resp_({status:'error', message:'Already processing'});
    }
    // Mark as IN_PROGRESS so concurrent retries skip
    props.setProperty(pid, 'IN_PROGRESS_' + new Date().getTime());
  }

  Logger.log('createSlide_ for: ' + pid + ' | Total slides: ' + slides.length);

  // ── STEP 1: Duplicate template slides 1 & 2, append at END ───────────────────
  // Check last 2 slides don't already have this project name (prevents retry duplicates)
  var allSlidesBefore = pres.getSlides();
  var lastSlide = allSlidesBefore[allSlidesBefore.length - 1];
  var lastSlideText = '';
  try {
    lastSlide.getPageElements().forEach(function(el) {
      try { lastSlideText += el.asShape().getText().asString(); } catch(e) {}
    });
  } catch(e) {}
  var projName = String(data.project_name || '');
  if (projName && lastSlideText.indexOf(projName) >= 0) {
    Logger.log('SKIP — slides already exist for: ' + projName);
    if (pid) props.setProperty(pid, slideUrl);
    updateSheetWithSlideUrl_(pid, slideUrl);
    return resp_({status:'success', slide_url:slideUrl, skipped:true});
  }

  var newSlide1 = pres.appendSlide(slides[0]);
  var newSlide2 = pres.appendSlide(slides[1]);
  Logger.log('Appended 2 slides at end. New total: ' + pres.getSlides().length);

  // ── STEP 2: Replace text placeholders ────────────────────────────────────────
  var dateStr  = (data.date || ((data.event_month||'') + ' ' + (data.event_year||''))).trim();
  var scopeStr = Array.isArray(data.scope)
    ? data.scope.join('\n')
    : String(data.scope||'').replace(/,\s*/g, '\n');

  var pairs = [
    ['{{CLIENT_NAME}}',  data.client_name  || ''],
    ['{{PROJECT_NAME}}', data.project_name || ''],
    ['{{CATEGORY}}',     data.category     || ''],
    ['{{DATE}}',         dateStr],
    ['{{VENUE}}',        data.venue        || ''],
    ['{{SCOPE}}',        scopeStr],
    ['{{CHALLENGE}}',    data.challenge    || ''],
    ['{{SOLUTION}}',     data.solution     || '']
  ];

  [newSlide1, newSlide2].forEach(function(slide) {
    pairs.forEach(function(pair) {
      slide.replaceAllText(pair[0], pair[1]);
    });
  });
  Logger.log('Text replaced');

  // ── STEP 3: Upload photos to Drive temp folder ────────────────────────────────
  var photos    = data.photos || data.images || [];
  var tempFolder = getOrCreateTempFolder_();
  var photoUrls = [];

  for (var i = 0; i < Math.min(photos.length, 8); i++) {
    try {
      var url = saveBase64ToPublicDrive_(tempFolder, 'ph'+(i+1)+'.jpg', photos[i], 'image/jpeg');
      photoUrls.push(url);
      Logger.log('Photo '+(i+1)+' uploaded: ' + url);
    } catch(e) {
      Logger.log('Photo '+(i+1)+' failed: ' + e.message);
      photoUrls.push(null);
    }
  }

  // ── STEP 4: Insert photos into PHOTO1-PHOTO8 placeholder shapes ───────────────
  // Find shapes by alt-text title matching PHOTO1..PHOTO8
  var allSlides = [newSlide1, newSlide2];
  var photoIndex = 0;

  allSlides.forEach(function(slide) {
    slide.getPageElements().forEach(function(el) {
      var title = '';
      try { title = el.getTitle() || ''; } catch(e) {}
      var desc  = '';
      try { desc = el.getDescription() || ''; } catch(e) {}
      var altText = title || desc;

      // Match PHOTO1-PHOTO8
      if (/^PHOTO[1-8]$/.test(altText)) {
        var num = parseInt(altText.replace('PHOTO','')) - 1;
        var url = photoUrls[num];
        if (!url) return;
        try {
          // Get the shape's position and size to place image exactly
          var pos  = el.getLeft();
          var top  = el.getTop();
          var w    = el.getWidth();
          var h    = el.getHeight();
          // Delete placeholder shape and insert image at exact same position
          el.remove();
          var img = slide.insertImage(url);
          img.setLeft(pos); img.setTop(top);
          img.setWidth(w);  img.setHeight(h);
          Logger.log('Inserted ' + altText + ' at ' + pos + ',' + top);
        } catch(pe) {
          Logger.log('Photo insert error for ' + altText + ': ' + pe.message);
        }
      }
    });
  });

  // ── STEP 5: Logo ──────────────────────────────────────────────────────────────
  var logoB64 = data.logo_white_base64 || data.logo_white || '';
  if (logoB64) {
    try {
      var logoUrl = saveBase64ToPublicDrive_(tempFolder, 'logo_white.png', logoB64, 'image/png');
      // Find logo placeholder on slide 1
      newSlide1.getPageElements().forEach(function(el) {
        var title = ''; try { title = el.getTitle() || ''; } catch(e) {}
        var desc  = ''; try { desc = el.getDescription() || ''; } catch(e) {}
        if (desc === 'project_logo' || title === 'photo1_placeholder' || title === 'logo_white') {
          var pos = el.getLeft(), top = el.getTop(), w = el.getWidth(), h = el.getHeight();
          el.remove();
          var img = newSlide1.insertImage(logoUrl);
          img.setLeft(pos); img.setTop(top);
          img.setWidth(w);  img.setHeight(h);
          Logger.log('Logo inserted');
        }
      });
    } catch(le) {
      Logger.log('Logo error: ' + le.message);
    }
  }

  // ── STEP 6: Write URL back to sheet ──────────────────────────────────────────
  if (pid) {
    props.setProperty(pid, slideUrl);
    updateSheetWithSlideUrl_(pid, slideUrl);
  }
  Logger.log('Done: ' + slideUrl);
  return resp_({status:'success', slide_url:slideUrl});
}

// ─── HELPERS ─────────────────────────────────────────────────────────────────

function getOrCreateTempFolder_() {
  var n = '_Firebean_SlideTemp';
  var it = DriveApp.getFoldersByName(n);
  var f  = it.hasNext() ? it.next() : DriveApp.createFolder(n);
  try { f.setSharing(DriveApp.Access.ANYONE_WITH_LINK, DriveApp.Permission.VIEW); } catch(e) {}
  return f;
}

function saveBase64ToPublicDrive_(folder, filename, b64, mimeType) {
  var clean = String(b64).replace(/^data:[^;]+;base64,/, '').replace(/\s/g, '');
  var bytes = Utilities.base64Decode(clean);
  var blob  = Utilities.newBlob(bytes, mimeType, filename);
  var it    = folder.getFilesByName(filename);
  while (it.hasNext()) { it.next().setTrashed(true); }
  var file  = folder.createFile(blob);
  try { file.setSharing(DriveApp.Access.ANYONE_WITH_LINK, DriveApp.Permission.VIEW); } catch(e) {}
  return 'https://drive.google.com/thumbnail?id=' + file.getId() + '&sz=s4000';
}

function updateSheetWithSlideUrl_(projectId, slideUrl) {
  if (!projectId) return;
  var sheet = SpreadsheetApp.openById(SHEET_ID).getSheetByName(SHEET_NAME);
  var vals  = sheet.getDataRange().getValues();
  for (var i = 1; i < vals.length; i++) {
    if (String(vals[i][25]).toUpperCase() === String(projectId).toUpperCase()) {
      sheet.getRange(i+1, 13).setValue(slideUrl);
      break;
    }
  }
}

function testAuth() {
  Logger.log('Slides: ' + SlidesApp.openById(TEMPLATE_ID).getSlides().length);
  Logger.log('Drive: ' + getOrCreateTempFolder_().getName());
  Logger.log('Sheet: ' + SpreadsheetApp.openById(SHEET_ID).getName());
}
