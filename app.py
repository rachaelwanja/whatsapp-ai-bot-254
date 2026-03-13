from flask import Flask, request, jsonify, send_file
from twilio.twiml.messaging_response import MessagingResponse
from google import genai

import os
import random
import requests
import speech_recognition as sr
from pydub import AudioSegment
from datetime import datetime

app = Flask(__name__)

# ---------------------------
# Gemini AI Setup
# ---------------------------
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

# ---------------------------
# Memory + Leads
# ---------------------------
memory = {}
leads = {}

# ---------------------------
# Home Route
# ---------------------------
@app.route("/")
def home():
    return "WhatsApp AI Bot Running"


# ---------------------------
# Website Chat Page
# ---------------------------
@app.route("/webchat")
def webchat():
    return send_file("chat.html")


# ---------------------------
# Admin Dashboard
# ---------------------------
@app.route("/dashboard")
def dashboard():
    return send_file("dashboard.html")


# ---------------------------
# Leads API
# ---------------------------
@app.route("/leads")
def get_leads():

    lead_list = []

    for user,data in leads.items():

        lead_list.append({
            "user":user,
            "name":data.get("name",""),
            "service":data.get("service","")
        })

    return jsonify(lead_list)


# ---------------------------
# Website Chat API
# ---------------------------
@app.route("/chat", methods=["POST"])
def chat():

    data = request.json
    user_message = data.get("message","")

    try:

        response = client.models.generate_content(
            model="gemini-1.5-flash-8b",
            contents=user_message
        )

        reply = response.text

    except Exception as e:

        print("AI ERROR:",e)
        reply = "AI temporarily unavailable."

    return jsonify({"reply":reply})


# ---------------------------
# Voice Processing
# ---------------------------
def process_voice(media_url):

    try:

        audio_file = "voice.ogg"

        r = requests.get(media_url)

        with open(audio_file,"wb") as f:
            f.write(r.content)

        sound = AudioSegment.from_ogg(audio_file)
        sound.export("voice.wav",format="wav")

        recognizer = sr.Recognizer()

        with sr.AudioFile("voice.wav") as source:
            audio = recognizer.record(source)

        text = recognizer.recognize_google(audio)

        return text

    except Exception as e:

        print("VOICE ERROR:",e)

        return None


# ---------------------------
# WhatsApp Bot
# ---------------------------
@app.route("/whatsapp", methods=["POST"])
def whatsapp():

    incoming_msg = request.values.get("Body","").strip()
    user = request.values.get("From")
    media_url = request.values.get("MediaUrl0")

    resp = MessagingResponse()
    msg = resp.message()

    # ---------------------------
    # Voice message detection
    # ---------------------------
    if media_url:

        voice_text = process_voice(media_url)

        if voice_text:
            incoming_msg = voice_text
        else:
            incoming_msg = "voice message"

    text = incoming_msg.lower()

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # ---------------------------
    # Log conversation
    # ---------------------------
    with open("chat_log.txt","a") as log:
        log.write(f"{timestamp} | {user} | USER: {incoming_msg}\n")


    # ---------------------------
    # Reset
    # ---------------------------
    if text == "reset":

        memory[user] = []
        leads[user] = {}

        reply = "Conversation reset. How can I help you today?"

        msg.body(reply)

        return str(resp)


    # ---------------------------
    # Greeting
    # ---------------------------
    if text in ["hi","hello","hey"]:

        greetings = [

            "Hello 👋 I'm your AI assistant. How can I help you today?",
            "Hi there 😊 What can I assist you with?",
            "Hey! I'm here to help. Ask me anything.",
            "Hello! 👋 How may I assist you today?"

        ]

        reply = random.choice(greetings)


    # ---------------------------
    # Menu
    # ---------------------------
    elif text in ["menu","help"]:

        reply = (
            "AI Assistant Menu\n\n"
            "1 Ask any question\n"
            "2 Get information\n"
            "3 Chat with AI\n"
            "4 Book a service\n\n"
            "Just send your message."
        )


    # ---------------------------
    # Lead capture
    # ---------------------------
    elif "book" in text or "service" in text:

        leads[user] = {"service":incoming_msg}

        reply = "Great! May I have your name?"


    elif user in leads and "name" not in leads[user]:

        leads[user]["name"] = incoming_msg

        reply = "Thanks! Our team will contact you shortly."


    # ---------------------------
    # AI conversation
    # ---------------------------
    else:

        try:

            if user not in memory:
                memory[user] = []

            memory[user].append(incoming_msg)

            memory[user] = memory[user][-6:]

            conversation = "\n".join(memory[user])

            response = client.models.generate_content(
                model="gemini-1.5-flash-8b",
                contents=f"""
You are a helpful WhatsApp AI assistant.

Respond clearly and briefly.

Conversation:
{conversation}
"""
            )

            reply = response.text

            if not reply:
                reply = "I'm here 😊 Ask me something."

            memory[user].append(reply)

        except Exception as e:

            print("AI ERROR:",e)

            reply = "AI is busy right now. Please try again later."


    # ---------------------------
    # Log bot reply
    # ---------------------------
    with open("chat_log.txt","a") as log:
        log.write(f"{timestamp} | BOT: {reply}\n")


    msg.body(reply)

    return str(resp)


# ---------------------------
# Run server
# ---------------------------
if __name__ == "__main__":

    port = int(os.environ.get("PORT",10000))

    app.run(host="0.0.0.0",port=port)
