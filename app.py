from flask import Flask, request, jsonify
import requests
import base64
from datetime import datetime
from requests.auth import HTTPBasicAuth

app = Flask(__name__)

# ===============================
# 🔐 CONFIG (PUT YOUR REAL VALUES)
# ===============================
CONSUMER_KEY = "qj4VjbXA8aEbDHhcseYNZVQN2MUHAqEu0tcnBuLQoz25kpl6"
CONSUMER_SECRET = "iNbAKgSOh5MmKwEDd7ZelDy5H4lLjRBCKGkayfEVdtLCI8t8Z1hN6pNj6mL6P5qD"

SHORTCODE = "174379"
PASSKEY = "bfb279f9aa9bdbcf158e97ddfce3c8b9"  # Sandbox default

CALLBACK_URL = "https://whatsapp-ai-bot-254-1.onrender.com/callback"


# ===============================
# 🔑 GET ACCESS TOKEN (ROBUST)
# ===============================
def get_access_token():
    url = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"

    try:
        response = requests.get(
            url,
            auth=HTTPBasicAuth(CONSUMER_KEY, CONSUMER_SECRET),
            timeout=10
        )

        print("\n🔑 ===== TOKEN REQUEST =====")
        print("STATUS:", response.status_code)
        print("RAW:", response.text)

        if response.status_code != 200:
            return None

        data = response.json()
        return data.get("access_token")

    except Exception as e:
        print("❌ TOKEN ERROR:", str(e))
        return None


# ===============================
# 🔐 GENERATE PASSWORD
# ===============================
def generate_password():
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    raw = SHORTCODE + PASSKEY + timestamp
    password = base64.b64encode(raw.encode()).decode()

    print("\n🔐 PASSWORD GENERATED")
    print("Timestamp:", timestamp)

    return password, timestamp


# ===============================
# 💳 STK PUSH
# ===============================
def stk_push(phone):

    print("\n🚀 ===== STK PUSH START =====")

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

    print("\n📤 STK REQUEST PAYLOAD:")
    print(payload)

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=15)

        print("\n📥 ===== MPESA RESPONSE =====")
        print("STATUS:", response.status_code)
        print("RAW:", response.text)

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
        print("Message:", incoming_msg)
        print("From:", sender)

        if not sender:
            return "No sender", 400

        # Convert phone to format: 2547XXXXXXXX
        phone = sender.replace("whatsapp:", "").replace("+", "")

        result = stk_push(phone)

        print("\n✅ STK RESULT:", result)

        return "OK", 200

    except Exception as e:
        print("❌ WHATSAPP ERROR:", str(e))
        return "Error", 500


# ===============================
# 🧪 MANUAL TEST ENDPOINT
# ===============================
@app.route("/stk", methods=["POST"])
def manual_stk():
    try:
        data = request.get_json()

        if not data or "phone" not in data:
            return jsonify({"error": "Missing phone"}), 400

        phone = data.get("phone")

        print("\n🧪 MANUAL STK TEST:", phone)

        result = stk_push(phone)

        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ===============================
# 🔁 CALLBACK (MPESA RESPONSE)
# ===============================
@app.route("/callback", methods=["POST"])
def callback():
    try:
        data = request.json

        print("\n📥 ===== MPESA CALLBACK =====")
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
    return "🚀 Backend is live and ready"


# ===============================
# 🚀 RUN
# ===============================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
