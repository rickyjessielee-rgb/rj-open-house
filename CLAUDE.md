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

## Status (Oct 10, 2026)
- Deployment access fixed (Anyone). Sign-ins save to the sheet with Synced = Yes.
- OPEN: the deployment still serves the OLD script (no doGet), so Settings > Test Connection shows red.
  `?ping=1` returns "Script function not found: doGet".
- Fix: deploy `apps-script/Code.gs` as a new version of the EXISTING deployment via clasp:
  1. One-time, by Ricky: enable "Google Apps Script API" at https://script.google.com/home/usersettings
  2. `npm i -g @google/clasp` then `clasp login` (Ricky approves in browser as rickyjessie.lee@gmail.com)
  3. Get the script ID: sheet > Extensions > Apps Script > Project Settings > Script ID
     (or `clasp clone <scriptId> --rootDir apps-script`)
  4. `clasp push` from apps-script/, then `clasp deployments` to find the deployment ID that matches the URL above,
     then `clasp deploy -i <deploymentId> -d "doGet ping"` (same URL, new version)
  5. Verify: GET `<exec URL>?ping=1` returns `{"status":"ok"}`

## Other open items
- Sheet cleanup: Damietta rows (20239-20249 drag-fill error, no dates), ~200 email-only rows, duplicates
  (Sean Kumbhani, kyle.lamunyon), test entries (Ricky/Jessie, "Regina Phalange"), typos (gmai.com, "Dover Canyon",
  "Guanajuanto"), inconsistent property names. Confirm with Ricky before deleting anything.
