from flask import Flask, request, jsonify
import requests
import base64
from datetime import datetime
from requests.auth import HTTPBasicAuth

app = Flask(__name__)

# ===============================
# 🔐 CONFIG
# ===============================
CONSUMER_KEY = "YGIS9ihXR2PppZlQ8xMZgxwceAyBTnPUXKKmYyEBkELvaQCc"
CONSUMER_SECRET = "iNbAKgSOh5MmKwEDd7ZelDy5H4lLjRBCKGkayfEVdtLCI8t8Z1hN6pNj6mL6P5qD"

SHORTCODE = "174379"
PASSKEY = "bfb279f9aa9bdbcf158e97ddfce3c8b9"

CALLBACK_URL = "https://whatsapp-ai-bot-254-1.onrender.com/callback"


# ===============================
# 🔑 GET ACCESS TOKEN
# ===============================
def get_access_token():
    url = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"

    try:
        response = requests.get(
            url,
            auth=HTTPBasicAuth(CONSUMER_KEY, CONSUMER_SECRET),
            timeout=10
        )

        print("\n🔑 TOKEN STATUS:", response.status_code)
        print("🔑 TOKEN RESPONSE:", response.text)

        if response.status_code != 200:
            return None

        return response.json().get("access_token")

    except Exception as e:
        print("❌ TOKEN ERROR:", str(e))
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

    print("\n🚀 STARTING STK PUSH")

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

    print("📤 STK PAYLOAD:", payload)

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=15)

        print("📥 MPESA STATUS:", response.status_code)
        print("📥 MPESA RESPONSE:", response.text)

        try:
            return response.json()
        except:
            return {"error": "Invalid response", "raw": response.text}

    except Exception as e:
        print("❌ STK ERROR:", str(e))
        return {"error": str(e)}


# ===============================
# 📩 WHATSAPP WEBHOOK
# ===============================
@app.route("/whatsapp", methods=["POST"])
def whatsapp():
    try:
        incoming_msg = request.form.get("Body")
        sender = request.form.get("From")

        print("\n📩 MESSAGE:", incoming_msg)
        print("📲 FROM:", sender)

        if not sender:
            return "No sender", 400

        phone = sender.replace("whatsapp:", "").replace("+", "")

        result = stk_push(phone)

        print("✅ RESULT:", result)

        return "OK", 200

    except Exception as e:
        print("❌ ERROR:", str(e))
        return "Error", 500


# ===============================
# 🧪 MANUAL TEST
# ===============================
@app.route("/stk", methods=["POST"])
def manual_stk():
    data = request.get_json()
    phone = data.get("phone")

    result = stk_push(phone)

    return jsonify(result)


# ===============================
# 🔁 CALLBACK
# ===============================
@app.route("/callback", methods=["POST"])
def callback():
    data = request.json
    print("\n📥 CALLBACK:", data)
    return jsonify({"status": "received"})


# ===============================
# ❤️ HEALTH CHECK
# ===============================
@app.route("/", methods=["GET"])
def home():
    return "🚀 Backend is live"


# ===============================
# 🚀 RUN
# ===============================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
