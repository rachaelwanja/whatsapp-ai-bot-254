import os
import requests
import base64
from datetime import datetime

# =========================================
# MPESA CONFIG
# =========================================

CONSUMER_KEY = os.getenv(
    "MPESA_CONSUMER_KEY"
)

CONSUMER_SECRET = os.getenv(
    "MPESA_CONSUMER_SECRET"
)

SHORTCODE = os.getenv(
    "MPESA_SHORTCODE"
)

PASSKEY = os.getenv(
    "MPESA_PASSKEY"
)

CALLBACK_URL = os.getenv(
    "CALLBACK_URL"
)

# =========================================
# MPESA
# =========================================

def get_access_token():

    url = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"

    response = requests.get(
        url,
        auth=(
            CONSUMER_KEY,
            CONSUMER_SECRET
        )
    )

    print("STATUS:", response.status_code)
    print("RESPONSE:", response.text)

    if response.status_code != 200:
        return None

    try:
        data = response.json()
        return data.get("access_token")
    except Exception as e:
        print("JSON ERROR:", e)
        print("RAW RESPONSE:", response.text)
        return None


def generate_password():

    timestamp = datetime.now().strftime(
        "%Y%m%d%H%M%S"
    )

    password = base64.b64encode(
        (
            SHORTCODE +
            PASSKEY +
            timestamp
        ).encode()
    ).decode()

    return password, timestamp


def stk_push(phone, amount):

    access_token = get_access_token()

    password, timestamp = generate_password()

    url = "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    payload = {
        "BusinessShortCode": SHORTCODE,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": amount,
        "PartyA": phone,
        "PartyB": SHORTCODE,
        "PhoneNumber": phone,
        "CallBackURL": CALLBACK_URL,
        "AccountReference": "FlowAI",
        "TransactionDesc": "Payment"
    }

    response = requests.post(
        url,
        json=payload,
        headers=headers
    )

    print("STK STATUS:", response.status_code)
    print("STK RESPONSE:", response.text)

    return response.json()


# =========================================
# OPENROUTER AI
# =========================================

def ask_ai(messages):

    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
            "Content-Type": "application/json"
        },
        json={
            "model": "openai/gpt-4o-mini",
            "messages": messages
        }
    )

    print(response.text)

    data = response.json()

    return data["choices"][0]["message"]["content"]
