/**
 * ============================================================
 * SCRIPT 2 of 3 — MASTER DB SLIDE CREATOR  v5.0
 * ============================================================
 * Deploy URL:  https://script.google.com/macros/s/AKfycbx_7Xf8_HERQel93WJB2F_KjFOWHtCXzfvEkP9B_p7Kh4ImRAWRgWSXtLklvdbYsqbI/exec
 * app.py var:  SLIDE_DB_URL
 * Action:      create_slide
 *
 * PHOTO / LOGO STRATEGY (v5.0):
 *   1. Find each PHOTO1-8 placeholder by alt-text → record bounds → remove
 *   2. Insert blob at exact frame bounds (this stretches initially)
 *   3. Call Slides REST API batchUpdate with cropProperties to centre-crop
 *      → image fills frame like CSS object-fit:cover; object-position:center
 *      → no distortion regardless of source photo aspect ratio
 *   4. If fewer than 8 photos → unused slots keep original gradient
 *   5. Logo: same insert + crop-fill approach
 * ============================================================
 */

var TEMPLATE_ID = '19rmqCzgKD8y2ZiLxkiAqhhkV6_t-8QAumZkSi0Eu9C0';
var SHEET_ID    = '1aTuqgmmSKMWgNCl2KR0QhK4Cj8G7W5yPsr4t39pi-yc';
var SHEET_NAME  = 'Basic Info';

// Hardcoded fallback positions (points) — [left, top, width, height]
var PHOTO_COORDS = {
  'PHOTO1': [210.6,   0,     254.7, 202.5],
  'PHOTO2': [465.3,   0,     254.7, 202.5],
  'PHOTO3': [210.6, 202.5,   254.7, 202.5],
  'PHOTO4': [465.3, 202.5,   254.7, 202.5],
  'PHOTO5': [210.5,   0,     254.8, 202.5],
  'PHOTO6': [465.2,   0,     254.8, 202.5],
  'PHOTO7': [210.5, 202.5,   254.8, 202.5],
  'PHOTO8': [465.2, 202.5,   254.8, 202.5]
};
var LOGO_COORDS = [24.3, 25.5, 166.2, 71.6];

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
  } catch (err) {
    return ContentService
      .createTextOutput(JSON.stringify({status:'error', message:err.toString()}))
      .setMimeType(ContentService.MimeType.JSON);
  }
}

// ─── MAIN ────────────────────────────────────────────────────────────────────

function createCaseStudySlide_(data) {
  var slideUrl = 'https://docs.google.com/presentation/d/' + TEMPLATE_ID + '/edit';

  // 1. Get template slide objectIds (slides 0 and 1)
  var pres0 = SlidesApp.openById(TEMPLATE_ID);
  var templateSlides = pres0.getSlides();
  if (templateSlides.length < 2) throw new Error('Template needs at least 2 slides.');
  var templateId1 = templateSlides[0].getObjectId();
  var templateId2 = templateSlides[1].getObjectId();
  var totalSlides  = templateSlides.length;
  pres0.saveAndClose();

  // 2. Duplicate template slides via REST API (creates truly independent copies)
  //    duplicateObject appends the copy to the end of the presentation
  var token   = ScriptApp.getOAuthToken();
  var apiBase = 'https://slides.googleapis.com/v1/presentations/' + TEMPLATE_ID + ':batchUpdate';

  var dupResp = UrlFetchApp.fetch(apiBase, {
    method: 'post', contentType: 'application/json',
    headers: {'Authorization': 'Bearer ' + token},
    payload: JSON.stringify({requests: [
      {duplicateObject: {objectId: templateId1}},
      {duplicateObject: {objectId: templateId2}}
    ]}),
    muteHttpExceptions: true
  });

  if (dupResp.getResponseCode() !== 200) {
    // Fallback to appendSlide if REST not available
    Logger.log('duplicateObject failed, falling back to appendSlide: ' + dupResp.getContentText().substring(0,200));
    var pres1 = SlidesApp.openById(TEMPLATE_ID);
    var ts    = pres1.getSlides();
    pres1.appendSlide(ts[0]);
    pres1.appendSlide(ts[1]);
    pres1.saveAndClose();
  }

  Utilities.sleep(1500);

  // 3. Re-open — new slides are the last 2
  var presentation = SlidesApp.openById(TEMPLATE_ID);
  var allSlides    = presentation.getSlides();
  var newSlide1    = allSlides[allSlides.length - 2];
  var newSlide2    = allSlides[allSlides.length - 1];

  // 4. Clear ALL photo images from BOTH new slides immediately
  //    (duplicateObject gives independent copies we can freely modify)
  removeAllPhotoImages_(newSlide1);
  removeAllPhotoImages_(newSlide2);

  // 5. Build strings
  var dateStr = (data.date || ((data.event_month||'') + ' ' + (data.event_year||''))).trim();
  var scopeStr = Array.isArray(data.scope)
    ? data.scope.join('\n')
    : String(data.scope || '').replace(/,\s*/g, '\n');

  // 6. Replace all text placeholders
  var replacements = [
    ['{{CLIENT_NAME}}',  data.client_name  || ''],
    ['{{PROJECT_NAME}}', data.project_name || ''],
    ['{{CATEGORY}}',     data.category     || ''],
    ['{{DATE}}',         dateStr],
    ['{{VENUE}}',        data.venue        || ''],
    ['{{SCOPE}}',        scopeStr],
    ['{{CHALLENGE}}',    data.challenge || '(Challenge TBC)'],
    ['{{SOLUTION}}',     data.solution  || '(Solution TBC)']
  ];
  replacements.forEach(function(pair) {
    newSlide1.replaceAllText(pair[0], pair[1]);
    newSlide2.replaceAllText(pair[0], pair[1]);
  });

  // 6. Insert photos with crop-centre fill
  var photos = data.photos || data.images || [];
  var heroIndex = parseInt(data.hero_index || 0, 10);
  var photoResults = [];
  var cropRequests = [];

  for (var i = 0; i < Math.min(photos.length, 8); i++) {
    var photoNum  = i + 1;
    var altText   = 'PHOTO' + photoNum;
    var targetSlide = photoNum <= 4 ? newSlide1 : newSlide2;

    try {
      var imgDims   = getBase64ImageDimensions_(photos[i]);
      var blob      = base64ToBlob_(photos[i], 'image/jpeg', 'p'+photoNum+'.jpg');
      // Use hardcoded coords (alt-text not preserved after appendSlide)
      var coords    = PHOTO_COORDS[altText];

      var inserted = targetSlide.insertImage(blob, coords[0], coords[1], coords[2], coords[3]);

      // Hero gets red border
      if (i === heroIndex) {
        inserted.getBorder().getLineFill().setSolidFill('#FF2A2A');
        inserted.getBorder().setWeight(2);
      }

      // Queue a fill+crop request — pass frame dims + image dims for transform calc
      var crop = calcCropCentre_(imgDims.w, imgDims.h, coords[2], coords[3]);
      cropRequests.push({
        objectId: inserted.getObjectId(),
        crop:     crop,
        left:     coords[0], top:    coords[1],
        frameW:   coords[2], frameH: coords[3],
        imgW:     imgDims.w, imgH:   imgDims.h
      });

      photoResults.push(altText + ':OK');
    } catch (photoErr) {
      Logger.log('Photo ' + photoNum + ' failed: ' + photoErr.message);
      photoResults.push(altText + ':FAIL:' + photoErr.message);
    }
  }

  // 7. Insert white logo with crop-centre fill
  var logoBase64 = data.logo_white_base64 || data.logo_white || '';
  var logoResult = 'no_logo';
  if (logoBase64) {
    try {
      var logoDims   = getBase64ImageDimensions_(logoBase64);
      var logoBlob   = base64ToBlob_(logoBase64, 'image/png', 'logo.png');
      var logoCoords = findAndRemoveLogoShape_(newSlide1);
      if (!logoCoords) logoCoords = LOGO_COORDS;

      var logoInserted = newSlide1.insertImage(logoBlob, logoCoords[0], logoCoords[1], logoCoords[2], logoCoords[3]);
      logoInserted.setTitle('logo_white');
      logoInserted.setDescription('project_logo');

      var logoCrop = calcCropCentre_(logoDims.w, logoDims.h, logoCoords[2], logoCoords[3]);
      cropRequests.push({
        objectId: logoInserted.getObjectId(),
        crop:     logoCrop,
        left:     logoCoords[0], top:    logoCoords[1],
        frameW:   logoCoords[2], frameH: logoCoords[3],
        imgW:     logoDims.w,    imgH:   logoDims.h
      });
      logoResult = 'OK';
    } catch (logoErr) {
      Logger.log('Logo failed: ' + logoErr.message);
      logoResult = 'FAIL:' + logoErr.message;
      clearLogoPlaceholderText_(newSlide1);
    }
  }

  // 8. Save and wait — REST API needs presentation fully committed
  presentation.saveAndClose();
  Utilities.sleep(2000);

  // 9. Apply size + position + centre-crop via Slides REST API via Slides REST API in one batchUpdate
  if (cropRequests.length > 0) {
    applyCropCentreFill_(TEMPLATE_ID, cropRequests);
  }

  // 10. Update Master DB col M
  updateSheetWithSlideUrl_(data.project_id, slideUrl);

  return ContentService.createTextOutput(JSON.stringify({
    status: 'success',
    slide_url: slideUrl,
    photos: photoResults,
    logo: logoResult,
    crops_applied: cropRequests.length
  })).setMimeType(ContentService.MimeType.JSON);
}

// ─── FILL FRAME: set size + position via REST API ────────────────────────────
/**
 * CORRECT approach for object-fit:cover in Google Slides:
 *
 * Step 1: updatePageElementTransform — set position (translateX/Y), scale=1
 * Step 2: updatePageElementSize — set EXACT frame width+height
 *         After this, Slides renders image stretched to fill frame completely
 * Step 3: updateImageProperties cropProperties — calculate how much to crop
 *         based on ORIGINAL image aspect ratio vs frame aspect ratio
 *         to achieve centre-crop (show middle, trim edges)
 *
 * cropProperties fractions are relative to the ORIGINAL image dimensions,
 * NOT the rendered/stretched size. This is the key insight.
 *
 * Example: 3:2 landscape photo in a 1:1 square frame
 *   → scale to fill height: rendered width > frame width
 *   → leftOffset = rightOffset = (renderedW - frameW) / (2 * renderedW)
 *   where renderedW = originalW * (frameH / originalH)
 */

function calcCropCentre_(imgW, imgH, frameW, frameH) {
  // If no image dimensions available, no crop needed (already fills frame)
  if (!imgW || !imgH) return {leftOffset:0, rightOffset:0, topOffset:0, bottomOffset:0};

  var imgAspect   = imgW  / imgH;
  var frameAspect = frameW / frameH;

  var l = 0, r = 0, t = 0, b = 0;

  if (imgAspect > frameAspect) {
    // Photo wider than frame → fill by height, crop left+right
    // When rendered to fill height: scaledW = imgW * (frameH/imgH)
    var scaledW = imgW * (frameH / imgH);
    var excess  = (scaledW - frameW) / scaledW; // fraction of original to crop total
    l = excess / 2;
    r = excess / 2;
  } else if (imgAspect < frameAspect) {
    // Photo taller than frame → fill by width, crop top+bottom
    var scaledH = imgH * (frameW / imgW);
    var excess  = (scaledH - frameH) / scaledH;
    t = excess / 2;
    b = excess / 2;
  }

  return {
    leftOffset:   Math.max(0, Math.min(0.49, l)),
    rightOffset:  Math.max(0, Math.min(0.49, r)),
    topOffset:    Math.max(0, Math.min(0.49, t)),
    bottomOffset: Math.max(0, Math.min(0.49, b))
  };
}

/**
 * Apply fill + crop using Apps Script Slides Service only (no UrlFetchApp).
 * Uses image.setLeft/Top/Width/Height for position+size,
 * then Slides REST API via ScriptApp.getOAuthToken for crop.
 * Falls back to no-crop (still fills frame) if REST API unavailable.
 */
function applyFillAndCrop_(presentationId, requests) {
  if (!requests.length) return;

  // Step 1 & 2: Set exact size + position using Slides Service
  // (works without external_request scope)
  var pres = SlidesApp.openById(presentationId);
  var slides = pres.getSlides();

  requests.forEach(function(r) {
    // Find the image across all slides
    for (var si = 0; si < slides.length; si++) {
      var imgs = slides[si].getImages();
      for (var ii = 0; ii < imgs.length; ii++) {
        if (imgs[ii].getObjectId() === r.objectId) {
          var img = imgs[ii];
          img.setLeft(r.left);
          img.setTop(r.top);
          img.setWidth(r.frameW);
          img.setHeight(r.frameH);
          Logger.log('Positioned ' + r.objectId + ' at ' + r.left + ',' + r.top + ' ' + r.frameW + 'x' + r.frameH);
          break;
        }
      }
    }
  });

  pres.saveAndClose();
  Utilities.sleep(2000);

  // Step 3: Apply crop via REST API (requires external_request scope)
  try {
    var PT = 12700;
    var batch = requests.map(function(r) {
      return {
        updateImageProperties: {
          objectId: r.objectId,
          imageProperties: {
            cropProperties: {
              leftOffset:   r.crop.leftOffset,
              rightOffset:  r.crop.rightOffset,
              topOffset:    r.crop.topOffset,
              bottomOffset: r.crop.bottomOffset
            }
          },
          fields: 'cropProperties'
        }
      };
    });

    var token = ScriptApp.getOAuthToken();
    var url   = 'https://slides.googleapis.com/v1/presentations/' + presentationId + ':batchUpdate';
    var resp  = UrlFetchApp.fetch(url, {
      method: 'post', contentType: 'application/json',
      headers: {'Authorization': 'Bearer ' + token},
      payload: JSON.stringify({requests: batch}),
      muteHttpExceptions: true
    });
    if (resp.getResponseCode() === 200) {
      Logger.log('Crop OK: ' + requests.length + ' images centre-cropped');
    } else {
      Logger.log('Crop REST failed (images still fill frame, just not cropped): ' + resp.getResponseCode());
    }
  } catch(e) {
    Logger.log('Crop skipped (no external_request scope): ' + e.message);
    // Images still fill frame correctly via setWidth/Height — just no centre crop
  }
}

// Alias for compatibility
function applyCropCentreFill_(presentationId, requests) {
  applyFillAndCrop_(presentationId, requests);
}


// ─── HELPER: Read image pixel dimensions from base64 header ──────────────────
// Used to calculate crop offsets (original aspect ratio vs frame aspect ratio).
// Returns {w, h} in pixels. Falls back to {w:0, h:0} → no crop applied.
function getBase64ImageDimensions_(base64Data) {
  try {
    var clean = String(base64Data).replace(/^data:[^;]+;base64,/, '').replace(/\s/g, '');
    var bytes  = Utilities.base64Decode(clean.substring(0, 32));

    // JPEG: FF D8 marker, SOF at 0xC0-0xC3
    if (bytes[0] === 0xFF && bytes[1] === 0xD8) {
      var fb = Utilities.base64Decode(clean.substring(0, 600));
      for (var i = 2; i < fb.length - 9; i++) {
        if (fb[i] === 0xFF && (fb[i+1] === 0xC0 || fb[i+1] === 0xC1 ||
            fb[i+1] === 0xC2 || fb[i+1] === 0xC3)) {
          return { w: (fb[i+7] << 8) | fb[i+8], h: (fb[i+5] << 8) | fb[i+6] };
        }
      }
    }

    // PNG: 89 50 4E 47, width bytes 16-19, height 20-23
    if (bytes[0] === 0x89 && bytes[1] === 0x50) {
      var pb = Utilities.base64Decode(clean.substring(0, 64));
      return {
        w: (pb[16]<<24)|(pb[17]<<16)|(pb[18]<<8)|pb[19],
        h: (pb[20]<<24)|(pb[21]<<16)|(pb[22]<<8)|pb[23]
      };
    }
  } catch(e) {
    Logger.log('getBase64ImageDimensions_ error: ' + e.message);
  }
  return {w: 0, h: 0};
}

// ─── HELPERS — FINDING & REMOVING ───────────────────────────────────────────

/**
 * Remove ALL photo images from the slide's right grid area (left > 200pt).
 * Called once before inserting new photos to ensure no stacking.
 * Preserves logo (left < 200pt) and text shapes.
 */
function removeAllPhotoImages_(slide) {
  var images = slide.getImages();
  for (var i = images.length - 1; i >= 0; i--) {
    var img = images[i];
    var title = img.getTitle() || '';
    // Remove photos (right side, left > 200pt) but keep logo
    if (img.getLeft() > 200 || title.indexOf('PHOTO') === 0) {
      img.remove();
    }
  }
}

function removeImagesAtCoords_(slide, left, top, width, height) {
  // Legacy — now calls removeAllPhotoImages_ instead
  removeAllPhotoImages_(slide);
}

function findAndRemoveImageByAltText_(slide, altText) {
  var images = slide.getImages();
  // Log all image titles for debugging
  var titles = images.map(function(im) { return '"' + im.getTitle() + '"'; }).join(', ');
  Logger.log('findAndRemove looking for ' + altText + ' among ' + images.length + ' images: [' + titles + ']');
  for (var i = 0; i < images.length; i++) {
    var img = images[i];
    var t = (img.getTitle() || '').trim();
    var d = (img.getDescription() || '').trim();
    if (t === altText || d === altText) {
      var coords = [img.getLeft(), img.getTop(), img.getWidth(), img.getHeight()];
      Logger.log('Found ' + altText + ' at ' + JSON.stringify(coords));
      img.remove();
      return coords;
    }
  }
  Logger.log('NOT FOUND: ' + altText + ' — using fallback coords');
  return null;
}

function findAndRemoveLogoShape_(slide) {
  var shapes = slide.getShapes();
  for (var i = 0; i < shapes.length; i++) {
    var sh = shapes[i];
    if (sh.getText().asString().indexOf('{{WHITE_LOGO}}') !== -1 ||
        sh.getDescription() === 'project_logo' ||
        sh.getTitle() === 'photo1_placeholder') {
      var coords = [sh.getLeft(), sh.getTop(), sh.getWidth(), sh.getHeight()];
      sh.remove();
      return coords;
    }
  }
  return null;
}

function clearLogoPlaceholderText_(slide) {
  var shapes = slide.getShapes();
  for (var i = 0; i < shapes.length; i++) {
    if (shapes[i].getText().asString().indexOf('{{WHITE_LOGO}}') !== -1) {
      shapes[i].getText().setText('');
      return;
    }
  }
}

// ─── HELPERS — BASE64 → BLOB ─────────────────────────────────────────────────

function base64ToBlob_(base64Data, mimeType, filename) {
  var clean = String(base64Data).replace(/^data:[^;]+;base64,/, '').replace(/\s/g, '');
  var bytes = Utilities.base64Decode(clean);
  return Utilities.newBlob(bytes, mimeType, filename);
}

// ─── HELPERS — MASTER DB ─────────────────────────────────────────────────────

function updateSheetWithSlideUrl_(projectId, slideUrl) {
  if (!projectId) return;
  var ss    = SpreadsheetApp.openById(SHEET_ID);
  var sheet = ss.getSheetByName(SHEET_NAME);
  var data  = sheet.getDataRange().getValues();
  for (var i = 1; i < data.length; i++) {
    if (String(data[i][25]).toUpperCase() === String(projectId).toUpperCase()) {
      sheet.getRange(i + 1, 13).setValue(slideUrl);
      break;
    }
  }
}
