import os
import re
import time
import requests
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv

# ----- 1.  Load secrets from .env ----------------------------------------
load_dotenv()  # makes os.getenv read the keys we defined above

RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
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
    """Query a RapidAPI Amazon price endpoint and return the current price in USD.

    NOTE:  This example uses the unofficial “Amazon Price API” on RapidAPI.
           If you pick a different endpoint, adjust the URL / JSON parsing
           below.  Printing the raw JSON once (`print(data)`) helps you see
           the exact field names.
    """
    url = "https://amazon-price1.p.rapidapi.com/price"  # endpoint URL
    params = {"marketplace": "US", "asin": asin}
    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": "amazon-price1.p.rapidapi.com",
    }

    try:
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()  # usually a list with one dict per ASIN

        if not data:
            return None

        # The API returns prices inside nested dicts.  A safe approach is to
        # inspect the first item and look for keys containing "price".
        # Here we assume the structure  data[0]["price"]["current_price"].
        price_info = data[0].get("price", {})
        current_price = price_info.get("current_price")
        return float(current_price) if current_price else None

    except (requests.RequestException, ValueError):
        return None


def send_email(recipient: str, subject: str, body: str) -> None:
    """Send a plain‑text email via SMTP."""

    msg = EmailMessage()
    msg["From"] = SMTP_USER
    msg["To"] = recipient
    msg["Subject"] = subject
    msg.set_content(body)

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()  # Secure the connection (use .SMTP_SSL for port 465)
        server.login(SMTP_USER, SMTP_PASS)
        server.send_message(msg)


# ----- 3.  Core tracker logic -------------------------------------------

def track_price(url: str, drop_percent: float, user_email: str, check_every: int = 3600) -> None:
    """Check price periodically and email when the target drop is reached."""

    asin = extract_asin(url)
    if not asin:
        print("Could not find an ASIN in that URL — please double‑check it.")
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
