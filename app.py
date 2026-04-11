from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import requests
import base64
import datetime
import os

app = Flask(__name__)

# =========================
# ENV VARIABLES
# =========================
MPESA_CONSUMER_KEY = os.getenv("MPESA_CONSUMER_KEY")
MPESA_CONSUMER_SECRET = os.getenv("MPESA_CONSUMER_SECRET")
MPESA_PASSKEY = os.getenv("MPESA_PASSKEY")
MPESA_SHORTCODE = os.getenv("MPESA_SHORTCODE")
CALLBACK_URL = os.getenv("CALLBACK_URL")

# =========================
# GET MPESA ACCESS TOKEN
# =========================
def get_access_token():
    try:
        url = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
        response = requests.get(url, auth=(MPESA_CONSUMER_KEY, MPESA_CONSUMER_SECRET))
        data = response.json()

        print("ACCESS TOKEN RESPONSE:", data)

        return data.get("access_token")
    except Exception as e:
        print("ACCESS TOKEN ERROR:", e)
        return None


# =========================
# SEND STK PUSH
# =========================
def send_mpesa_payment(phone):
    try:
        access_token = get_access_token()

        if not access_token:
            print("❌ No access token")
            return

        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")

        password = base64.b64encode(
            (MPESA_SHORTCODE + MPESA_PASSKEY + timestamp).encode()
        ).decode()

        url = "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest"

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        payload = {
            "BusinessShortCode": MPESA_SHORTCODE,
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": 1,
            "PartyA": phone,
            "PartyB": MPESA_SHORTCODE,
            "PhoneNumber": phone,
            "CallBackURL": CALLBACK_URL,
            "AccountReference": "FlowAI",
            "TransactionDesc": "Payment"
        }

        print("📤 SENDING TO MPESA:", payload)

        response = requests.post(url, json=payload, headers=headers)

        print("📩 MPESA RESPONSE:", response.text)

    except Exception as e:
        print("❌ MPESA ERROR:", e)


# =========================
# WHATSAPP WEBHOOK
# =========================
@app.route("/whatsapp", methods=["POST"])
def whatsapp():
    incoming_msg = request.values.get('Body', '').strip().lower()
    from_number = request.values.get('From', '').replace("whatsapp:", "")

    resp = MessagingResponse()
    msg = resp.message()

    if "buy" in incoming_msg:
        # ✅ FAST RESPONSE (fix delay)
        msg.body("📲 Processing payment... check your phone.")

        # ✅ RUN PAYMENT AFTER RESPONSE (non-blocking style)
        send_mpesa_payment(from_number)

    else:
        msg.body("👋 Welcome! Type *buy* to make payment.")

    return str(resp)


# =========================
# MPESA CALLBACK
# =========================
@app.route("/callback", methods=["POST"])
def callback():
    try:
        data = request.json
        print("📥 MPESA CALLBACK:", data)
    except Exception as e:
        print("❌ CALLBACK ERROR:", e)

    return "OK", 200


# =========================
# HOME
# =========================
@app.route("/")
def home():
    return "WhatsApp Bot Running ✅"


# =========================
# RUN
# =========================
if __name__ == "__main__":
    app.run(debug=True)
