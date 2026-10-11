# RJ Realty Open House Sign-In

Owner: Ricky Lee, RJ Realty. Prefers zero manual steps; do the work, report briefly.

## What this is
- Single-page sign-in app: `index.html`, hosted on GitHub Pages at https://rickyjessielee-rgb.github.io/rj-open-house/
- Backend: Google Apps Script web app bound to the sheet "RJ Realty Open House Leads"
  - Sheet ID: 1l3UzDw1iQcJSfLjDmA_f7xAG_KA-7175PiPcMfWVNgQ
  - Web app URL (keep this URL; update the existing deployment, never create a new one):
    https://script.google.com/macros/s/AKfycbzaSIhO5skUUTQ1rubyozaxCP1BkD0eO5s6vKMh_FAa4qioYbjJT2tpQ0xy6sshsB6i/exec
  - Source of truth for the script: `apps-script/Code.gs`

## Hard rule
Guests must never see any "saved to Google Sheets" style message. The success screen stays "Thank you! Enjoy exploring the home."

## Status (Oct 11, 2026)
- Deployment access fixed (Anyone). Sign-ins save to the sheet with Synced = Yes.
- DONE: `apps-script/Code.gs` (with doGet) pushed via clasp and deployed to the existing deployment as version 5
  ("doGet ping"), same URL. Script ID: 1_AEtjpY4K6On9R7-mb4A3LAUdC3yHlxvA9iBXv4ZIYk19nT83oMeq0DR
- To verify: open `<exec URL>?ping=1`; expect `{"status":"ok"}`, then Settings > Test Connection should be green.
  (Not verified from the cloud sandbox: script.google.com is blocked by its network policy.)
- To redeploy later: `clasp clone <scriptId>`, copy Code.gs over Code.js, `clasp push -f`,
  `clasp deploy -i AKfycbzaSIhO5skUUTQ1rubyozaxCP1BkD0eO5s6vKMh_FAa4qioYbjJT2tpQ0xy6sshsB6i -d "<note>"`

## Other open items
- Sheet cleanup: Damietta rows (20239-20249 drag-fill error, no dates), ~200 email-only rows, duplicates
  (Sean Kumbhani, kyle.lamunyon), test entries (Ricky/Jessie, "Regina Phalange"), typos (gmai.com, "Dover Canyon",
  "Guanajuanto"), inconsistent property names. Confirm with Ricky before deleting anything.
