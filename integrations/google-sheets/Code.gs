/**
 * GBSBFORYOU Floating Project Office -> Google Sheets bridge
 * Deploy as a Google Apps Script Web App (Execute as: Me; access: Anyone).
 * Do not put secrets/API keys in this sheet. The endpoint accepts project-office records only.
 */
const SHEET_ID = 'PASTE_YOUR_GOOGLE_SHEET_ID_HERE';
const TABS = {
  projects: ['Project ID','Project Name','Purpose / Summary','Status','Priority','Platform','Repository URL','Next Action','Created At','Updated At'],
  activities: ['Entry ID','Project ID','Entry Type','Title','Platform','Work Details','Status','Priority','Next Action','Conversation URL','Repository / Resource URL','Timestamp UTC'],
  misc: ['Title','Platform','Details','Conversation URL','Resource URL','Timestamp UTC']
};
function doGet() {
  return ContentService.createTextOutput(JSON.stringify({ok:true,service:'GBSBFORYOU Sheets Bridge',version:'1.0'})).setMimeType(ContentService.MimeType.JSON);
}
function doPost(e) {
  try {
    const payload = JSON.parse((e && e.postData && e.postData.contents) || '{}');
    if (!payload || !['project','activity','misc','snapshot'].includes(payload.type)) throw new Error('Unsupported record type');
    if (SHEET_ID === 'PASTE_YOUR_GOOGLE_SHEET_ID_HERE') throw new Error('Configure SHEET_ID in Apps Script first');
    const ss = SpreadsheetApp.openById(SHEET_ID);
    if (payload.type === 'snapshot') {
      const data = payload.data || {};
      writeRows_(ss, 'Project Register', TABS.projects, (data.projects||[]).map(p=>[p.id,p.title,p.goal,p.status,p.priority,p.platform,p.asset,p.next,p.createdAt,p.updatedAt]));
      writeRows_(ss, 'Daily Cashbook', TABS.activities, (data.activities||[]).map(a=>[a.id,a.projectId,a.kind,a.title,a.platform,a.details,a.status,a.priority,a.next,a.conversation,a.asset,a.at]));
      writeRows_(ss, 'Miscellaneous', TABS.misc, (data.misc||[]).map(m=>[m.title,m.platform,m.details,m.conversation,m.asset,m.at]));
    } else if (payload.type === 'project') {
      const p=payload.data||{}; append_(ss,'Project Register',TABS.projects,[p.id,p.title,p.goal,p.status,p.priority,p.platform,p.asset,p.next,p.createdAt,p.updatedAt]);
    } else if (payload.type === 'activity') {
      const a=payload.data||{}; append_(ss,'Daily Cashbook',TABS.activities,[a.id,a.projectId,a.kind,a.title,a.platform,a.details,a.status,a.priority,a.next,a.conversation,a.asset,a.at]);
    } else {
      const m=payload.data||{}; append_(ss,'Miscellaneous',TABS.misc,[m.title,m.platform,m.details,m.conversation,m.asset,m.at]);
    }
    return json_({ok:true,type:payload.type,at:new Date().toISOString()});
  } catch(err) { return json_({ok:false,error:String(err.message||err)}); }
}
function append_(ss,name,headers,row) { const sh=sheet_(ss,name,headers); sh.appendRow(row); }
function writeRows_(ss,name,headers,rows) { const sh=sheet_(ss,name,headers); sh.clearContents(); sh.getRange(1,1,1,headers.length).setValues([headers]); if(rows.length) sh.getRange(2,1,rows.length,headers.length).setValues(rows); sh.setFrozenRows(1); }
function sheet_(ss,name,headers) { let sh=ss.getSheetByName(name); if(!sh) sh=ss.insertSheet(name); if(sh.getLastRow()===0) sh.appendRow(headers); sh.setFrozenRows(1); return sh; }
function json_(o) { return ContentService.createTextOutput(JSON.stringify(o)).setMimeType(ContentService.MimeType.JSON); }
