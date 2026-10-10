// RJ Realty Open House Sign-In — Google Apps Script backend
// Paste into: Google Sheet > Extensions > Apps Script (replace everything)
// Deploy: Deploy > Manage deployments > edit > Execute as: Me,
//         Who has access: Anyone > Version: New version > Deploy

var SHEET_ID = '1l3UzDw1iQcJSfLjDmA_f7xAG_KA-7175PiPcMfWVNgQ';

function json_(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}

// Connection test from the app (Settings > Test Connection). Adds no row.
function doGet(e) {
  return json_({ status: 'ok', service: 'rj-open-house' });
}

function doPost(e) {
  var lock = LockService.getScriptLock();
  try {
    lock.waitLock(10000);
    var data = JSON.parse(e.postData.contents);
    if (data.ping) return json_({ status: 'ok' });
    var sheet = SpreadsheetApp.openById(SHEET_ID).getSheets()[0];
    sheet.appendRow([
      data.name || '',
      data.email || '',
      data.phone || '',
      data.wechat || '',
      data.property || '',
      data.date || '',
      data.time || '',
      'Yes'
    ]);
    return json_({ status: 'ok' });
  } catch (err) {
    return json_({ status: 'error', message: String(err) });
  } finally {
    try { lock.releaseLock(); } catch (ignore) {}
  }
}
