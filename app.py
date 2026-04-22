from flask import Flask, request, jsonify
import requests
import base64
from datetime import datetime

app = Flask(__name__)

# ===============================
# 🔐 CONFIG (YOUR REAL VALUES)
# ===============================
CONSUMER_KEY = "YGIS9ihXR2PppZlQ8xMZgxwceAyBTnPUXKKmYyEBkELvaQCc"
CONSUMER_SECRET = "iNbAKgSOh5MmKwEDd7ZelDy5H4lLjRBCKGkayfEVdtLCI8t8Z1hN6pNj6mL6P5qD"

SHORTCODE = "174379"

PASSKEY = "bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919"

CALLBACK_URL = "https://whatsapp-ai-bot-254-1.onrender.com/callback"


# ===============================
# 🔑 GET ACCESS TOKEN (FIXED)
# ===============================
def get_access_token():
    url = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"

    try:
        response = requests.get(url, auth=(CONSUMER_KEY, CONSUMER_SECRET))

        print("\n🔑 ===== TOKEN REQUEST =====")
        print("STATUS:", response.status_code)
        print("RAW:", response.text)

        if response.status_code != 200:
            return None

        try:
            data = response.json()
            return data.get("access_token")
        except:
            print("❌ JSON PARSE ERROR")
            return None

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
    print("\n🚀 ===== STARTING STK PUSH =====")

    access_token = get_access_token()

    if not access_token:
        print("❌ FAILED TO GET ACCESS TOKEN")
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

    print("\n📤 STK PAYLOAD:", payload)

    try:
        response = requests.post(url, json=payload, headers=headers)

        print("\n📥 MPESA STATUS:", response.status_code)
        print("📥 MPESA RESPONSE:", response.text)

        try:
            return response.json()
        except:
            return {"error": "Invalid MPESA response", "raw": response.text}

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

        print("\n📩 ===== WHATSAPP INCOMING =====")
        print("MESSAGE:", incoming_msg)
        print("FROM:", sender)

        if not sender:
            return "No sender", 400

        # Clean phone
        phone = sender.replace("whatsapp:", "").replace("+", "")

        # ✅ FORCE WORKING SANDBOX NUMBER
        phone = "254708374149"

        print("📞 USING PHONE:", phone)

        result = stk_push(phone)

        print("\n✅ STK RESULT:", result)

        return "STK Triggered", 200

    except Exception as e:
        print("❌ WHATSAPP ERROR:", str(e))
        return "Error", 500


# ===============================
# 🧪 MANUAL TEST
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
# 🔁 CALLBACK
# ===============================
@app.route("/callback", methods=["POST"])
def callback():
    try:
        data = request.json

        print("\n📥 ===== CALLBACK RECEIVED =====")
        print(data)

        return jsonify({"status": "received"})

    except Exception as e:
        print("❌ CALLBACK ERROR:", str(e))
        return jsonify({"error": str(e)})


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
