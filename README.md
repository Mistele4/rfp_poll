# AIAA DBF 2026-27 RFP Watcher

Checks aiaa.org/dbf every 30 minutes via GitHub Actions and emails you **once**
when a 2027 ("2026-27") rules/RFP link appears.

## Setup (≈5 minutes)

1. Create a new GitHub repo (private is fine) and push these files.
2. Get an SMTP login. Easiest with Gmail:
   - Turn on 2-Step Verification on your Google account.
   - Go to https://myaccount.google.com/apppasswords and create an app password.
3. In the repo: **Settings → Secrets and variables → Actions → New repository secret**, add:

   | Secret      | Value                          |
   |-------------|--------------------------------|
   | `SMTP_HOST` | `smtp.gmail.com`               |
   | `SMTP_PORT` | `587`                          |
   | `SMTP_USER` | your Gmail address             |
   | `SMTP_PASS` | the 16-char app password       |
   | `EMAIL_TO`  | address to alert (can be same) |

4. **Actions** tab → enable workflows if prompted → open "Check AIAA DBF for 2026-27 RFP"
   → **Run workflow** with *test_email* checked. You should get a test email.
5. Done. It now runs on its own. When the RFP appears you get one email and
   `state.json` records it so you aren't spammed.

## Notes
- GitHub may skip scheduled runs on repos with no activity for ~60 days; a manual
  "Run workflow" resets that.
- To re-arm after a false alarm, delete `state.json` (or set `"notified": false`).
- Run locally instead: `export SMTP_HOST=... EMAIL_TO=...; python check_dbf.py`
  and put it in cron.
