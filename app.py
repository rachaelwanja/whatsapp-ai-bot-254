from flask import Flask, request, jsonify
import requests
import base64
from datetime import datetime

app = Flask(__name__)

# 🔐 YOUR APP CREDENTIALS (from AI flow app)
CONSUMER_KEY = "PUT_YOUR_KEY_HERE"
CONSUMER_SECRET = "PUT_YOUR_SECRET_HERE"

# 🏦 Sandbox details
SHORTCODE = "174379"
PASSKEY = "bfb279f9aa9bdbc...FULL_PASSKEY_HERE..."

# 🌐 Callback URL
CALLBACK_URL = "https://whatsapp-ai-bot-254-1.onrender.com/callback"


# ===============================
# ACCESS TOKEN
# ===============================
def get_access_token():
    url = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"

    response = requests.get(url, auth=(CONSUMER_KEY, CONSUMER_SECRET))
    
    print("TOKEN RESPONSE:", response.text)  # 👈 debug

    return response.json().get("access_token")


# ===============================
# PASSWORD GENERATION
# ===============================
def generate_password():
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

    data = SHORTCODE + PASSKEY + timestamp
    password = base64.b64encode(data.encode()).decode()

    return password, timestamp


# ===============================
# STK PUSH ROUTE
# ===============================
@app.route("/stk", methods=["POST"])
def stk_push():
    phone = request.json.get("phone")

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

    print("REQUEST:", payload)  # 👈 debug

    response = requests.post(url, json=payload, headers=headers)

    print("MPESA RESPONSE:", response.text)  # 👈 debug

    return jsonify(response.json())


# ===============================
# CALLBACK (VERY IMPORTANT)
# ===============================
@app.route("/callback", methods=["POST"])
def callback():
    data = request.json
    print("CALLBACK RECEIVED:", data)
    return jsonify({"status": "ok"})


# ===============================
# RUN
# ===============================
if __name__ == "__main__":
    app.run(debug=True)
