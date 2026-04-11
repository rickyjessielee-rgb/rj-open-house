#!/usr/bin/env python3
"""
RJ Rental Manager — One-Time Setup Script
==========================================
Run this script ONCE to create your AI rental agent in the cloud.
After this, use "python run.py" to check Gmail and process new inquiries.

════════════════════════════════════════════
COMPLETE THESE STEPS BEFORE RUNNING THIS SCRIPT:
════════════════════════════════════════════

STEP 1 — Get your Anthropic API key:
  • Go to: https://console.anthropic.com/
  • Sign up or log in → click "API Keys" → click "Create Key"
  • Copy the key (starts with "sk-ant-...")

STEP 2 — Create a Gmail App Password:
  • Go to: https://myaccount.google.com/
  • Click "Security" on the left sidebar
  • Under "How you sign in to Google" → click "2-Step Verification"
    (You must have 2-Step Verification ON — enable it if needed)
  • Scroll down to the bottom → click "App passwords"
  • Under "Select app" choose "Mail"
  • Under "Select device" choose "Windows Computer" (or any option)
  • Click "Generate" — Google gives you a 16-character password
  • Copy that password (e.g.  abcd efgh ijkl mnop)

STEP 3 — Enable IMAP in Gmail:
  • Open Gmail → click the gear icon (top right) → "See all settings"
  • Click the "Forwarding and POP/IMAP" tab
  • Under "IMAP access" → select "Enable IMAP"
  • Scroll down → click "Save Changes"

STEP 4 — Create your .env file:
  • In this folder, copy ".env.example" and rename it to ".env"
  • Open ".env" and fill in:
      ANTHROPIC_API_KEY=sk-ant-...your key here...
      GMAIL_APP_PASSWORD=abcdefghijklmnop  (no spaces)

STEP 5 — Install Python packages (run this in Terminal / Command Prompt):
  pip install anthropic python-dotenv

STEP 6 — Run this script:
  python setup.py
════════════════════════════════════════════
"""

import anthropic
import json
import os
import sys
from dotenv import load_dotenv

load_dotenv()

# ─── Property & Business Info ──────────────────────────────────────────────────
PROPERTY_ADDRESS = "12977 Radiance Ct, Eastvale, CA"

AGENT_SYSTEM_PROMPT = f"""You are the rental manager assistant for Ricky Lee at RJ Realty (DRE 01932116).

Your job: Process rental inquiry emails for the property at {PROPERTY_ADDRESS}.

PROPERTY INFORMATION:
Use web_search to look up "{PROPERTY_ADDRESS} rental" to get the current listing details,
especially the monthly asking rent. You need the rent to check the income qualification.

══════════════════════════════════════════════
STRICT DISQUALIFICATION RULES
══════════════════════════════════════════════
Apply these rules silently. NEVER tell the applicant they were disqualified.
NEVER give a reason. Simply call the ignore_applicant tool and stop all communication.

1. Applicant mentions ANY pets, emotional support animals, or service animals
   → Call ignore_applicant immediately. Send NO reply whatsoever.

2. Applicant states a credit score below 680
   → Call ignore_applicant immediately. Send NO reply whatsoever.

3. Applicant's monthly combined income is less than 2x the monthly asking rent
   → Call ignore_applicant immediately. Send NO reply whatsoever.
   (Use web_search to find the asking rent if you don't already know it.)

══════════════════════════════════════════════
FOR NEW INQUIRIES (applicant has NOT yet answered the qualification questions)
══════════════════════════════════════════════
Call the send_reply tool with:
  - to_email: the applicant's email address (extract it from the Zillow forwarded email)
  - reply_text: use EXACTLY this message, word for word:

"Thank you for your interest. The house is available.
• How many people will be in?
• What's your monthly combined income?
• How's your credit score?
• Any pets, emotional support, or service animals?
• When do you plan to move in?

Ricky Lee, RJ Realty
DRE 01932116"

══════════════════════════════════════════════
FOR FOLLOW-UP REPLIES (applicant answered the qualification questions)
══════════════════════════════════════════════
Step 1 — Check for disqualifiers (in this order):
  • Pets / ESA / service animals mentioned → call ignore_applicant, stop
  • Credit score < 680 → call ignore_applicant, stop
  • Monthly income < 2x monthly rent → call ignore_applicant, stop

Step 2 — If the applicant PASSES all three checks (FULLY QUALIFIED):
  a. Call notify_landlord with the applicant's full details so Ricky can be asked
     for his showing availability.
  b. Call send_reply to let the applicant know they qualify and a showing will be arranged:

     "Great news! You meet our rental requirements for {PROPERTY_ADDRESS}.
We will be in touch shortly to schedule a property showing.

Ricky Lee, RJ Realty
DRE 01932116"

IMPORTANT: The emails you receive are forwarded by Zillow.
Always extract the actual applicant's email address from the email body or headers.
Zillow typically includes the renter's contact information in the body of the email.
"""
# ───────────────────────────────────────────────────────────────────────────────


def check_env():
    """Verify the .env file is properly configured."""
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not key or "paste_your" in key:
        print("❌  ANTHROPIC_API_KEY is missing or not set in your .env file.")
        print("    Please add it following Step 4 in the instructions above.")
        sys.exit(1)
    return key


def main():
    api_key = check_env()
    client = anthropic.Anthropic(api_key=api_key)

    print("\n🏠  RJ Rental Manager — One-Time Setup")
    print("=" * 50)

    # ── Step 1: Create the cloud environment ──────────────────────────────────
    print("\n[1/2] Creating cloud environment...")
    try:
        environment = client.beta.environments.create(
            name="rj-rental-manager-env",
            config={
                "type": "cloud",
                # Unrestricted so the agent can search the web for property info
                "networking": {"type": "unrestricted"},
            },
        )
        print(f"      ✅  Environment ready: {environment.id}")
    except anthropic.BadRequestError as exc:
        if "already exists" in str(exc).lower():
            print("      ⚠️   An environment named 'rj-rental-manager-env' already exists.")
            print("          Delete agent_config.json and re-run, or contact support.")
            sys.exit(1)
        raise

    # ── Step 2: Create the rental manager agent ───────────────────────────────
    print("\n[2/2] Creating the rental manager agent...")
    agent = client.beta.agents.create(
        name="RJ Rental Manager",
        model="claude-haiku-4-5",
        system=AGENT_SYSTEM_PROMPT,
        tools=[
            # Built-in toolset: bash, read, write, web_search, web_fetch, and more
            {
                "type": "agent_toolset_20260401",
                "default_config": {"enabled": True},
            },
            # Custom tool: your run.py script actually sends the email
            {
                "type": "custom",
                "name": "send_reply",
                "description": (
                    "Send an email reply to a rental inquiry applicant. "
                    "Use this when an applicant passes the initial screening "
                    "and you want to send them a message."
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "to_email": {
                            "type": "string",
                            "description": "The applicant's email address to send the reply to",
                        },
                        "reply_text": {
                            "type": "string",
                            "description": "The full text of the reply email",
                        },
                    },
                    "required": ["to_email", "reply_text"],
                },
            },
            # Custom tool: silently disqualify an applicant (no email is sent)
            {
                "type": "custom",
                "name": "ignore_applicant",
                "description": (
                    "Disqualify this applicant and stop all communication. "
                    "Use when applicant mentions pets, emotional support animals, "
                    "service animals, has a credit score below 680, or has a monthly "
                    "income below 2x the monthly rent. "
                    "This does NOT send any email — the applicant is simply ignored."
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "applicant_email": {
                            "type": "string",
                            "description": "The applicant's email address",
                        },
                        "reason": {
                            "type": "string",
                            "description": (
                                "Internal reason — one of: 'pets', "
                                "'low_credit_score', or 'insufficient_income'"
                            ),
                        },
                    },
                    "required": ["applicant_email", "reason"],
                },
            },
            # Custom tool: alert Ricky that a renter has fully qualified and ask for availability
            {
                "type": "custom",
                "name": "notify_landlord",
                "description": (
                    "Send Ricky Lee an email notifying him that a renter has passed ALL "
                    "qualifications (no pets, credit score ≥ 680, income ≥ 2x rent). "
                    "Include the renter's full details. This asks Ricky for his next "
                    "available dates and times to schedule a property showing."
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "applicant_name": {
                            "type": "string",
                            "description": "Applicant's full name (if available)",
                        },
                        "applicant_email": {
                            "type": "string",
                            "description": "Applicant's email address",
                        },
                        "applicant_phone": {
                            "type": "string",
                            "description": "Applicant's phone number (if available)",
                        },
                        "num_occupants": {
                            "type": "string",
                            "description": "Number of people who will be living in the property",
                        },
                        "monthly_income": {
                            "type": "string",
                            "description": "Applicant's stated monthly combined income",
                        },
                        "credit_score": {
                            "type": "string",
                            "description": "Applicant's stated credit score",
                        },
                        "move_in_date": {
                            "type": "string",
                            "description": "Applicant's desired move-in date",
                        },
                    },
                    "required": ["applicant_email", "monthly_income", "credit_score"],
                },
            },
        ],
    )
    print(f"      ✅  Agent ready: {agent.id}")

    # ── Save config for run.py ─────────────────────────────────────────────────
    config = {
        "environment_id": environment.id,
        "agent_id": agent.id,
        "agent_version": agent.version,
    }
    with open("agent_config.json", "w") as f:
        json.dump(config, f, indent=2)

    print("\n" + "=" * 50)
    print("✅  Setup complete!")
    print(f"    Environment : {environment.id}")
    print(f"    Agent       : {agent.id}")
    print(f"    Config saved: agent_config.json")
    print("\n👉  Next step:")
    print("    Run  'python run.py'  to check Gmail and process new inquiries.")
    print("    Tip: Set a scheduled task to run it every 15 minutes automatically.")


if __name__ == "__main__":
    main()
