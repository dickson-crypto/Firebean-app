/**
 * ============================================================
 * SCRIPT 2 of 3 — MASTER DB SLIDE CREATOR  v9.0 (Pure REST)
 * ============================================================
 * Deploy URL:  https://script.google.com/macros/s/AKfycbx_7Xf8_HERQel93WJB2F_KjFOWHtCXzfvEkP9B_p7Kh4ImRAWRgWSXtLklvdbYsqbI/exec
 * app.py var:  SLIDE_DB_URL
 * Action:      create_slide
 *
 * v9.0: Pure REST API approach
 *   - appendSlide (SlidesApp) for duplication — simpler and reliable
 *   - All photo operations via REST batchUpdate:
 *     deleteObject (remove template photos) + createImage (insert new)
 *   - cropProperties + size set in same createImage request
 *   - One batchUpdate call handles everything: delete + create + text replace
 * ============================================================
 */

var TEMPLATE_ID = '19rmqCzgKD8y2ZiLxkiAqhhkV6_t-8QAumZkSi0Eu9C0';
var SHEET_ID    = '1aTuqgmmSKMWgNCl2KR0QhK4Cj8G7W5yPsr4t39pi-yc';
var SHEET_NAME  = 'Basic Info';

// Photo grid positions in EMU (1pt = 12700 EMU)
var PT = 12700;
var PHOTO_EMU = {
  'PHOTO1': {l:210.6*PT, t:0,       w:254.7*PT, h:202.5*PT},
  'PHOTO2': {l:465.3*PT, t:0,       w:254.7*PT, h:202.5*PT},
  'PHOTO3': {l:210.6*PT, t:202.5*PT,w:254.7*PT, h:202.5*PT},
  'PHOTO4': {l:465.3*PT, t:202.5*PT,w:254.7*PT, h:202.5*PT},
  'PHOTO5': {l:210.5*PT, t:0,       w:254.8*PT, h:202.5*PT},
  'PHOTO6': {l:465.2*PT, t:0,       w:254.8*PT, h:202.5*PT},
  'PHOTO7': {l:210.5*PT, t:202.5*PT,w:254.8*PT, h:202.5*PT},
  'PHOTO8': {l:465.2*PT, t:202.5*PT,w:254.8*PT, h:202.5*PT}
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
      .createTextOutput(JSON.stringify({status:'error',message:'Unknown action: '+data.action}))
      .setMimeType(ContentService.MimeType.JSON);
  } catch(err) {
    return ContentService
      .createTextOutput(JSON.stringify({status:'error',message:err.toString()}))
      .setMimeType(ContentService.MimeType.JSON);
  }
}

// ─── MAIN ────────────────────────────────────────────────────────────────────

function createCaseStudySlide_(data) {
  var token   = ScriptApp.getOAuthToken();
  var apiBase = 'https://slides.googleapis.com/v1/presentations/' + TEMPLATE_ID;
  var slideUrl = 'https://docs.google.com/presentation/d/' + TEMPLATE_ID + '/edit';

  // 1. Read current presentation to get template slide objectIds + their photo element IDs
  var getResp = UrlFetchApp.fetch(apiBase, {
    headers:{'Authorization':'Bearer '+token}, muteHttpExceptions:true
  });
  if (getResp.getResponseCode() !== 200) throw new Error('GET pres failed: '+getResp.getResponseCode());

  var pres = JSON.parse(getResp.getContentText());
  var slides = pres.slides;
  var tmpl1  = slides[0];
  var tmpl2  = slides[1];

  // Collect objectIds of images to delete from the new slides (photo + logo placeholders)
  var tmpl1PhotoIds = [];
  var tmpl2PhotoIds = [];
  var tmpl1LogoId   = null;

  (tmpl1.pageElements || []).forEach(function(el) {
    if (el.image) {
      var t = el.title || ''; var d = el.description || '';
      if (t === 'PHOTO1'||t==='PHOTO2'||t==='PHOTO3'||t==='PHOTO4') tmpl1PhotoIds.push(el.objectId);
      else if (d === 'project_logo' || t === 'photo1_placeholder' || t === 'logo_white') {
        // skip logo placeholder — we'll handle it separately
      }
    }
    if (el.shape && (el.description === 'project_logo' || el.title === 'photo1_placeholder')) {
      tmpl1LogoId = el.objectId;
    }
  });
  (tmpl2.pageElements || []).forEach(function(el) {
    if (el.image) {
      var t = el.title || '';
      if (t==='PHOTO5'||t==='PHOTO6'||t==='PHOTO7'||t==='PHOTO8') tmpl2PhotoIds.push(el.objectId);
    }
  });

  // 2. Duplicate both template slides via REST
  var dupResp = UrlFetchApp.fetch(apiBase+':batchUpdate', {
    method:'post', contentType:'application/json',
    headers:{'Authorization':'Bearer '+token},
    payload: JSON.stringify({requests:[
      {duplicateObject:{objectId: tmpl1.objectId}},
      {duplicateObject:{objectId: tmpl2.objectId}}
    ]}),
    muteHttpExceptions:true
  });
  if (dupResp.getResponseCode() !== 200) throw new Error('Duplicate failed: '+dupResp.getContentText().substring(0,300));

  var dupResult = JSON.parse(dupResp.getContentText());
  var newId1 = dupResult.replies[0].duplicateObject.objectId;
  var newId2 = dupResult.replies[1].duplicateObject.objectId;
  Logger.log('New slide IDs: ' + newId1 + ', ' + newId2);

  // 3. Re-read presentation to get the new slide elements (with new objectIds)
  Utilities.sleep(1000);
  getResp = UrlFetchApp.fetch(apiBase, {
    headers:{'Authorization':'Bearer '+token}, muteHttpExceptions:true
  });
  pres = JSON.parse(getResp.getContentText());
  slides = pres.slides;

  // Find our new slides by objectId
  var newSlideData1 = null, newSlideData2 = null;
  slides.forEach(function(s) {
    if (s.objectId === newId1) newSlideData1 = s;
    if (s.objectId === newId2) newSlideData2 = s;
  });
  if (!newSlideData1 || !newSlideData2) throw new Error('Could not find new slides: '+newId1+', '+newId2);

  // 4. Collect element IDs to delete + logo shape ID on new slide 1
  var deleteIds  = [];
  var newLogoId  = null;

  (newSlideData1.pageElements || []).forEach(function(el) {
    if (el.image) deleteIds.push(el.objectId); // delete ALL images on slide 1
    if (el.shape && (el.description === 'project_logo' || el.title === 'photo1_placeholder')) {
      newLogoId = el.objectId;
    }
  });
  (newSlideData2.pageElements || []).forEach(function(el) {
    if (el.image) deleteIds.push(el.objectId); // delete ALL images on slide 2
  });

  Logger.log('Deleting ' + deleteIds.length + ' images. Logo shape: ' + newLogoId);

  // 5. Build the mega batchUpdate:
  //    a) Delete all photos
  //    b) Delete logo shape
  //    c) Replace all text
  //    d) Create new photo images with exact size + crop
  //    e) Create logo image

  var requests = [];

  // a) Delete old photos
  deleteIds.forEach(function(id) {
    requests.push({deleteObject:{objectId:id}});
  });

  // b) Delete logo shape (we'll replace with image)
  if (newLogoId) requests.push({deleteObject:{objectId:newLogoId}});

  // c) Replace text placeholders
  var dateStr = (data.date || ((data.event_month||'')+' '+(data.event_year||''))).trim();
  var scopeStr = Array.isArray(data.scope) ? data.scope.join('\n') : String(data.scope||'').replace(/,\s*/g,'\n');
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
    [newId1, newId2].forEach(function(slideId) {
      requests.push({replaceAllText:{
        containsText:{text:pair[0],matchCase:true},
        replaceText:pair[1],
        pageObjectIds:[slideId]
      }});
    });
  });

  // d) Upload photos to Drive as temp files, get URLs, create images
  var photos    = data.photos || data.images || [];
  var heroIndex = parseInt(data.hero_index || 0, 10);
  var photoResults = [];
  var tempFolder = getOrCreateTempFolder_();

  for (var i = 0; i < Math.min(photos.length, 8); i++) {
    var photoNum = i + 1;
    var altText  = 'PHOTO' + photoNum;
    var slideId  = photoNum <= 4 ? newId1 : newId2;
    var pos      = PHOTO_EMU[altText];

    try {
      var imgDims = getBase64ImageDimensions_(photos[i]);
      var url     = saveBase64ToPublicDrive_(tempFolder, 'ph'+photoNum+'.jpg', photos[i], 'image/jpeg');
      var crop    = calcCropCentre_(imgDims.w, imgDims.h, pos.w/PT, pos.h/PT);

      requests.push({createImage:{
        url: url,
        objectId: 'NEWPHOTO_'+photoNum+'_'+newId1.replace(/[^a-z0-9]/gi,''),
        elementProperties:{
          pageObjectId: slideId,
          size:{
            width: {magnitude:pos.w, unit:'EMU'},
            height:{magnitude:pos.h, unit:'EMU'}
          },
          transform:{
            scaleX:1, scaleY:1,
            translateX:pos.l, translateY:pos.t,
            unit:'EMU'
          }
        }
      }});

      photoResults.push(altText+':OK');
    } catch(pe) {
      Logger.log('Photo '+photoNum+' error: '+pe.message);
      photoResults.push(altText+':FAIL:'+pe.message);
    }
  }

  // e) Logo image
  var logoResult  = 'no_logo';
  var logoBase64  = data.logo_white_base64 || data.logo_white || '';
  if (logoBase64) {
    try {
      var logoUrl = saveBase64ToPublicDrive_(tempFolder, 'logo_white.png', logoBase64, 'image/png');
      requests.push({createImage:{
        url: logoUrl,
        objectId: 'NEWLOGO_'+newId1.replace(/[^a-z0-9]/gi,''),
        elementProperties:{
          pageObjectId: newId1,
          size:{width:{magnitude:LOGO_EMU.w,unit:'EMU'},height:{magnitude:LOGO_EMU.h,unit:'EMU'}},
          transform:{scaleX:1,scaleY:1,translateX:LOGO_EMU.l,translateY:LOGO_EMU.t,unit:'EMU'}
        }
      }});
      logoResult = 'OK';
    } catch(le) {
      Logger.log('Logo error: '+le.message);
      logoResult = 'FAIL:'+le.message;
    }
  }

  // 6. Execute the mega batchUpdate
  Utilities.sleep(500);
  var batchResp = UrlFetchApp.fetch(apiBase+':batchUpdate', {
    method:'post', contentType:'application/json',
    headers:{'Authorization':'Bearer '+token},
    payload: JSON.stringify({requests:requests}),
    muteHttpExceptions:true
  });

  if (batchResp.getResponseCode() !== 200) {
    Logger.log('batchUpdate FAILED: '+batchResp.getContentText().substring(0,500));
    throw new Error('batchUpdate failed: '+batchResp.getResponseCode()+': '+batchResp.getContentText().substring(0,200));
  }
  Logger.log('batchUpdate OK: '+requests.length+' requests');

  // 7. Apply cropProperties via second batchUpdate (after images are created)
  Utilities.sleep(1500);
  var cropRequests = [];
  for (var j = 0; j < Math.min(photos.length, 8); j++) {
    var pn   = j + 1;
    var at   = 'PHOTO' + pn;
    var pos2 = PHOTO_EMU[at];
    var dims = getBase64ImageDimensions_(photos[j]);
    var cr   = calcCropCentre_(dims.w, dims.h, pos2.w/PT, pos2.h/PT);
    var oid  = 'NEWPHOTO_'+pn+'_'+newId1.replace(/[^a-z0-9]/gi,'');
    cropRequests.push({updateImageProperties:{
      objectId:oid,
      imageProperties:{cropProperties:{
        leftOffset:cr.leftOffset, rightOffset:cr.rightOffset,
        topOffset:cr.topOffset,   bottomOffset:cr.bottomOffset
      }},
      fields:'cropProperties'
    }});
  }

  if (cropRequests.length > 0) {
    var cropResp = UrlFetchApp.fetch(apiBase+':batchUpdate', {
      method:'post', contentType:'application/json',
      headers:{'Authorization':'Bearer '+token},
      payload:JSON.stringify({requests:cropRequests}),
      muteHttpExceptions:true
    });
    Logger.log('Crop update: '+cropResp.getResponseCode());
  }

  // 8. Update Master DB col M
  updateSheetWithSlideUrl_(data.project_id, slideUrl);

  return ContentService.createTextOutput(JSON.stringify({
    status:'success', slide_url:slideUrl,
    photos:photoResults, logo:logoResult,
    requests_sent: requests.length,
    new_slides:[newId1,newId2]
  })).setMimeType(ContentService.MimeType.JSON);
}

// ─── CROP MATH ────────────────────────────────────────────────────────────────

function calcCropCentre_(imgW, imgH, frameW, frameH) {
  if (!imgW||!imgH) return {leftOffset:0,rightOffset:0,topOffset:0,bottomOffset:0};
  var ia = imgW/imgH, fa = frameW/frameH;
  var l=0,r=0,t=0,b=0;
  if (ia > fa) { var sw=imgW*(frameH/imgH),f=(sw-frameW)/sw; l=f/2; r=f/2; }
  else if (ia < fa) { var sh=imgH*(frameW/imgW),f=(sh-frameH)/sh; t=f/2; b=f/2; }
  return {
    leftOffset:Math.max(0,Math.min(0.49,l)), rightOffset:Math.max(0,Math.min(0.49,r)),
    topOffset:Math.max(0,Math.min(0.49,t)),  bottomOffset:Math.max(0,Math.min(0.49,b))
  };
}

// ─── IMAGE DIMENSIONS ─────────────────────────────────────────────────────────

function getBase64ImageDimensions_(base64Data) {
  try {
    var clean=String(base64Data).replace(/^data:[^;]+;base64,/,'').replace(/\s/g,'');
    var bytes=Utilities.base64Decode(clean.substring(0,32));
    if (bytes[0]===0xFF&&bytes[1]===0xD8) {
      var fb=Utilities.base64Decode(clean.substring(0,600));
      for (var i=2;i<fb.length-9;i++) {
        if (fb[i]===0xFF&&(fb[i+1]===0xC0||fb[i+1]===0xC1||fb[i+1]===0xC2||fb[i+1]===0xC3))
          return {w:(fb[i+7]<<8)|fb[i+8],h:(fb[i+5]<<8)|fb[i+6]};
      }
    }
    if (bytes[0]===0x89&&bytes[1]===0x50) {
      var pb=Utilities.base64Decode(clean.substring(0,64));
      return {w:(pb[16]<<24)|(pb[17]<<16)|(pb[18]<<8)|pb[19],h:(pb[20]<<24)|(pb[21]<<16)|(pb[22]<<8)|pb[23]};
    }
  } catch(e) { Logger.log('dims err: '+e.message); }
  return {w:0,h:0};
}

// ─── DRIVE HELPERS ────────────────────────────────────────────────────────────

function getOrCreateTempFolder_() {
  var name='_Firebean_SlideTemp';
  var it=DriveApp.getFoldersByName(name);
  var f=it.hasNext()?it.next():DriveApp.createFolder(name);
  f.setSharing(DriveApp.Access.ANYONE_WITH_LINK,DriveApp.Permission.VIEW);
  return f;
}

function saveBase64ToPublicDrive_(folder, filename, base64Data, mimeType) {
  var clean=String(base64Data).replace(/^data:[^;]+;base64,/,'').replace(/\s/g,'');
  var bytes=Utilities.base64Decode(clean);
  var blob=Utilities.newBlob(bytes,mimeType,filename);
  var existing=folder.getFilesByName(filename);
  while(existing.hasNext()){existing.next().setTrashed(true);}
  var file=folder.createFile(blob);
  file.setSharing(DriveApp.Access.ANYONE_WITH_LINK,DriveApp.Permission.VIEW);
  return 'https://drive.google.com/uc?export=download&id='+file.getId();
}

// ─── MASTER DB ────────────────────────────────────────────────────────────────

function updateSheetWithSlideUrl_(projectId, slideUrl) {
  if (!projectId) return;
  var sheet=SpreadsheetApp.openById(SHEET_ID).getSheetByName(SHEET_NAME);
  var data=sheet.getDataRange().getValues();
  for (var i=1;i<data.length;i++) {
    if (String(data[i][25]).toUpperCase()===String(projectId).toUpperCase()) {
      sheet.getRange(i+1,13).setValue(slideUrl); break;
    }
  }
}
