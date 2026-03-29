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
  var presentation = SlidesApp.openById(TEMPLATE_ID);
  var slideUrl = 'https://docs.google.com/presentation/d/' + TEMPLATE_ID + '/edit';

  var templateSlides = presentation.getSlides();
  if (templateSlides.length < 2) throw new Error('Template needs at least 2 slides.');

  // 1. Append copies of template slides 1 & 2 to end
  var newSlide1 = presentation.appendSlide(templateSlides[0]);
  var newSlide2 = presentation.appendSlide(templateSlides[1]);

  // 2. Build strings
  var dateStr = (data.date || ((data.event_month||'') + ' ' + (data.event_year||''))).trim();
  var scopeStr = Array.isArray(data.scope)
    ? data.scope.join('\n')
    : String(data.scope || '').replace(/,\s*/g, '\n');

  // 3. Replace all text placeholders
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

  // 4. Save now so we can use REST API on the new slide objects
  presentation.saveAndClose();

  // 5. Re-open to get updated objectIds for the new slides
  presentation = SlidesApp.openById(TEMPLATE_ID);
  var allSlides = presentation.getSlides();
  newSlide1 = allSlides[allSlides.length - 2];
  newSlide2 = allSlides[allSlides.length - 1];

  // 6. Insert photos with crop-centre fill
  var photos = data.photos || data.images || [];
  var heroIndex = parseInt(data.hero_index || 0, 10);
  var photoResults = [];
  var cropRequests = []; // collected for batch REST call

  for (var i = 0; i < Math.min(photos.length, 8); i++) {
    var photoNum  = i + 1;
    var altText   = 'PHOTO' + photoNum;
    var targetSlide = photoNum <= 4 ? newSlide1 : newSlide2;

    try {
      var imgDims   = getBase64ImageDimensions_(photos[i]);
      var blob      = base64ToBlob_(photos[i], 'image/jpeg', 'p'+photoNum+'.jpg');
      var coords = findAndRemoveImageByAltText_(targetSlide, altText);
      if (!coords) {
        // Alt-text placeholder not found — use hardcoded coords
        // Also remove any existing image at that grid position (gradient placeholder)
        coords = PHOTO_COORDS[altText];
        removeImagesAtCoords_(targetSlide, coords[0], coords[1], coords[2], coords[3]);
      }

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

  // 8. Save before REST API call
  presentation.saveAndClose();

  // 9. Apply all crop-centre fills via Slides REST API in one batchUpdate
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

function applyFillAndCrop_(presentationId, requests) {
  if (!requests.length) return;
  var PT = 12700; // 1 point = 12700 EMU
  var batch = [];

  requests.forEach(function(r) {
    var fw = Math.round(r.frameW * PT);
    var fh = Math.round(r.frameH * PT);
    var tx = Math.round(r.left   * PT);
    var ty = Math.round(r.top    * PT);

    // 1. Position (scaleX/Y = 1, just translate)
    batch.push({
      updatePageElementTransform: {
        objectId:  r.objectId,
        transform: { scaleX:1, scaleY:1, translateX:tx, translateY:ty, unit:'EMU' },
        applyMode: 'ABSOLUTE'
      }
    });

    // 2. Set exact frame size → image stretches to fill
    batch.push({
      updatePageElementSize: {
        objectId: r.objectId,
        size: {
          width:  { magnitude: fw, unit:'EMU' },
          height: { magnitude: fh, unit:'EMU' }
        }
      }
    });

    // 3. Centre-crop based on original aspect ratio
    batch.push({
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
    });
  });

  var token    = ScriptApp.getOAuthToken();
  var url      = 'https://slides.googleapis.com/v1/presentations/' + presentationId + ':batchUpdate';
  var resp     = UrlFetchApp.fetch(url, {
    method: 'post', contentType: 'application/json',
    headers: {'Authorization': 'Bearer ' + token},
    payload: JSON.stringify({requests: batch}),
    muteHttpExceptions: true
  });
  if (resp.getResponseCode() !== 200) {
    Logger.log('Fill+crop FAILED: ' + resp.getContentText().substring(0, 300));
  } else {
    Logger.log('Fill+crop OK: ' + requests.length + ' images');
  }
}

// Keep old name as alias for compatibility
function applyCropCentreFill_(presentationId, requests) {
  applyFillAndCrop_(presentationId, requests);
}

// ─── HELPERS — FINDING & REMOVING ───────────────────────────────────────────

/**
 * Remove all images whose bounding box overlaps significantly with the given coords.
 * Used when alt-text lookup fails (template slide was already modified by a previous sync).
 * Tolerance: 20pt — removes any image whose centre falls within the frame.
 */
function removeImagesAtCoords_(slide, left, top, width, height) {
  var cx = left  + width  / 2;
  var cy = top   + height / 2;
  var images = slide.getImages();
  for (var i = 0; i < images.length; i++) {
    var img = images[i];
    var il = img.getLeft();
    var it = img.getTop();
    var iw = img.getWidth();
    var ih = img.getHeight();
    var icx = il + iw / 2;
    var icy = it + ih / 2;
    // If image centre is within 20pt of our frame centre → remove it
    if (Math.abs(icx - cx) < 20 && Math.abs(icy - cy) < 20) {
      img.remove();
    }
  }
}

function findAndRemoveImageByAltText_(slide, altText) {
  var images = slide.getImages();
  for (var i = 0; i < images.length; i++) {
    var img = images[i];
    if (img.getTitle() === altText || img.getDescription() === altText) {
      var coords = [img.getLeft(), img.getTop(), img.getWidth(), img.getHeight()];
      img.remove();
      return coords;
    }
  }
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
