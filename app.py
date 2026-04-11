from flask import Flask, request
import requests
import base64
import datetime
import os
from twilio.twiml.messaging_response import MessagingResponse

app = Flask(__name__)

# ==============================
# LOAD ENV VARIABLES
# ==============================
CONSUMER_KEY = os.getenv("MPESA_CONSUMER_KEY")
CONSUMER_SECRET = os.getenv("MPESA_CONSUMER_SECRET")
SHORTCODE = os.getenv("MPESA_SHORTCODE")
PASSKEY = os.getenv("MPESA_PASSKEY")
CALLBACK_URL = os.getenv("CALLBACK_URL")

# ==============================
# GET ACCESS TOKEN
# ==============================
def get_access_token():
    url = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
    response = requests.get(url, auth=(CONSUMER_KEY, CONSUMER_SECRET))
    return response.json().get("access_token")

# ==============================
# STK PUSH FUNCTION
# ==============================
def stk_push(phone, amount):
    access_token = get_access_token()
    url = "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest"

    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    password = base64.b64encode((SHORTCODE + PASSKEY + timestamp).encode()).decode()

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    payload = {
        "BusinessShortCode": SHORTCODE,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": 1,  # change amount if needed
        "PartyA": phone,
        "PartyB": SHORTCODE,
        "PhoneNumber": phone,
        "CallBackURL": CALLBACK_URL,
        "AccountReference": "FlowAI",
        "TransactionDesc": "Payment"
    }

    response = requests.post(url, json=payload, headers=headers)
    return response.json()

# ==============================
# WHATSAPP WEBHOOK
# ==============================
@app.route("/whatsapp", methods=["POST"])
def whatsapp():
    incoming_msg = request.values.get("Body", "").lower()
    phone = request.values.get("From", "").replace("whatsapp:", "")

    resp = MessagingResponse()
    msg = resp.message()

    if "buy" in incoming_msg:
        stk_push(phone, 1)
        msg.body("💳 Payment request sent! Check your phone 📲")
    else:
        msg.body("👋 Welcome! Type *buy* to make payment.")

    return str(resp)

# ==============================
# CALLBACK (MPESA RESPONSE)
# ==============================
@app.route("/callback", methods=["POST"])
def callback():
    data = request.json
    print("MPESA CALLBACK:", data)
    return {"ResultCode": 0, "ResultDesc": "Accepted"}

# ==============================
# ROOT
# ==============================
@app.route("/")
def home():
    return "Bot is running 🚀"

# ==============================
# RUN
# ==============================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
