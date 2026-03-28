/**
 * ============================================================
 * SCRIPT 3 of 3 — FIREBEAN CASE STUDY SLIDE CREATOR  v4.0
 * ============================================================
 * Deploy URL:  https://script.google.com/macros/s/AKfycbxKP-8Xrvy6hblPqTmtXn76rO3DFOeU6jYQtLw5QDfDP1-adNDk02bhoKihfvp_Xsvy/exec
 * app.py var:  CASE_STUDY_URL
 * Action:      create_case_study
 *
 * PHOTO STRATEGY (v4.0):
 *   - Find each PHOTO1-8 placeholder by alt-text title
 *   - Record exact left/top/width/height
 *   - Delete placeholder
 *   - Decode base64 → blob → insertImage(blob, left, top, w, h)
 *   - Falls back to hardcoded coordinates if alt-text lookup fails
 *   - If no photo provided for a slot, keep original gradient (don't delete)
 *
 * LOGO STRATEGY (v4.0):
 *   - Find {{WHITE_LOGO}} shape by text content or description
 *   - Record exact bounds
 *   - Delete shape
 *   - Decode base64 → blob → insertImage(blob, left, top, w, h)
 *
 * HARDCODED FALLBACK COORDINATES (from live template, confirmed):
 *   Slide 1: PHOTO1(210.6, 0, 254.7, 202.5) PHOTO2(465.3, 0, 254.7, 202.5)
 *            PHOTO3(210.6, 202.5, 254.7, 202.5) PHOTO4(465.3, 202.5, 254.7, 202.5)
 *            LOGO(24.3, 25.5, 166.2, 71.6)
 *   Slide 2: PHOTO5(210.5, 0, 254.8, 202.5) PHOTO6(465.2, 0, 254.8, 202.5)
 *            PHOTO7(210.5, 202.5, 254.8, 202.5) PHOTO8(465.2, 202.5, 254.8, 202.5)
 * ============================================================
 */

var TEMPLATE_ID = '19rmqCzgKD8y2ZiLxkiAqhhkV6_t-8QAumZkSi0Eu9C0';
var SHEET_ID    = '1aTuqgmmSKMWgNCl2KR0QhK4Cj8G7W5yPsr4t39pi-yc';
var SHEET_NAME  = 'Basic Info';

// Hardcoded fallback positions (points) — [left, top, width, height]
var PHOTO_COORDS = {
  'PHOTO1': [210.6,   0,   254.7, 202.5],
  'PHOTO2': [465.3,   0,   254.7, 202.5],
  'PHOTO3': [210.6, 202.5, 254.7, 202.5],
  'PHOTO4': [465.3, 202.5, 254.7, 202.5],
  'PHOTO5': [210.5,   0,   254.8, 202.5],
  'PHOTO6': [465.2,   0,   254.8, 202.5],
  'PHOTO7': [210.5, 202.5, 254.8, 202.5],
  'PHOTO8': [465.2, 202.5, 254.8, 202.5]
};
var LOGO_COORDS = [24.3, 25.5, 166.2, 71.6]; // [left, top, width, height]

// ─── ENTRY POINT ─────────────────────────────────────────────────────────────

function doPost(e) {
  try {
    var data = JSON.parse(e.postData.contents);
    if (data.action === 'create_slide' || data.action === 'create_case_study') {
      return createCaseStudySlide_(data);
    }
    return ContentService.createTextOutput(JSON.stringify({status: 'error', message: 'Unknown action: ' + data.action}))
      .setMimeType(ContentService.MimeType.JSON);
  } catch (err) {
    return ContentService.createTextOutput(JSON.stringify({status: 'error', message: err.toString()}))
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
  var dateStr = (data.date || ((data.event_month || '') + ' ' + (data.event_year || ''))).trim();
  var scopeStr = Array.isArray(data.scope)
    ? data.scope.join('\n')
    : String(data.scope || '').replace(/,\s*/g, '\n');

  // 3. Replace all text placeholders on BOTH slides
  var replacements = [
    ['{{CLIENT_NAME}}',  data.client_name  || ''],
    ['{{PROJECT_NAME}}', data.project_name || ''],
    ['{{CATEGORY}}',     data.category     || ''],
    ['{{DATE}}',         dateStr],
    ['{{VENUE}}',        data.venue        || ''],
    ['{{SCOPE}}',        scopeStr],
    ['{{CHALLENGE}}',    data.challenge    || ''],
    ['{{SOLUTION}}',     data.solution     || '']
  ];
  replacements.forEach(function(pair) {
    newSlide1.replaceAllText(pair[0], pair[1]);
    newSlide2.replaceAllText(pair[0], pair[1]);
  });

  // 4. Insert photos using blob (no Drive URL needed)
  var photos = data.photos || data.images || [];
  var heroIndex = parseInt(data.hero_index || 0, 10);
  var photoResults = [];

  for (var i = 0; i < Math.min(photos.length, 8); i++) {
    var photoNum = i + 1;
    var altText  = 'PHOTO' + photoNum;
    var targetSlide = photoNum <= 4 ? newSlide1 : newSlide2;

    try {
      var blob = base64ToBlob_(photos[i], 'image/jpeg', 'photo' + photoNum + '.jpg');
      var coords = findAndRemoveImageByAltText_(targetSlide, altText);
      if (!coords) coords = PHOTO_COORDS[altText]; // fallback to hardcoded

      var img = targetSlide.insertImage(blob, coords[0], coords[1], coords[2], coords[3]);
      img.setTitle(altText);
      img.setDescription(altText);

      // Hero photo gets a subtle red border
      if (i === heroIndex) {
        img.getBorder().getLineFill().setSolidFill('#FF2A2A');
        img.getBorder().setWeight(2);
      }
      photoResults.push(altText + ':OK');
    } catch (photoErr) {
      Logger.log('Photo ' + photoNum + ' failed: ' + photoErr.message);
      photoResults.push(altText + ':FAIL:' + photoErr.message);
    }
  }

  // 5. Insert white logo using blob
  var logoBase64 = data.logo_white_base64 || data.logo_white || '';
  var logoResult = 'no_logo';
  if (logoBase64) {
    try {
      var logoBlob   = base64ToBlob_(logoBase64, 'image/png', 'logo_white.png');
      var logoCoords = findAndRemoveLogoShape_(newSlide1);
      if (!logoCoords) logoCoords = LOGO_COORDS; // fallback to hardcoded

      var logoImg = newSlide1.insertImage(logoBlob, logoCoords[0], logoCoords[1], logoCoords[2], logoCoords[3]);
      logoImg.setTitle('logo_white');
      logoImg.setDescription('project_logo');
      logoResult = 'OK';
    } catch (logoErr) {
      Logger.log('Logo failed: ' + logoErr.message);
      logoResult = 'FAIL:' + logoErr.message;
      clearLogoPlaceholderText_(newSlide1);
    }
  }

  presentation.saveAndClose();

  // 6. Update Master DB col M with slide URL
  updateSheetWithSlideUrl_(data.project_id, slideUrl);

  return ContentService.createTextOutput(JSON.stringify({
    status: 'success',
    slide_url: slideUrl,
    photos: photoResults,
    logo: logoResult
  })).setMimeType(ContentService.MimeType.JSON);
}

// ─── HELPERS — IMAGE FINDING ─────────────────────────────────────────────────

/**
 * Finds image element by alt-text title, records its bounds, removes it.
 * Returns [left, top, width, height] in points, or null if not found.
 */
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
  return null; // Not found — caller uses hardcoded fallback
}

/**
 * Finds the {{WHITE_LOGO}} shape, records its bounds, removes it.
 * Returns [left, top, width, height] in points, or null if not found.
 */
function findAndRemoveLogoShape_(slide) {
  var shapes = slide.getShapes();
  for (var i = 0; i < shapes.length; i++) {
    var sh = shapes[i];
    var isLogo = (
      sh.getText().asString().indexOf('{{WHITE_LOGO}}') !== -1 ||
      sh.getDescription() === 'project_logo' ||
      sh.getTitle() === 'photo1_placeholder'
    );
    if (isLogo) {
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
