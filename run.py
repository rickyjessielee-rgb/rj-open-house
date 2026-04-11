#!/usr/bin/env python3
"""
RJ Rental Manager — Email Processing Script
============================================
Run this script every 15 minutes to check Gmail for new Zillow inquiries
and let the AI agent handle them automatically.

HOW TO RUN ONCE (manually):
  python run.py

HOW TO RUN AUTOMATICALLY EVERY 15 MINUTES:

  On Mac/Linux — open Terminal and type:
    crontab -e
    Add this line (replace /path/to/rj-open-house with your actual folder path):
    */15 * * * * cd /path/to/rj-open-house && python run.py >> rental_log.txt 2>&1

  On Windows — open Task Scheduler:
    • Create a Basic Task → set trigger to "Daily", repeat every 15 minutes
    • Action: Start a program → browse to python.exe
    • Add arguments: run.py
    • Start in: your rj-open-house folder path

WHAT THIS SCRIPT DOES:
  1. Connects to your Gmail and looks for unread emails from Zillow
  2. For each new inquiry, asks the AI agent how to handle it
  3. The agent either:
       a) Sends the qualification questions (new inquiry)
       b) Continues a qualified conversation (follow-up)
       c) Silently ignores the email (disqualified applicant)
  4. Saves a record of what was done in processed_emails.json
"""

import anthropic
import imaplib
import smtplib
import email
import json
import os
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.header import decode_header
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# ─── Configuration ─────────────────────────────────────────────────────────────
GMAIL_ADDRESS     = "Rickyjessie.lee@gmail.com"
GMAIL_APP_PASS    = os.environ.get("GMAIL_APP_PASSWORD", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

AGENT_CONFIG_FILE    = "agent_config.json"
PROCESSED_FILE       = "processed_emails.json"
DISQUALIFIED_FILE    = "disqualified_emails.json"
# ───────────────────────────────────────────────────────────────────────────────


# ─── Helper: JSON file utilities ───────────────────────────────────────────────

def load_json(path: str) -> dict:
    """Load a JSON file; return an empty dict if the file doesn't exist yet."""
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {}


def save_json(path: str, data: dict):
    """Save data to a JSON file."""
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


# ─── Gmail: Read emails ─────────────────────────────────────────────────────────

def decode_header_value(value: str) -> str:
    """Decode encoded email header strings into plain text."""
    parts = decode_header(value or "")
    result = []
    for chunk, encoding in parts:
        if isinstance(chunk, bytes):
            result.append(chunk.decode(encoding or "utf-8", errors="ignore"))
        else:
            result.append(chunk)
    return "".join(result)


def fetch_zillow_emails() -> list[dict]:
    """
    Connect to Gmail via IMAP, fetch all unread emails from Zillow,
    mark them as read, and return their content as a list.
    """
    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    mail.login(GMAIL_ADDRESS, GMAIL_APP_PASS)
    mail.select("inbox")

    # Look for unread emails that came from a zillow address
    _, message_ids = mail.search(None, '(UNSEEN FROM "zillow")')

    emails = []
    for msg_id in message_ids[0].split():
        if not msg_id:
            continue

        # Fetch the full email
        _, data = mail.fetch(msg_id, "(RFC822)")
        raw_bytes = data[0][1]
        msg = email.message_from_bytes(raw_bytes)

        # Pull out the key headers
        subject  = decode_header_value(msg.get("Subject", "(no subject)"))
        sender   = decode_header_value(msg.get("From", ""))
        reply_to = msg.get("Reply-To") or msg.get("From", "")
        date     = msg.get("Date", "")

        # Extract the plain-text body
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    payload = part.get_payload(decode=True)
                    if payload:
                        body = payload.decode("utf-8", errors="ignore")
                        break
        else:
            payload = msg.get_payload(decode=True)
            if payload:
                body = payload.decode("utf-8", errors="ignore")

        emails.append({
            "id":       msg_id.decode(),
            "subject":  subject,
            "sender":   sender,
            "reply_to": reply_to,
            "date":     date,
            "body":     body,
        })

        # Mark the email as read so we don't process it twice
        mail.store(msg_id, "+FLAGS", "\\Seen")

    mail.logout()
    return emails


# ─── Gmail: Send email ──────────────────────────────────────────────────────────

def send_email(to_address: str, original_subject: str, body_text: str):
    """Send an email reply via Gmail's SMTP server."""
    msg = MIMEMultipart()
    msg["From"]    = GMAIL_ADDRESS
    msg["To"]      = to_address
    # Prepend "Re:" if it's not already there
    subject = original_subject if original_subject.startswith("Re:") else f"Re: {original_subject}"
    msg["Subject"] = subject
    msg.attach(MIMEText(body_text, "plain"))

    with smtplib.SMTP("smtp.gmail.com", 587) as smtp:
        smtp.ehlo()
        smtp.starttls()
        smtp.login(GMAIL_ADDRESS, GMAIL_APP_PASS)
        smtp.send_message(msg)

    print(f"    ✉️   Reply sent to: {to_address}")


# ─── Managed Agent session ──────────────────────────────────────────────────────

def run_agent_on_email(em: dict, config: dict) -> tuple:
    """
    Start a Managed Agent session to decide what to do with one email.
    Returns: (reply_text, reply_to_email, was_disqualified)
    """
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    # Build the message we'll send to the agent
    agent_message = f"""New Zillow rental inquiry received:

FROM: {em['sender']}
REPLY-TO: {em['reply_to']}
DATE: {em['date']}
SUBJECT: {em['subject']}

EMAIL BODY:
{em['body']}

---
Instructions:
1. Extract the applicant's actual email address from the content above.
2. Apply the disqualification rules (pets / credit score below 680).
3. If disqualified → call ignore_applicant. Do NOT send any reply.
4. If not disqualified → call send_reply with the qualification questions
   (or continue the conversation if they already answered).
"""

    # Create a fresh session for this email
    session = client.beta.sessions.create(
        agent=config["agent_id"],          # uses the latest version of the agent
        environment_id=config["environment_id"],
        title=f"Inquiry: {em['subject'][:60]}",
    )

    reply_text       = None
    reply_email      = None
    was_disqualified = False
    iteration        = 0

    try:
        # Outer loop: keep going until the agent is fully done
        # (the agent may call tools multiple times before finishing)
        while True:
            iteration += 1

            with client.beta.sessions.stream(session_id=session.id) as stream:
                # Stream-first: send the initial message while the stream is open
                if iteration == 1:
                    client.beta.sessions.events.send(
                        session_id=session.id,
                        events=[{
                            "type": "user.message",
                            "content": [{"type": "text", "text": agent_message}],
                        }],
                    )

                # Collect any custom tool calls the agent makes this round
                tool_calls = []
                for event in stream:
                    if event.type == "agent.custom_tool_use":
                        tool_calls.append(event)
                    elif event.type in ("session.status_idle", "session.status_terminated"):
                        break  # agent is pausing or done

            # No tool calls this round — agent finished its work
            if not tool_calls:
                break

            # Handle each tool the agent called and collect results to send back
            tool_results = []
            for call in tool_calls:

                if call.tool_name == "send_reply":
                    # Agent wants to send a reply — capture the text and recipient
                    reply_text  = call.input.get("reply_text", "")
                    reply_email = call.input.get("to_email", em["reply_to"])
                    print(f"    📝  Agent drafted a reply to: {reply_email}")
                    tool_results.append({
                        "type": "user.custom_tool_result",
                        "custom_tool_use_id": call.id,
                        "content": [{"type": "text", "text": "Reply queued for sending."}],
                    })

                elif call.tool_name == "ignore_applicant":
                    # Agent decided to disqualify — log and stay silent
                    was_disqualified  = True
                    applicant_email   = call.input.get("applicant_email", "")
                    reason            = call.input.get("reason", "unspecified")
                    print(f"    🚫  Disqualified ({reason}): {applicant_email}")

                    # Record this email address so we ignore future messages from them
                    disqualified = load_json(DISQUALIFIED_FILE)
                    if applicant_email:
                        disqualified[applicant_email] = {
                            "reason":    reason,
                            "timestamp": datetime.now().isoformat(),
                        }
                        save_json(DISQUALIFIED_FILE, disqualified)

                    tool_results.append({
                        "type": "user.custom_tool_result",
                        "custom_tool_use_id": call.id,
                        "content": [{"type": "text", "text": "Applicant disqualified and logged."}],
                    })

            # Send the tool results back so the agent can continue
            client.beta.sessions.events.send(
                session_id=session.id,
                events=tool_results,
            )

    finally:
        # Clean up the session when done (brief pause for status to settle)
        try:
            time.sleep(0.5)
            client.beta.sessions.delete(session_id=session.id)
        except Exception:
            pass  # cleanup failure is not critical

    return reply_text, reply_email, was_disqualified


# ─── Main ───────────────────────────────────────────────────────────────────────

def main():
    print(f"\n🏠  RJ Rental Manager — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 55)

    # ── Validate environment ──────────────────────────────────────────────────
    if not ANTHROPIC_API_KEY or "paste_your" in ANTHROPIC_API_KEY:
        print("❌  ANTHROPIC_API_KEY not set. Check your .env file.")
        return
    if not GMAIL_APP_PASS or "paste_your" in GMAIL_APP_PASS:
        print("❌  GMAIL_APP_PASSWORD not set. Check your .env file.")
        return

    config = load_json(AGENT_CONFIG_FILE)
    if not config.get("agent_id"):
        print("❌  agent_config.json not found.")
        print("    Please run 'python setup.py' first.")
        return

    # ── Load records ──────────────────────────────────────────────────────────
    processed    = load_json(PROCESSED_FILE)
    disqualified = load_json(DISQUALIFIED_FILE)

    # ── Fetch new Zillow emails ───────────────────────────────────────────────
    print("📬  Checking Gmail for new Zillow inquiries...")
    try:
        emails = fetch_zillow_emails()
    except imaplib.IMAP4.error as exc:
        print(f"❌  Gmail login failed: {exc}")
        print("    Check that IMAP is enabled and your GMAIL_APP_PASSWORD is correct.")
        return

    if not emails:
        print("✅  No new Zillow inquiries.")
        return

    print(f"📩  Found {len(emails)} new email(s).\n")

    # ── Process each email ────────────────────────────────────────────────────
    for em in emails:
        label = em["subject"][:55]
        print(f"  📧  {label}")

        # Skip if we've already handled this exact email
        if em["id"] in processed:
            print("      ↩️   Already processed — skipping.")
            continue

        # Skip if this sender is already disqualified
        if em["reply_to"] in disqualified:
            print(f"      🚫  Known disqualified applicant — ignoring.")
            processed[em["id"]] = {
                "status": "skipped_disqualified",
                "ts":     datetime.now().isoformat(),
            }
            save_json(PROCESSED_FILE, processed)
            continue

        # Hand the email to the AI agent
        reply_text, reply_email, was_disqualified = run_agent_on_email(em, config)

        # Act on the agent's decision
        if reply_text and reply_email:
            send_email(reply_email, em["subject"], reply_text)
            processed[em["id"]] = {
                "status": "replied",
                "to":     reply_email,
                "ts":     datetime.now().isoformat(),
            }
        elif was_disqualified:
            processed[em["id"]] = {
                "status": "disqualified",
                "ts":     datetime.now().isoformat(),
            }
        else:
            processed[em["id"]] = {
                "status": "no_action",
                "ts":     datetime.now().isoformat(),
            }

        save_json(PROCESSED_FILE, processed)
        print()  # blank line between emails for readability

    print("✅  Done.\n")


if __name__ == "__main__":
    main()
