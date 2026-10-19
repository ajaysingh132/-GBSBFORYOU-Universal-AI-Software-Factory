# GBSBFORYOU Digital Project Office

## Governance
- Project Officer: C.G. Bharti (designated role name; not a real employee unless separately appointed).
- AI coordination assistant: ChatGPT.
- Central office identifier: GBS-000.
- Founder retains final approval for material decisions, publication, deployment, external spending, and destructive actions.

## Registers and meanings
- Daily Diary (Rोजनामचा): timestamped activity entries.
- Daily Project Cashbook (कैशबुक): date-wise list of every project worked on that day, with work summary, outcome, evidence link, and next action. This is not a financial ledger.
- Project Ledger (लेजर): the permanent, detailed ID page for one project, including origin, goals, status, activity history, platforms, links, milestones, decisions, blockers, and remaining work.
- Miscellaneous Register: useful ideas, links, and resources not yet assigned to a project.
- Platform Journey: chronological history of each AI/platform handoff under the same project ID.
- Pending Work Register: incomplete tasks, blocker, priority, due date when known, and next action.

## Assistant officer roles (role names are proposed)
- Aarav Sharma — Project Registration Officer.
- Kavita Verma — Daily Diary Officer.
- Rohan Mehta — Daily Project Cashbook Officer.
- Neha Joshi — Project Ledger Officer.
- Imran Khan — Platform Coordination Officer.
- Pooja Sharma — Documents and Links Officer.
- Vikram Patel — Pending Work Officer.
- Meera Singh — Progress Reporting Officer.
- Ankit Verma — Verification Officer.
- Sana Khan — Miscellaneous Register Officer.

These are workflow roles, not separate active AI agents or real staff appointments. ChatGPT coordinates them as logical responsibilities until software automation is implemented.

## Capture workflow
1. User submits project name, purpose, source platform, conversation URL if available, and any repo/demo/docs/storage/workflow links.
2. Search existing records before creating a new project to reduce duplicates.
3. Allocate a stable GBS-### ID. ID assignment must be atomic and never reuse an ID.
4. Store server timestamp in UTC and display date/time in Asia/Kolkata.
5. Add a timestamped activity to the project diary and a date-wise summary to the daily project cashbook.
6. Update the same project's ledger and platform journey; do not create a new ID just because the AI platform changes.
7. Record incomplete work with a next action. Never mark work verified/complete without suitable evidence.
8. Keep old history; corrections should be added as new audit entries rather than silently erasing history.

## Required project fields
Project ID; project name; purpose; creation time; last update; status; priority; source platform; model/provider when known; conversation URLs; GitHub repository and commit links; live/demo URL; workflow/automation link; API/docs links; storage location; version; completed work; pending work; blockers; next action; evidence; keywords.

## Security and limitations
- Do not store passwords, API keys, tokens, or other secrets in the registry.
- A platform change does not grant automatic access to private conversations on the new platform. User-shared links/content or authorized connectors are required.
- A standard PWA cannot display a true system-wide Android overlay above other apps. MVP should use a mobile capture page and Share/paste flow; a true overlay would require a separate Android app and permissions.
- Do not expose unauthenticated write endpoints on a public host. Add authentication and access controls before public deployment.
- The existing SQLite store is a single-instance MVP and does not by itself provide cloud sync or a durable multi-device registry.
- Google Sheets sync, notifications, backups, and external-platform integrations must be explicitly configured and tested before being described as active.

## Acceptance criteria
- Mobile-friendly project capture.
- Stable, sequential, non-reused project ID.
- Search by ID, name, platform, status, keyword, and repository URL.
- Date-wise daily project cashbook.
- Detailed project ledger and timestamped diary.
- Platform journey under the same ID.
- Pending tasks with next action and evidence status.
- Export of registry data.
- Automated tests for ID allocation, date handling, duplicate prevention, activity history, search, and export.
- Honest status reporting: proposed, in progress, blocked, testing, verified, complete.