from flask import Flask, request, render_template, redirect, jsonify, Response
from twilio.twiml.voice_response import VoiceResponse
import requests, json
from datetime import datetime

app = Flask(__name__)

# -----------------------------
# HELPERS
# -----------------------------

def load_json(file):
    try:
        with open(file, "r") as f:
            return json.load(f)
    except:
        return []

def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=2)


# -----------------------------
# HOME
# -----------------------------
@app.route("/")
def home():
    return render_template("index.html")


# -----------------------------
# DASHBOARD
# -----------------------------
@app.route("/dashboard")
def dashboard():
    payments = load_json("payments.json")
    appointments = load_json("appointments.json")

    total_revenue = sum([p["amount"] for p in payments]) if payments else 0

    return render_template(
        "dashboard.html",
        payments=payments,
        appointments=appointments,
        revenue=total_revenue
    )


# -----------------------------
# PAYMENTS PAGE
# -----------------------------
@app.route("/payments")
def payments_page():
    payments = load_json("payments.json")
    return render_template("payments.html", payments=payments)


# -----------------------------
# CUSTOMERS PAGE
# -----------------------------
@app.route("/customers")
def customers_page():
    customers = load_json("appointments.json")
    return render_template("customers.html", customers=customers)


# -----------------------------
# SETTINGS PAGE
# -----------------------------
@app.route("/settings")
def settings():
    return render_template("settings.html")


# -----------------------------
# MPESA STK PUSH (SIMPLIFIED)
# -----------------------------
def stk_push(phone, amount):
    print("Sending STK push to:", phone, "Amount:", amount)

    # TODO: Replace with real MPESA API
    return True


@app.route("/pay", methods=["POST"])
def pay():
    data = request.json

    phone = data.get("phone")
    amount = data.get("amount")

    stk_push(phone, amount)

    return jsonify({"status": "Payment request sent"})


# -----------------------------
# MPESA CALLBACK (SAVE PAYMENT)
# -----------------------------
@app.route("/callback", methods=["POST"])
def callback():
    data = request.json

    phone = data.get("PhoneNumber", "unknown")
    amount = int(data.get("Amount", 0))

    payments = load_json("payments.json")

    payments.append({
        "phone": phone,
        "amount": amount,
        "date": str(datetime.now())
    })

    save_json("payments.json", payments)

    return jsonify({"ResultCode": 0})


# -----------------------------
# VOICE AI (CORE SYSTEM)
# -----------------------------
@app.route("/voice", methods=["POST"])
def voice():
    response = VoiceResponse()

    speech = request.values.get("SpeechResult")

    if not speech:
        gather = response.gather(input="speech", action="/voice", method="POST")
        gather.say("Hello! Welcome to Flow AI. What service would you like to book?")
        return Response(str(response), mimetype="text/xml")

    speech = speech.lower()
    phone = request.values.get("From").replace("+", "")

    # SIMPLE AI LOGIC
    if "hair" in speech or "appointment" in speech:

        # SAVE BOOKING
        appointments = load_json("appointments.json")

        booking = {
            "phone": phone,
            "service": "Hair Service",
            "date": str(datetime.now())
        }

        appointments.append(booking)
        save_json("appointments.json", appointments)

        # SEND PAYMENT
        requests.post("https://whatsapp-ai-bot-254-1.onrender.com/pay", json={
            "phone": phone,
            "amount": 1000
        })

        response.say("Your appointment has been booked. A payment request has been sent to your phone.")

    else:
        response.say("Sorry, I didn't understand. Please say the service you want.")

    return Response(str(response), mimetype="text/xml")


# -----------------------------
# RUN
# -----------------------------
if __name__ == "__main__":
    app.run(debug=True)
