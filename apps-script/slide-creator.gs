/**
 * FIREBEAN GOOGLE SLIDES GENERATOR
 * Receives webhook from Streamlit, opens the Master presentation,
 * duplicates the template slides (pages 1-2) to the end,
 * replaces placeholders and empty shapes on the new slides, 
 * then updates the Master DB.
 */

var TEMPLATE_ID = '19rmqCzgKD8y2ZiLxkiAqhhkV6_t-8QAumZkSi0Eu9C0';
var SHEET_ID = '1aTuqgmmSKMWgNCl2KR0QhK4Cj8G7W5yPsr4t39pi-yc';
var SHEET_NAME = 'Basic Info';

function doPost(e) {
  try {
    var data = JSON.parse(e.postData.contents);
    
    if (data.action !== 'create_slide') {
      return ContentService.createTextOutput(JSON.stringify({status: 'error', message: 'Unknown action'}))
        .setMimeType(ContentService.MimeType.JSON);
    }
    
    // 1. Open Master Presentation
    var presentation = SlidesApp.openById(TEMPLATE_ID);
    var slideUrl = 'https://docs.google.com/presentation/d/' + TEMPLATE_ID + '/edit';
    
    // 2. Get template slides (Page 1 and Page 2, which are index 0 and 1)
    var slides = presentation.getSlides();
    if (slides.length < 2) {
      throw new Error("Master presentation does not have at least 2 template slides.");
    }
    var templateSlide1 = slides[0];
    var templateSlide2 = slides[1];
    
    // 3. Append template slides to the end of the presentation
    var slide1 = presentation.appendSlide(templateSlide1);
    var slide2 = presentation.appendSlide(templateSlide2);
    
    // 4. Replace Text Placeholders on the newly appended slides
    slide1.replaceAllText('Test Client', data.client_name || '');
    slide2.replaceAllText('{{CLIENT_NAME}}', data.client_name || '');
    slide2.replaceAllText('{{PROJECT_NAME}}', data.project_name || '');
    slide2.replaceAllText('{{CHALLENGE}}', data.challenge || '');
    slide2.replaceAllText('{{SOLUTION}}', data.solution || '');
    
    // 5. Fill empty shapes in Slide 1 based on Y-position
    var shapes = slide1.getShapes();
    for (var i = 0; i < shapes.length; i++) {
      var shape = shapes[i];
      var text = shape.getText().asString().trim();
      var y = shape.getTop();
      
      // If it's an empty shape, fill it based on its Y position
      if (text === '') {
        if (y > 100 && y < 120) {
          // Category (y=114)
          shape.getText().setText(data.category || '');
        } else if (y > 130 && y < 140) {
          // Project Name (y=132)
          shape.getText().setText(data.project_name || '');
        } else if (y > 190 && y < 200) {
          // Date value (y=193)
          shape.getText().setText(data.date || '');
        } else if (y > 230 && y < 240) {
          // Venue value (y=232)
          shape.getText().setText(data.venue || '');
        } else if (y > 270 && y < 285) {
          // Scope value (y=279)
          var scopeText = (data.scope || '').replace(/,/g, '\n');
          shape.getText().setText(scopeText);
        }
      }
    }
    
    // 6. Replace White Logo
    if (data.logo_white_url) {
      // Find the shape containing {{WHITE_LOGO}}
      for (var i = 0; i < shapes.length; i++) {
        var shape = shapes[i];
        if (shape.getText().asString().indexOf('{{WHITE_LOGO}}') !== -1) {
          try {
            // Get file ID from URL
            var fileIdMatch = data.logo_white_url.match(/id=([a-zA-Z0-9_-]+)/);
            if (fileIdMatch && fileIdMatch[1]) {
              var logoFile = DriveApp.getFileById(fileIdMatch[1]);
              var blob = logoFile.getBlob();
              slide1.insertImage(blob, shape.getLeft(), shape.getTop(), shape.getWidth(), shape.getHeight());
              shape.remove(); // Remove the text placeholder shape
            } else {
              shape.getText().setText(''); // Clear placeholder if no valid ID
            }
          } catch (e) {
            Logger.log('Error replacing logo: ' + e);
            shape.getText().setText(''); // Clear placeholder on error
          }
          break;
        }
      }
    } else {
      // Clear placeholder if no logo
      for (var i = 0; i < shapes.length; i++) {
        var shape = shapes[i];
        if (shape.getText().asString().indexOf('{{WHITE_LOGO}}') !== -1) {
          shape.getText().setText('');
          break;
        }
      }
    }
    
    presentation.saveAndClose();
    
    // 7. Update Master DB
    updateSheetWithSlideUrl(data.project_id, slideUrl);
    
    return ContentService.createTextOutput(JSON.stringify({
      status: 'success', 
      slide_url: slideUrl
    })).setMimeType(ContentService.MimeType.JSON);
    
    } catch (err) {
    return ContentService.createTextOutput(JSON.stringify({
      status: 'error', 
      message: err.toString()
    })).setMimeType(ContentService.MimeType.JSON);
  }
}

function updateSheetWithSlideUrl(projectId, slideUrl) {
  if (!projectId) return;
  
  var ss = SpreadsheetApp.openById(SHEET_ID);
  var sheet = ss.getSheetByName(SHEET_NAME);
  var data = sheet.getDataRange().getValues();
  
  // Find row by Project ID (Column Z / 26)
  for (var i = 1; i < data.length; i++) {
    if (String(data[i][25]) === String(projectId)) {
      // Update Column M (13) with Slide URL
      sheet.getRange(i + 1, 13).setValue(slideUrl);
      break;
    }
  }
}
