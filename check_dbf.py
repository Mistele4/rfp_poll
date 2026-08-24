#!/usr/bin/env python3
"""
AIAA Design/Build/Fly RFP watcher.

Polls the DBF site, looks for a 2026-27 (i.e. "2027") rules/RFP link, and emails
you once when it appears. Keeps a tiny state.json so it only emails one time.

Required env vars:
  SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS   (e.g. smtp.gmail.com / 587 / app password)
  EMAIL_TO                                     (where to send the alert)
Optional:
  EMAIL_FROM   (defaults to SMTP_USER)
  DBF_FORCE_EMAIL=1  (send a test email regardless of detection)
"""
import json, os, re, smtplib, ssl, sys
from datetime import datetime, timezone
from email.message import EmailMessage
from urllib.request import Request, urlopen
from html.parser import HTMLParser

PAGES = [
    "https://aiaa.org/dbf/",
    "https://aiaa.org/dbf/competition-information/rules-faq-qa/",
    "https://aiaa.org/dbf/competition-information/",
]
STATE_FILE = "state.json"
TARGET_YEAR = "2027"          # the 2026-27 season is labeled "2027 DBF Rules"
UA = "Mozilla/5.0 (DBF RFP watcher; personal use)"


class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links, self._href, self._text = [], None, []
    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self._href = dict(attrs).get("href")
            self._text = []
    def handle_data(self, data):
        if self._href is not None:
            self._text.append(data)
    def handle_endtag(self, tag):
        if tag == "a" and self._href is not None:
            self.links.append((self._href, " ".join(self._text).strip()))
            self._href = None


def fetch(url):
    req = Request(url, headers={"User-Agent": UA})
    with urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def find_rfp(html):
    """Return list of (href, text) that look like the 2026-27 rules/RFP."""
    p = LinkParser()
    p.feed(html)
    hits = []
    for href, text in p.links:
        blob = f"{href} {text}".lower()
        year_hit = TARGET_YEAR in blob or "2026-27" in blob or "2026-2027" in blob
        rfp_hit = any(k in blob for k in ("rule", "rfp", "request for proposal"))
        if year_hit and rfp_hit:
            hits.append((href, text))
    # Also catch plain-text mentions like "2026-2027 Rules" with no link yet
    if re.search(r"2026\s*[-–/]\s*(20)?27\s+(dbf\s+)?(rules|rfp)", html, re.I):
        hits.append(("(text mention, no link)", "2026-27 rules mentioned on page"))
    return hits


def load_state():
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except FileNotFoundError:
        return {"notified": False}


def save_state(s):
    with open(STATE_FILE, "w") as f:
        json.dump(s, f, indent=2)


def send_email(subject, body):
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = os.environ.get("EMAIL_FROM", os.environ["SMTP_USER"])
    msg["To"] = os.environ["EMAIL_TO"]
    msg.set_content(body)
    host, port = os.environ["SMTP_HOST"], int(os.environ.get("SMTP_PORT", "587"))
    with smtplib.SMTP(host, port, timeout=30) as s:
        s.starttls(context=ssl.create_default_context())
        s.login(os.environ["SMTP_USER"], os.environ["SMTP_PASS"])
        s.send_message(msg)


def main():
    state = load_state()
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")

    if os.environ.get("DBF_FORCE_EMAIL") == "1":
        send_email("[DBF watcher] test email", f"Watcher is alive as of {now}.")
        print("Test email sent.")
        return

    if state.get("notified"):
        print("Already notified; nothing to do.")
        return

    all_hits, fetched = [], 0
    for url in PAGES:
        try:
            hits = find_rfp(fetch(url))
            fetched += 1
        except Exception as e:  # keep going if one page fails
            print(f"WARN {url}: {e}", file=sys.stderr)
            continue
        for h in hits:
            all_hits.append((url, *h))
        print(f"{url}: {len(hits)} hit(s)")

    if fetched == 0:
        print("ERROR: could not fetch any DBF page", file=sys.stderr)
        sys.exit(1)   # makes the Actions run show red so you notice

    state["last_checked"] = now
    if all_hits:
        lines = [f"- {text or '(no text)'}\n  {href}\n  found on {page}" for page, href, text in all_hits]
        body = (f"The 2026-27 AIAA DBF rules/RFP looks like it's up (checked {now}).\n\n"
                + "\n".join(lines)
                + "\n\nMain page: https://aiaa.org/dbf/\n")
        send_email("AIAA DBF 2026-27 RFP has been posted!", body)
        state.update(notified=True, notified_at=now, hits=all_hits)
        print("ALERT sent.")
    else:
        print("No 2026-27 RFP yet.")
    save_state(state)


if __name__ == "__main__":
    main()
