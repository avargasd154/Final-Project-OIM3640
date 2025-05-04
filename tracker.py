import os
import re
import time
import requests
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv

# ----- 1.  Load API key from .env ----------------------------------------

load_dotenv()

RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
if not RAPIDAPI_KEY:
    raise ValueError("RAPIDAPI_KEY not found.")
SMTP_SERVER  = os.getenv("SMTP_SERVER")
SMTP_PORT    = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER    = os.getenv("SMTP_USER")
SMTP_PASS    = os.getenv("SMTP_PASS")

# ----- 2.  Helper functions ---------------------------------------------

def extract_asin(url: str) -> str | None:
    """Pull the 10‑character ASIN from almost any Amazon product URL."""
    m = re.search(r"/(?:dp|gp/product)/([A-Z0-9]{10})", url)
    if not m:
        # fallback pattern – works for many other URL shapes
        m = re.search(r"/([A-Z0-9]{10})(?:[/?]|$)", url)
    return m.group(1) if m else None


def get_current_price(asin: str) -> float | None:
    """Query a RapidAPI Amazon price endpoint and return the current price in USD."""
    url = "https://real-time-amazon-data.p.rapidapi.com/product-offers"
    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": "real-time-amazon-data.p.rapidapi.com",
    }
    params = {"asin": asin, "country": "US", "page": "1", "limit": "1"}

    try:
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        # Parse the JSON returned by *Real‑Time Amazon Data API*
        offers = data.get("data", {}).get("product_offers", [])
        if not offers:
            return None  # empty list → no offer/ASIN mismatch

        price_value = offers[0].get("price", {}).get("value")
        return float(price_value) if price_value is not None else None

    except (requests.RequestException, ValueError):
        return None


def send_email(recipient: str, subject: str, body: str) -> None:
    """Send a plain text email via SMTP."""

    msg = EmailMessage()
    msg["From"] = SMTP_USER
    msg["To"] = recipient
    msg["Subject"] = subject
    msg.set_content(body)

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.send_message(msg)


# ----- 3.  Core tracker logic -------------------------------------------

def track_price(url: str, drop_percent: float, user_email: str, check_every: int = 3600) -> None:
    """Check price periodically and email when the target drop is reached."""

    asin = extract_asin(url)
    if not asin:
        print("Could not find an ASIN in that URL — please double check it.")
        return

    print("Fetching current price…")
    start_price = get_current_price(asin)
    if start_price is None:
        print("Sorry, couldn’t retrieve the price (maybe try again later?).")
        return

    target_price = start_price * (1 - drop_percent / 100)
    print(f"Current price:  ${start_price:.2f}")
    print(f"Alert below:    ${target_price:.2f}  (‑{drop_percent}%)")
    print("\nTracking…  (press Ctrl+C to stop)")

    try:
        while True:
            time.sleep(check_every)
            latest_price = get_current_price(asin)
            if latest_price is None:
                continue  # skip this round if the API failed

            print(f"Checked: ${latest_price:.2f}")
            if latest_price <= target_price:
                body = (
                    f"Great news! The Amazon item you’re watching is now ${latest_price:.2f}.\n"
                    f"Original price: ${start_price:.2f}\n"
                    f"Link: {url}\n"
                )
                send_email(user_email, "Amazon Price Drop Alert", body)
                print("Price drop found — email sent!  Tracker stopped.")
                break
    except KeyboardInterrupt:
        print("\nTracker stopped by user.")


# ----- 4.  Command‑line interface ---------------------------------------
if __name__ == "__main__":
    product_url   = input("Amazon product URL: ").strip()
    percent_drop  = float(input("Notify me when price drops by (%): ").strip())
    email_address = input("Your e‑mail address: ").strip()

    track_price(product_url, percent_drop, email_address)