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
    url = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
    response = requests.get(url, auth=(MPESA_CONSUMER_KEY, MPESA_CONSUMER_SECRET))
    return response.json().get("access_token")


# =========================
# SEND STK PUSH
# =========================
def send_mpesa_payment(phone):
    access_token = get_access_token()

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

    response = requests.post(url, json=payload, headers=headers)

    print("MPESA RESPONSE:", response.text)

    return "💳 Payment request sent! Check your phone."


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
        reply = send_mpesa_payment(from_number)
    else:
        reply = "👋 Welcome! Type *buy* to make payment."

    msg.body(reply)
    return str(resp)


# =========================
# MPESA CALLBACK
# =========================
@app.route("/callback", methods=["POST"])
def callback():
    data = request.json
    print("MPESA CALLBACK:", data)
    return "OK", 200


# =========================
# HOME (TEST)
# =========================
@app.route("/")
def home():
    return "WhatsApp Bot Running ✅"


# =========================
# RUN APP
# =========================
if __name__ == "__main__":
    app.run(debug=True)
