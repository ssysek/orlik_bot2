import os
import requests
import logging
from dotenv import load_dotenv, find_dotenv
import sys

# Load .env if present for local development; CI provides env via runner
load_dotenv(find_dotenv(), override=False)

# Configure logging to show INFO by default in local runs; override via LOG_LEVEL
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s %(levelname)s %(message)s",
    stream=sys.stdout,
)

# Config via env to avoid committing secrets and allow overrides in CI
# Default court id remains 229 unless COURT_ID is provided
COURT_ID = int(os.getenv("COURT_ID", "229"))

FROM_DATE = "2025-08-22"
TO_DATE = "2025-09-30"

# Timezone offset in minutes for the Ballsquad API; default -120 (UTC+2)
TIMEZONE_OFFSET = -120

# When true, send a Discord notification even if no slots were found.
# Useful for daily heartbeat runs to confirm the bot works end-to-end.
ALWAYS_NOTIFY_ON_SUCCESS = os.getenv("ALWAYS_NOTIFY_ON_SUCCESS", "false").lower() in ("1", "true", "yes", "y")

def notify_discord(msg: str):
    """Send a message to Discord channel via webhook.
    If webhook isn't configured, we skip to avoid leaking errors and breaking CI.
    """
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        logging.info("DISCORD_WEBHOOK_URL not set; skipping Discord notify")
        return
    payload = {"content": msg}
    r = requests.post(webhook_url, json=payload, timeout=15)
    r.raise_for_status()

def get_token():
    url = "https://api.ballsquad.pl/api/authenticate/discover"
    headers = {
        "accept": "*/*",
        "accept-language": "en-GB,en;q=0.9",
        "timezoneoffset": str(TIMEZONE_OFFSET),
        "origin": "https://app.ballsquad.pl",
        "referer": "https://app.ballsquad.pl/",
        "user-agent": "Mozilla/5.0",
    }
    r = requests.post(url, headers=headers)
    r.raise_for_status()
    data = r.json()
    return data.get("access_token") or data.get("id_token") or data.get("token")

def get_availabilities(token: str):
    url = f"https://api.ballsquad.pl/api/availabilities/court/{COURT_ID}?fromDate={FROM_DATE}&toDate={TO_DATE}"
    headers = {
        "accept": "*/*",
        "authorization": f"Bearer {token}",
        "timezoneoffset": str(TIMEZONE_OFFSET),
        "origin": "https://app.ballsquad.pl",
        "referer": "https://app.ballsquad.pl/",
        "user-agent": "Mozilla/5.0",
    }
    r = requests.get(url, headers=headers)
    r.raise_for_status()
    return r.json()


try:
    logging.info(f"Getting token for court {COURT_ID}")
    token = get_token()
    logging.info(f"Getting availabilities for court {COURT_ID}")
    slots = get_availabilities(token)
    logging.info(f"Found {len(slots)} slots")
    if slots:
        logging.info(f"Found {len(slots)} slots")
        notify_discord(f"SLOTY na {COURT_ID}: {slots} @here @channel @everyone")
    else:
        logging.info("No slots found")
        if ALWAYS_NOTIFY_ON_SUCCESS:
            notify_discord(
                f"Heartbeat ✅: No slots found for {COURT_ID} in range {FROM_DATE}→{TO_DATE}"
            )
        

except Exception as e:
    logging.error(f"ERROR: {e}")
    try:
        notify_discord(f"ERROR: {e}")
    except Exception:
        logging.error(f"ERROR sending error message: {e}")
