# Google Sheets connection — GBSBFORYOU Floating Project Office

This bridge is prepared, but it is not connected to a live sheet until the owner supplies a Google Sheet ID and deploys the Apps Script web app.

## One-time setup (mobile browser; desktop-site mode may help)
1. Create/open the Google Sheet that should be the central register.
2. In its URL, copy the ID between `/d/` and `/edit`.
3. Open script.google.com, create a project, and paste `Code.gs` from this folder.
4. Replace `PASTE_YOUR_GOOGLE_SHEET_ID_HERE` with that Sheet ID.
5. Deploy > New deployment > Web app; Execute as: Me; Who has access: Anyone. Review access implications before publishing.
6. Copy the Web App URL ending in `/exec`. The app must be configured with that URL before writes can sync.
7. Test with non-sensitive sample data first.

Tabs created by the bridge: Project Register, Daily Cashbook, Miscellaneous.
The current browser-only app still stores its own local copy. A true live connection requires configuring the Web App URL in the frontend and testing it. The bridge's `snapshot` action replaces rows in those three tabs, so use it only when intentionally syncing a complete snapshot.

Never store API keys, passwords, access tokens, or private credentials in the sheet.
