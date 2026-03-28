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
      var coords    = findAndRemoveImageByAltText_(targetSlide, altText);
      if (!coords) coords = PHOTO_COORDS[altText];

      var inserted  = targetSlide.insertImage(blob, coords[0], coords[1], coords[2], coords[3]);

      // Hero gets red border
      if (i === heroIndex) {
        inserted.getBorder().getLineFill().setSolidFill('#FF2A2A');
        inserted.getBorder().setWeight(2);
      }

      // Queue a crop-centre request for this image
      var crop = calcCropCentre_(imgDims.w, imgDims.h, coords[2], coords[3]);
      cropRequests.push({objectId: inserted.getObjectId(), crop: crop});

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
      cropRequests.push({objectId: logoInserted.getObjectId(), crop: logoCrop});
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

// ─── CROP-CENTRE MATH ────────────────────────────────────────────────────────
/**
 * Calculates cropProperties for object-fit:cover + object-position:center.
 * Google Slides cropProperties use fractional offsets (0.0–1.0) where:
 *   leftOffset  = fraction of image width to crop from the left
 *   rightOffset = fraction of image width to crop from the right
 *   topOffset   = fraction of image height to crop from the top
 *   bottomOffset= fraction of image height to crop from the bottom
 *
 * To fill frameW×frameH from imgW×imgH centred:
 *   If img is wider than frame (relative to height): crop sides equally
 *   If img is taller than frame (relative to width):  crop top/bottom equally
 */
function calcCropCentre_(imgW, imgH, frameW, frameH) {
  // Avoid divide-by-zero
  if (!imgW || !imgH || !frameW || !frameH) {
    return {leftOffset:0, rightOffset:0, topOffset:0, bottomOffset:0};
  }

  var imgAspect   = imgW / imgH;
  var frameAspect = frameW / frameH;

  var leftOffset = 0, rightOffset = 0, topOffset = 0, bottomOffset = 0;

  if (imgAspect > frameAspect) {
    // Image is wider → crop sides
    // Scale so height matches: scaledW = imgW * (frameH / imgH)
    var scaledW  = imgW * (frameH / imgH);
    var cropFrac = (scaledW - frameW) / scaledW; // total fraction to remove
    leftOffset   = cropFrac / 2;
    rightOffset  = cropFrac / 2;
  } else if (imgAspect < frameAspect) {
    // Image is taller → crop top/bottom
    var scaledH  = imgH * (frameW / imgW);
    var cropFrac = (scaledH - frameH) / scaledH;
    topOffset    = cropFrac / 2;
    bottomOffset = cropFrac / 2;
  }
  // If same aspect ratio: no crop needed (all offsets = 0)

  return {
    leftOffset:   Math.max(0, leftOffset),
    rightOffset:  Math.max(0, rightOffset),
    topOffset:    Math.max(0, topOffset),
    bottomOffset: Math.max(0, bottomOffset)
  };
}

/**
 * Applies cropProperties to a list of image elements via Slides REST API batchUpdate.
 * Each item in requests: { objectId: string, crop: {leftOffset, rightOffset, topOffset, bottomOffset} }
 */
function applyCropCentreFill_(presentationId, requests) {
  var batchRequests = requests.map(function(r) {
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

  var token   = ScriptApp.getOAuthToken();
  var url     = 'https://slides.googleapis.com/v1/presentations/' + presentationId + ':batchUpdate';
  var payload = JSON.stringify({requests: batchRequests});

  var response = UrlFetchApp.fetch(url, {
    method: 'post',
    contentType: 'application/json',
    headers: {'Authorization': 'Bearer ' + token},
    payload: payload,
    muteHttpExceptions: true
  });

  if (response.getResponseCode() !== 200) {
    Logger.log('Crop batchUpdate failed: ' + response.getContentText().substring(0, 500));
  } else {
    Logger.log('Crop batchUpdate OK: ' + requests.length + ' images cropped');
  }
}

/**
 * Reads image dimensions from base64 JPEG/PNG header bytes.
 * Returns {w, h} in pixels. Falls back to {w:0, h:0} on failure.
 */
function getBase64ImageDimensions_(base64Data) {
  try {
    var clean = String(base64Data).replace(/^data:[^;]+;base64,/, '').replace(/\s/g, '');
    var bytes = Utilities.base64Decode(clean.substring(0, 32)); // only need header

    // JPEG: starts with FF D8, dimensions at specific offsets
    if (bytes[0] === 0xFF && bytes[1] === 0xD8) {
      // Full decode needed to find SOF marker — use full header
      var fullBytes = Utilities.base64Decode(clean.substring(0, 500));
      for (var i = 2; i < fullBytes.length - 8; i++) {
        if (fullBytes[i] === 0xFF &&
            (fullBytes[i+1] === 0xC0 || fullBytes[i+1] === 0xC1 ||
             fullBytes[i+1] === 0xC2 || fullBytes[i+1] === 0xC3)) {
          var h = (fullBytes[i+5] << 8) | fullBytes[i+6];
          var w = (fullBytes[i+7] << 8) | fullBytes[i+8];
          return {w: w, h: h};
        }
      }
    }

    // PNG: starts with 89 50 4E 47, width at bytes 16-19, height at 20-23
    if (bytes[0] === 0x89 && bytes[1] === 0x50) {
      var pngBytes = Utilities.base64Decode(clean.substring(0, 64));
      var w = (pngBytes[16]<<24)|(pngBytes[17]<<16)|(pngBytes[18]<<8)|pngBytes[19];
      var h = (pngBytes[20]<<24)|(pngBytes[21]<<16)|(pngBytes[22]<<8)|pngBytes[23];
      return {w: w, h: h};
    }
  } catch(e) {
    Logger.log('getBase64ImageDimensions_ error: ' + e.message);
  }
  return {w: 0, h: 0}; // unknown → no crop offset applied
}

// ─── HELPERS — FINDING & REMOVING ───────────────────────────────────────────

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
