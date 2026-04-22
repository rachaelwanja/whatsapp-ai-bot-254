from flask import Flask, request, jsonify
import requests
import base64
from datetime import datetime

app = Flask(__name__)

# ===============================
# 🔐 CONFIG (PUT YOUR REAL VALUES)
# ===============================
CONSUMER_KEY = "YOUR_CONSUMER_KEY"
CONSUMER_SECRET = "YOUR_CONSUMER_SECRET"

SHORTCODE = "174379"
PASSKEY = "YOUR_FULL_PASSKEY"

CALLBACK_URL = "https://whatsapp-ai-bot-254-1.onrender.com/callback"


# ===============================
# 🔑 GET ACCESS TOKEN (SAFE)
# ===============================
def get_access_token():
    url = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"

    try:
        response = requests.get(url, auth=(CONSUMER_KEY, CONSUMER_SECRET))

        print("TOKEN STATUS:", response.status_code)
        print("TOKEN RAW:", response.text)

        if response.status_code != 200:
            return None

        data = response.json()
        return data.get("access_token")

    except Exception as e:
        print("TOKEN ERROR:", str(e))
        return None


# ===============================
# 🔐 GENERATE PASSWORD
# ===============================
def generate_password():
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    data = SHORTCODE + PASSKEY + timestamp
    password = base64.b64encode(data.encode()).decode()
    return password, timestamp


# ===============================
# 💳 STK PUSH
# ===============================
def stk_push(phone):

    access_token = get_access_token()

    if not access_token:
        print("❌ FAILED TO GET TOKEN")
        return {"error": "Access token failed"}

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

    print("📤 STK REQUEST:", payload)

    try:
        response = requests.post(url, json=payload, headers=headers)

        print("📥 MPESA STATUS:", response.status_code)
        print("📥 MPESA RESPONSE:", response.text)

        try:
            return response.json()
        except:
            return {"error": "Invalid MPESA response", "raw": response.text}

    except Exception as e:
        print("STK ERROR:", str(e))
        return {"error": str(e)}


# ===============================
# 📩 WHATSAPP WEBHOOK (FIXED)
# ===============================
@app.route("/whatsapp", methods=["POST"])
def whatsapp():
    try:
        incoming_msg = request.form.get("Body")
        sender = request.form.get("From")

        print("📩 WHATSAPP MESSAGE:", incoming_msg)
        print("📲 FROM:", sender)

        # Extract phone
        if sender:
            phone = sender.replace("whatsapp:", "").replace("+", "")
        else:
            return "No sender", 400

        # 🚀 Trigger STK
        result = stk_push(phone)

        print("✅ STK RESULT:", result)

        return "STK Triggered", 200

    except Exception as e:
        print("WHATSAPP ERROR:", str(e))
        return "Error", 500


# ===============================
# 🧪 MANUAL TEST ENDPOINT
# ===============================
@app.route("/stk", methods=["POST"])
def manual_stk():
    try:
        data = request.get_json()
        phone = data.get("phone")

        result = stk_push(phone)

        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)})


# ===============================
# 🔁 CALLBACK (VERY IMPORTANT)
# ===============================
@app.route("/callback", methods=["POST"])
def callback():
    try:
        data = request.json

        print("📥 CALLBACK RECEIVED:", data)

        return jsonify({"status": "received"})

    except Exception as e:
        print("CALLBACK ERROR:", str(e))
        return jsonify({"error": str(e)})


# ===============================
# ❤️ HEALTH CHECK (RENDER FIX)
# ===============================
@app.route("/", methods=["GET"])
def home():
    return "🚀 Backend is live"


# ===============================
# 🚀 RUN
# ===============================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
