from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from openai import OpenAI
import os

app = Flask(__name__)

# Home route (required so Render doesn't crash)
@app.route("/")
def home():
    return "WhatsApp AI Bot is running successfully!"

# WhatsApp webhook
@app.route("/whatsapp", methods=["POST"])
def whatsapp():

    incoming_msg = request.form.get("Body", "").strip()

    # Prevent crash during Twilio validation
    if not incoming_msg:
        return str(MessagingResponse())

    try:
        # Initialize OpenAI client
        client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

        # Generate AI response
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful WhatsApp AI assistant."},
                {"role": "user", "content": incoming_msg}
            ]
        )

        reply = response.choices[0].message.content

    except Exception as e:
        print("ERROR:", e)
        reply = "Sorry, something went wrong."

    # Send response back to WhatsApp
    twilio_response = MessagingResponse()
    twilio_response.message(reply)

    return str(twilio_response)


# Required for local running (Render uses gunicorn)
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
