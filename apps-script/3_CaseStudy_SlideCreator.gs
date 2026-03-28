/**
 * ============================================================
 * SCRIPT 3 of 3 — FIREBEAN CASE STUDY SLIDE CREATOR
 * ============================================================
 * Deploy URL:  https://script.google.com/macros/s/AKfycbxKP-8Xrvy6hblPqTmtXn76rO3DFOeU6jYQtLw5QDfDP1-adNDk02bhoKihfvp_Xsvy/exec
 * app.py var:  CASE_STUDY_URL
 * Action:      create_case_study
 *
 * What it does:
 *   - Same as Script 2 but for a SEPARATE Case Study presentation
 *   - Creates a standalone Firebean case study deck per project
 *   - Can use a different template or the same one
 *
 * Template Slides ID:  19rmqCzgKD8y2ZiLxkiAqhhkV6_t-8QAumZkSi0Eu9C0
 * Google Sheet:        1aTuqgmmSKMWgNCl2KR0QhK4Cj8G7W5yPsr4t39pi-yc
 * ============================================================
 */

/**
 * FIREBEAN GOOGLE SLIDES GENERATOR  v2.0
 * Receives webhook from Streamlit app.py
 * - Duplicates template slides 1+2 to end of Master presentation
 * - Fills text placeholders (client, project, venue, date, scope, category)
 * - Inserts project photos into photo grid on slide 1
 * - Inserts white logo (from base64) onto slide 1
 * - Updates Master DB col M (Google Slide URL)
 */

var TEMPLATE_ID = '19rmqCzgKD8y2ZiLxkiAqhhkV6_t-8QAumZkSi0Eu9C0';
var SHEET_ID    = '1aTuqgmmSKMWgNCl2KR0QhK4Cj8G7W5yPsr4t39pi-yc';
var SHEET_NAME  = 'Basic Info';

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

function createCaseStudySlide_(data) {
  // 1. Open Master Presentation
  var presentation = SlidesApp.openById(TEMPLATE_ID);
  var slideUrl = 'https://docs.google.com/presentation/d/' + TEMPLATE_ID + '/edit';

  // 2. Get template slides (index 0 = cover slide, index 1 = detail slide)
  var slides = presentation.getSlides();
  if (slides.length < 2) {
    throw new Error('Master presentation needs at least 2 template slides.');
  }

  // 3. Append copies of templates to end of presentation
  var slide1 = presentation.appendSlide(slides[0]); // Cover / photo grid
  var slide2 = presentation.appendSlide(slides[1]); // Detail / text slide

  // ── 4. Fill text on Slide 2 (detail) ─────────────────────────────────────
  var dateStr = (data.date || ((data.event_month || '') + ' ' + (data.event_year || ''))).trim();
  var scopeStr = Array.isArray(data.scope)
    ? data.scope.join('\n')
    : String(data.scope || '').replace(/,\s*/g, '\n');

  slide2.replaceAllText('{{CLIENT_NAME}}',  data.client_name  || '');
  slide2.replaceAllText('{{PROJECT_NAME}}', data.project_name || '');
  slide2.replaceAllText('{{VENUE}}',        data.venue        || '');
  slide2.replaceAllText('{{DATE}}',         dateStr);
  slide2.replaceAllText('{{CATEGORY}}',     data.category     || '');
  slide2.replaceAllText('{{SCOPE}}',        scopeStr);
  slide2.replaceAllText('{{CHALLENGE}}',    data.challenge    || '');
  slide2.replaceAllText('{{SOLUTION}}',     data.solution     || '');

  // ── 5. Fill text on Slide 1 (cover) ──────────────────────────────────────
  slide1.replaceAllText('{{CLIENT_NAME}}',  data.client_name  || '');
  slide1.replaceAllText('{{PROJECT_NAME}}', data.project_name || '');
  slide1.replaceAllText('Test Client',      data.client_name  || '');

  // Also fill empty shapes by Y-position (legacy support)
  var shapes1 = slide1.getShapes();
  for (var i = 0; i < shapes1.length; i++) {
    var sh = shapes1[i];
    var txt = sh.getText().asString().trim();
    var y   = sh.getTop();
    if (txt === '') {
      if      (y > 100 && y < 120) sh.getText().setText(data.category     || '');
      else if (y > 130 && y < 140) sh.getText().setText(data.project_name || '');
      else if (y > 190 && y < 200) sh.getText().setText(dateStr);
      else if (y > 230 && y < 240) sh.getText().setText(data.venue        || '');
      else if (y > 270 && y < 285) sh.getText().setText(scopeStr);
    }
  }

  // ── 6. Insert photos into Slide 1 ────────────────────────────────────────
  // Use data.photos[] or data.images[] (both are base64 JPEG arrays)
  var photos = data.photos || data.images || [];
  if (photos.length > 0) {
    insertPhotosIntoSlide_(slide1, photos, data.hero_index || 0);
  }

  // ── 7. Insert white logo ──────────────────────────────────────────────────
  var logoBase64 = data.logo_white_base64 || data.logo_white || '';
  if (logoBase64) {
    insertLogoIntoSlide_(slide1, logoBase64);
  }

  // ── 8. Save ───────────────────────────────────────────────────────────────
  presentation.saveAndClose();

  // ── 9. Update Master DB col M (Google Slide URL) ──────────────────────────
  updateSheetWithSlideUrl_(data.project_id, slideUrl);

  return ContentService.createTextOutput(JSON.stringify({
    status: 'success',
    slide_url: slideUrl,
    slides_added: 2
  })).setMimeType(ContentService.MimeType.JSON);
}

// ── Insert photos into a 2×3 grid on slide1 ──────────────────────────────────
function insertPhotosIntoSlide_(slide, photos, heroIndex) {
  // Get dimensions from the presentation object (not the slide)
  var pres    = SlidesApp.openById(TEMPLATE_ID);
  var slideW  = pres.getPageWidth();   // points, e.g. 720
  var slideH  = pres.getPageHeight();  // points, e.g. 405

  // Right half of slide = photo area (left half = text/logo area)
  var photoAreaLeft  = slideW * 0.5;
  var photoAreaTop   = 0;
  var photoAreaW     = slideW * 0.5;
  var photoAreaH     = slideH;

  var maxPhotos = Math.min(photos.length, 6); // max 6 = 2 cols × 3 rows
  var cols = maxPhotos <= 3 ? 1 : 2;
  var rows = Math.ceil(maxPhotos / cols);

  var cellW = photoAreaW / cols;
  var cellH = photoAreaH / rows;

  // Delete any existing image shapes in the photo area (right half)
  var existingImages = slide.getImages();
  for (var ei = 0; ei < existingImages.length; ei++) {
    var img = existingImages[ei];
    if (img.getLeft() >= photoAreaLeft * 0.9) {
      img.remove();
    }
  }

  for (var pi = 0; pi < maxPhotos; pi++) {
    try {
      var col = pi % cols;
      var row = Math.floor(pi / cols);
      var x = photoAreaLeft + col * cellW;
      var y = photoAreaTop  + row * cellH;

      var cleanB64 = String(photos[pi]).replace(/^data:[^;]+;base64,/, '');
      var bytes    = Utilities.base64Decode(cleanB64);
      var blob     = Utilities.newBlob(bytes, 'image/jpeg', 'photo_' + pi + '.jpg');

      var inserted = slide.insertImage(blob, x, y, cellW, cellH);

      // Hero gets a subtle highlight border
      if (pi === heroIndex) {
        inserted.getBorder().getLineFill().setSolidFill('#FF0000');
        inserted.getBorder().setWeight(3);
      }
    } catch (photoErr) {
      Logger.log('Photo ' + pi + ' insert error: ' + photoErr.message);
    }
  }
}

// ── Insert white logo — look for {{WHITE_LOGO}} placeholder, replace with image ─
function insertLogoIntoSlide_(slide, logoBase64) {
  var shapes = slide.getShapes();
  var logoPlaceholder = null;

  for (var i = 0; i < shapes.length; i++) {
    if (shapes[i].getText().asString().indexOf('{{WHITE_LOGO}}') !== -1) {
      logoPlaceholder = shapes[i];
      break;
    }
  }

  try {
    var cleanB64 = logoBase64.replace(/^data:[^;]+;base64,/, '');
    var bytes    = Utilities.base64Decode(cleanB64);
    var blob     = Utilities.newBlob(bytes, 'image/png', 'logo_white.png');

    if (logoPlaceholder) {
      // Replace placeholder shape with logo image at same position/size
      var lx = logoPlaceholder.getLeft();
      var ly = logoPlaceholder.getTop();
      var lw = logoPlaceholder.getWidth();
      var lh = logoPlaceholder.getHeight();
      logoPlaceholder.remove();
      slide.insertImage(blob, lx, ly, lw, lh);
    } else {
      // No placeholder found — insert at top-left of slide
      slide.insertImage(blob, 20, 20, 120, 50);
    }
  } catch (logoErr) {
    Logger.log('Logo insert error: ' + logoErr.message);
    // Clear placeholder text if image failed
    if (logoPlaceholder) logoPlaceholder.getText().setText('');
  }
}

// ── Update Master DB col M with slide URL ────────────────────────────────────
function updateSheetWithSlideUrl_(projectId, slideUrl) {
  if (!projectId) return;
  var ss    = SpreadsheetApp.openById(SHEET_ID);
  var sheet = ss.getSheetByName(SHEET_NAME);
  var data  = sheet.getDataRange().getValues();

  for (var i = 1; i < data.length; i++) {
    if (String(data[i][25]).toUpperCase() === String(projectId).toUpperCase()) {
      sheet.getRange(i + 1, 13).setValue(slideUrl); // col M = Google Slide
      break;
    }
  }
}
