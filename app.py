import requests
import base64
from datetime import datetime

# 🔐 Your credentials (from Safaricom portal)
CONSUMER_KEY = "YOUR_CONSUMER_KEY"
CONSUMER_SECRET = "YOUR_CONSUMER_SECRET"

# 🏦 Sandbox details
SHORTCODE = "174379"
PASSKEY = "bfb279f9aa9bdbc...YOUR_FULL_PASSKEY..."

# 📱 Sandbox test number
PHONE = "254708374149"

# 🌐 Your callback URL (must be live https)
CALLBACK_URL = "https://your-domain.com/callback"

# ===============================
# 1. GENERATE ACCESS TOKEN
# ===============================
def get_access_token():
    url = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
    
    response = requests.get(url, auth=(CONSUMER_KEY, CONSUMER_SECRET))
    data = response.json()
    
    return data['access_token']

# ===============================
# 2. GENERATE PASSWORD + TIMESTAMP
# ===============================
def generate_password():
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    
    data_to_encode = SHORTCODE + PASSKEY + timestamp
    password = base64.b64encode(data_to_encode.encode()).decode()
    
    return password, timestamp

# ===============================
# 3. STK PUSH REQUEST
# ===============================
def stk_push():
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
        "PartyA": PHONE,
        "PartyB": SHORTCODE,
        "PhoneNumber": PHONE,
        "CallBackURL": CALLBACK_URL,
        "AccountReference": "FlowAI",
        "TransactionDesc": "Test Payment"
    }

    response = requests.post(url, json=payload, headers=headers)
    print("RESPONSE:", response.json())

# ===============================
# RUN
# ===============================
if __name__ == "__main__":
    stk_push()
