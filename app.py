from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from google import genai
import os

app = Flask(__name__)

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

@app.route("/")
def home():
    return "AI Bot Running"

@app.route("/whatsapp", methods=["POST"])
def whatsapp():

    incoming_msg = request.values.get("Body", "")

    resp = MessagingResponse()
    msg = resp.message()

    try:
        response = client.models.generate_content(
            model="gemini-1.5-flash-8b",
            contents=incoming_msg
        )

        reply = response.text

    except Exception as e:
        print("AI ERROR:", e)
        reply = "AI temporarily unavailable."

    msg.body(reply)

    return str(resp)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
