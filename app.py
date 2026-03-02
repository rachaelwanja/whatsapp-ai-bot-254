from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse

app = Flask(__name__)

@app.route("/")
def home():
    return "WhatsApp AI Bot is running successfully!"

@app.route("/whatsapp", methods=["POST"])
def whatsapp():
    incoming_msg = request.form.get("Body")

    resp = MessagingResponse()
    msg = resp.message()
    msg.body(f"You said: {incoming_msg}")

    return str(resp)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)