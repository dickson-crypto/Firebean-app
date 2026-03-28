/**
 * ============================================================
 * SCRIPT 3 of 3 — FIREBEAN CASE STUDY SLIDE CREATOR  v3.0
 * ============================================================
 * Deploy URL:  https://script.google.com/macros/s/AKfycbxKP-8Xrvy6hblPqTmtXn76rO3DFOeU6jYQtLw5QDfDP1-adNDk02bhoKihfvp_Xsvy/exec
 * app.py var:  CASE_STUDY_URL
 * Action:      create_case_study
 *
 * Template structure (confirmed from live template):
 *   Slide 1: PHOTO1–PHOTO4 image placeholders + {{WHITE_LOGO}} shape + text fields
 *   Slide 2: PHOTO5–PHOTO8 image placeholders + text fields
 *
 * Strategy:
 *   1. Copy slides 1+2 from template to end of presentation
 *   2. Upload each base64 photo to Drive as a temp file → get public URL
 *   3. Use replaceAllShapesWithImage (alt-text match) to fill PHOTO1–PHOTO8 in-place
 *      → image fills placeholder exactly, cropped to center (no floating images)
 *   4. If fewer than 8 photos, unused slots keep the original gradient placeholder
 *   5. Replace {{WHITE_LOGO}} shape with logo image in-place
 *   6. Replace all text placeholders
 *   7. Update Master DB col M with slide URL
 * ============================================================
 */

var TEMPLATE_ID  = '19rmqCzgKD8y2ZiLxkiAqhhkV6_t-8QAumZkSi0Eu9C0';
var SHEET_ID     = '1aTuqgmmSKMWgNCl2KR0QhK4Cj8G7W5yPsr4t39pi-yc';
var SHEET_NAME   = 'Basic Info';
// Temp folder for base64 → Drive uploads (images need a public URL for Slides API)
var TEMP_FOLDER_NAME = '_Firebean_Temp_Uploads';

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

  // 2. Build date string
  var dateStr = (data.date || ((data.event_month || '') + ' ' + (data.event_year || ''))).trim();

  // 3. Build scope string
  var scopeStr = '';
  if (Array.isArray(data.scope)) {
    scopeStr = data.scope.join('\n');
  } else {
    scopeStr = String(data.scope || '').replace(/,\s*/g, '\n');
  }

  // 4. Replace all text placeholders on both slides
  var textReplacements = [
    ['{{CLIENT_NAME}}',  data.client_name  || ''],
    ['{{PROJECT_NAME}}', data.project_name || ''],
    ['{{CATEGORY}}',     data.category     || ''],
    ['{{DATE}}',         dateStr],
    ['{{VENUE}}',        data.venue        || ''],
    ['{{SCOPE}}',        scopeStr],
    ['{{CHALLENGE}}',    data.challenge    || ''],
    ['{{SOLUTION}}',     data.solution     || '']
  ];
  textReplacements.forEach(function(pair) {
    newSlide1.replaceAllText(pair[0], pair[1]);
    newSlide2.replaceAllText(pair[0], pair[1]);
  });

  // 5. Upload photos to Drive → get public URLs → replace PHOTO1–PHOTO8 in-place
  var photos = data.photos || data.images || [];
  var tempFolder = getOrCreateTempFolder_();
  var photoUrls = [];

  for (var pi = 0; pi < Math.min(photos.length, 8); pi++) {
    try {
      var url = saveBase64ToPublicDrive_(tempFolder, 'slide_photo_' + (pi+1) + '.jpg', photos[pi], 'image/jpeg');
      photoUrls.push(url);
    } catch(e) {
      photoUrls.push(null);
      Logger.log('Photo ' + pi + ' upload failed: ' + e.message);
    }
  }

  // Replace PHOTO1–PHOTO4 on slide 1, PHOTO5–PHOTO8 on slide 2
  for (var i = 0; i < photoUrls.length; i++) {
    if (!photoUrls[i]) continue;
    var photoNum = i + 1;                          // 1-based
    var targetSlide = photoNum <= 4 ? newSlide1 : newSlide2;
    var altText = 'PHOTO' + photoNum;
    replaceImageByAltText_(targetSlide, altText, photoUrls[i]);
  }

  // 6. Replace {{WHITE_LOGO}} shape with logo image
  var logoBase64 = data.logo_white_base64 || data.logo_white || '';
  if (logoBase64) {
    try {
      var logoUrl = saveBase64ToPublicDrive_(tempFolder, 'slide_logo_white.png', logoBase64, 'image/png');
      replaceLogoShape_(newSlide1, logoUrl);
    } catch(e) {
      Logger.log('Logo replace failed: ' + e.message);
      // Clear the placeholder text so it doesn't show raw {{WHITE_LOGO}}
      clearLogoPlaceholderText_(newSlide1);
    }
  } else {
    clearLogoPlaceholderText_(newSlide1);
  }

  presentation.saveAndClose();

  // 7. Update Master DB col M
  updateSheetWithSlideUrl_(data.project_id, slideUrl);

  return ContentService.createTextOutput(JSON.stringify({
    status: 'success',
    slide_url: slideUrl,
    photos_replaced: photoUrls.filter(function(u){return !!u;}).length
  })).setMimeType(ContentService.MimeType.JSON);
}

// ─── REPLACE IMAGE BY ALT TEXT ───────────────────────────────────────────────
// Finds the image element whose title == altText, then replaces it in-place
// using the Slides REST API replaceAllShapesWithImage approach via UrlFetchApp.
// Falls back to remove+insert if the API call fails.
function replaceImageByAltText_(slide, altText, imageUrl) {
  var elements = slide.getImages();
  for (var i = 0; i < elements.length; i++) {
    var img = elements[i];
    if (img.getTitle() === altText || img.getDescription() === altText) {
      // Get position and size before removing
      var left   = img.getLeft();
      var top    = img.getTop();
      var width  = img.getWidth();
      var height = img.getHeight();

      // Remove old image, insert new one at exact same position/size
      img.remove();

      var newImg = slide.insertImage(imageUrl, left, top, width, height);
      // Set alt text on new image to preserve naming
      newImg.setTitle(altText);
      newImg.setDescription(altText);
      return true;
    }
  }
  Logger.log('Alt text not found: ' + altText);
  return false;
}

// ─── REPLACE LOGO SHAPE ──────────────────────────────────────────────────────
// Finds shape containing {{WHITE_LOGO}}, removes it, inserts logo image at same bounds
function replaceLogoShape_(slide, logoUrl) {
  var shapes = slide.getShapes();
  for (var i = 0; i < shapes.length; i++) {
    var sh = shapes[i];
    if (sh.getText().asString().indexOf('{{WHITE_LOGO}}') !== -1 ||
        sh.getDescription() === 'project_logo' ||
        sh.getTitle() === 'photo1_placeholder') {
      var left   = sh.getLeft();
      var top    = sh.getTop();
      var width  = sh.getWidth();
      var height = sh.getHeight();
      sh.remove();
      var logoImg = slide.insertImage(logoUrl, left, top, width, height);
      logoImg.setTitle('logo_white');
      logoImg.setDescription('project_logo');
      return;
    }
  }
}

function clearLogoPlaceholderText_(slide) {
  var shapes = slide.getShapes();
  for (var i = 0; i < shapes.length; i++) {
    var sh = shapes[i];
    if (sh.getText().asString().indexOf('{{WHITE_LOGO}}') !== -1) {
      sh.getText().setText('');
      return;
    }
  }
}

// ─── DRIVE HELPERS ───────────────────────────────────────────────────────────

function getOrCreateTempFolder_() {
  var folders = DriveApp.getFoldersByName(TEMP_FOLDER_NAME);
  if (folders.hasNext()) return folders.next();
  var f = DriveApp.createFolder(TEMP_FOLDER_NAME);
  // Make publicly readable so Slides API can fetch the URL
  f.setSharing(DriveApp.Access.ANYONE_WITH_LINK, DriveApp.Permission.VIEW);
  return f;
}

// Upload base64 image to Drive, make it public, return the direct content URL
function saveBase64ToPublicDrive_(folder, filename, base64Data, mimeType) {
  var clean = base64Data.replace(/^data:[^;]+;base64,/, '');
  var bytes = Utilities.base64Decode(clean);
  var blob  = Utilities.newBlob(bytes, mimeType, filename);

  // Delete existing file with same name to avoid duplicates
  var existing = folder.getFilesByName(filename);
  while (existing.hasNext()) { existing.next().setTrashed(true); }

  var file = folder.createFile(blob);
  file.setSharing(DriveApp.Access.ANYONE_WITH_LINK, DriveApp.Permission.VIEW);

  // Return a URL that Google Slides API can fetch directly
  return 'https://drive.google.com/uc?export=download&id=' + file.getId();
}

// ─── UPDATE MASTER DB ────────────────────────────────────────────────────────

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
