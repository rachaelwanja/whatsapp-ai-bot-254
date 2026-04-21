from flask import Flask, request, jsonify
import requests
import base64
from datetime import datetime

app = Flask(__name__)

# ===============================
# 🔐 SAFARICOM CREDENTIALS (AI flow app)
# ===============================
CONSUMER_KEY = "YOUR_CONSUMER_KEY"
CONSUMER_SECRET = "YOUR_CONSUMER_SECRET"

SHORTCODE = "174379"
PASSKEY = "bfb279f9aa9bdbc...FULL_PASSKEY_HERE..."

# 🌐 Your live callback URL
CALLBACK_URL = "https://whatsapp-ai-bot-254-1.onrender.com/callback"


# ===============================
# 1. GET ACCESS TOKEN
# ===============================
def get_access_token():
    url = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"

    response = requests.get(url, auth=(CONSUMER_KEY, CONSUMER_SECRET))
    
    print("TOKEN RESPONSE:", response.text)

    return response.json().get("access_token")


# ===============================
# 2. GENERATE PASSWORD
# ===============================
def generate_password():
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

    data = SHORTCODE + PASSKEY + timestamp
    password = base64.b64encode(data.encode()).decode()

    return password, timestamp


# ===============================
# 3. STK PUSH FUNCTION
# ===============================
def stk_push(phone):
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
        "Amount": 1,
        "PartyA": phone,
        "PartyB": SHORTCODE,
        "PhoneNumber": phone,
        "CallBackURL": CALLBACK_URL,
        "AccountReference": "FlowAI",
        "TransactionDesc": "Payment"
    }

    print("STK REQUEST:", payload)

    response = requests.post(url, json=payload, headers=headers)

    print("MPESA RESPONSE:", response.text)

    return response.json()


# ===============================
# 4. WHATSAPP WEBHOOK (FIXED)
# ===============================
@app.route("/whatsapp", methods=["POST"])
def whatsapp():
    incoming_msg = request.form.get("Body")
    sender = request.form.get("From")

    print("WHATSAPP MESSAGE:", incoming_msg)
    print("FROM:", sender)

    # Extract phone (Twilio format: whatsapp:+2547...)
    if sender:
        phone = sender.replace("whatsapp:", "").replace("+", "")
    else:
        phone = "254708374149"  # fallback

    # 🚀 Trigger STK
    response = stk_push(phone)

    return "STK Sent", 200


# ===============================
# 5. MANUAL STK (FOR TESTING)
# ===============================
@app.route("/stk", methods=["POST"])
def stk():
    data = request.get_json()
    phone = data.get("phone", "254708374149")

    response = stk_push(phone)

    return jsonify(response)


# ===============================
# 6. CALLBACK (VERY IMPORTANT)
# ===============================
@app.route("/callback", methods=["POST"])
def callback():
    data = request.json

    print("CALLBACK RECEIVED:", data)

    return jsonify({"status": "received"})


# ===============================
# 7. HEALTH CHECK (IMPORTANT FOR RENDER)
# ===============================
@app.route("/", methods=["GET"])
def home():
    return "Backend is running 🚀"


# ===============================
# RUN
# ===============================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
