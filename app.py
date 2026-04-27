from flask import Flask, request, render_template, redirect, session, Response, jsonify
from flask_sqlalchemy import SQLAlchemy
from apscheduler.schedulers.background import BackgroundScheduler
import datetime, os, requests, base64

app = Flask(__name__)
app.secret_key = "super-secret-key"

# ================= DATABASE =================
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

# ================= CONFIG =================
PLANS = {
    "basic": 500,
    "pro": 1000,
    "premium": 2000
}

user_sessions = {}

# ================= MODELS =================
class Client(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    phone = db.Column(db.String(20))  # WhatsApp number
    username = db.Column(db.String(50), unique=True)
    password = db.Column(db.String(50))
    plan = db.Column(db.String(20), default="basic")
    active = db.Column(db.Boolean, default=True)
    expiry = db.Column(db.Date)

class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    phone = db.Column(db.String(20))
    date = db.Column(db.String(100))
    client_id = db.Column(db.Integer)

class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    phone = db.Column(db.String(20))
    amount = db.Column(db.Integer)
    date = db.Column(db.String(50))
    client_id = db.Column(db.Integer)

# ================= MPESA CONFIG =================
MPESA = {
    "consumer_key": os.getenv("MPESA_CONSUMER_KEY"),
    "consumer_secret": os.getenv("MPESA_CONSUMER_SECRET"),
    "shortcode": os.getenv("MPESA_SHORTCODE"),
    "passkey": os.getenv("MPESA_PASSKEY")
}

# ================= MPESA =================
def get_access_token():
    url = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
    res = requests.get(url, auth=(MPESA["consumer_key"], MPESA["consumer_secret"]))
    return res.json().get("access_token")

def stk_push(phone, amount, client_id):

    access_token = get_access_token()
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")

    password = base64.b64encode(
        (MPESA["shortcode"] + MPESA["passkey"] + timestamp).encode()
    ).decode()

    payload = {
        "BusinessShortCode": MPESA["shortcode"],
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": amount,
        "PartyA": phone,
        "PartyB": MPESA["shortcode"],
        "PhoneNumber": phone,
        "CallBackURL": "https://flowai.co.ke/mpesa/callback",
        "AccountReference": str(client_id),
        "TransactionDesc": "FlowAI Subscription"
    }

    headers = {"Authorization": f"Bearer {access_token}"}

    requests.post(
        "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest",
        json=payload,
        headers=headers
    )

# ================= CALLBACK =================
@app.route("/mpesa/callback", methods=["POST"])
def mpesa_callback():

    data = request.get_json()

    try:
        callback = data["Body"]["stkCallback"]

        if callback["ResultCode"] == 0:

            metadata = callback["CallbackMetadata"]["Item"]

            amount = next(i["Value"] for i in metadata if i["Name"] == "Amount")
            phone = str(next(i["Value"] for i in metadata if i["Name"] == "PhoneNumber"))

            client = Client.query.filter_by(phone=phone).first()

            if client:
                client.active = True
                client.expiry = datetime.date.today() + datetime.timedelta(days=30)

                db.session.add(Payment(
                    phone=phone,
                    amount=amount,
                    date=str(datetime.date.today()),
                    client_id=client.id
                ))

                db.session.commit()

    except Exception as e:
        print("MPESA ERROR:", e)

    return jsonify({"status": "ok"})

# ================= AI =================
def ai_reply(message, client):

    prompt = f"""
You are a Kenyan WhatsApp receptionist and sales assistant for {client.name}.

Rules:
- Be friendly (Kenyan tone)
- Detect booking → BOOKING_REQUEST: <date/time>
- Detect payment → PAYMENT_REQUEST
- Upsell services

User: {message}
"""

    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {os.getenv('OPENROUTER_API')}",
                "Content-Type": "application/json"
            },
            json={
                "model": "openai/gpt-4o-mini",
                "messages": [{"role": "user", "content": prompt}]
            }
        )

        return response.json()["choices"][0]["message"]["content"]

    except:
        return "Sasa 👋 how can I help?"

# ================= REMINDER SYSTEM =================
def send_whatsapp_message(phone, message):
    print(f"Sending to {phone}: {message}")

def check_subscriptions():

    today = datetime.date.today()
    clients = Client.query.all()

    for c in clients:

        if not c.expiry:
            continue

        days_left = (c.expiry - today).days

        if days_left == 3:
            send_whatsapp_message(c.phone, f"{c.name} 👋 expires in 3 days. Reply PAY.")

        if days_left == 1:
            send_whatsapp_message(c.phone, f"⚠️ expires tomorrow. Reply PAY.")

        if days_left < 0:
            c.active = False

    db.session.commit()

scheduler = BackgroundScheduler()
scheduler.add_job(func=check_subscriptions, trigger="interval", hours=6)
scheduler.start()

# ================= ROUTES =================
@app.route("/")
def home():
    return render_template("index.html")

# ================= AUTH =================
@app.route("/signup", methods=["GET","POST"])
def signup():
    if request.method == "POST":
        client = Client(
            name=request.form["name"],
            phone=request.form["phone"],
            username=request.form["username"],
            password=request.form["password"],
            active=True,
            expiry=datetime.date.today() + datetime.timedelta(days=7)
        )
        db.session.add(client)
        db.session.commit()
        return redirect("/login")

    return render_template("signup.html")

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        client = Client.query.filter_by(
            username=request.form["username"],
            password=request.form["password"]
        ).first()

        if client:
            session["client_id"] = client.id
            return redirect("/dashboard")

    return render_template("login.html")

# ================= DASHBOARD =================
@app.route("/dashboard")
def dashboard():

    if "client_id" not in session:
        return redirect("/login")

    client_id = session["client_id"]

    payments = Payment.query.filter_by(client_id=client_id).all()
    appointments = Appointment.query.filter_by(client_id=client_id).all()

    revenue = sum(p.amount for p in payments)

    chart_labels = [p.date for p in payments]
    chart_data = [p.amount for p in payments]

    return render_template(
        "dashboard.html",
        total_customers=len(appointments),
        total_bookings=len(appointments),
        revenue=revenue,
        payments=payments,
        chart_labels=chart_labels,
        chart_data=chart_data
    )

# ================= WHATSAPP =================
@app.route("/whatsapp", methods=["POST"])
def whatsapp():

    incoming = request.form.get("Body", "").strip()
    user = request.form.get("From")
    to = request.form.get("To")

    client = Client.query.filter_by(phone=to).first()

    if not client:
        return Response("<Response><Message>Bot not configured</Message></Response>", mimetype="text/xml")

    msg = incoming.lower()

    if user not in user_sessions:
        user_sessions[user] = {}

    s = user_sessions[user]

    # 🔥 PAY TRIGGER
    if msg == "pay":
        s["step"] = "pay_number"
        return Response("<Response><Message>Tuma namba ya MPESA (2547...)</Message></Response>", mimetype="text/xml")

    # RECEIVE NUMBER
    if s.get("step") == "pay_number":
        stk_push(incoming, PLANS[client.plan], client.id)
        s["step"] = None
        return Response("<Response><Message>STK sent 👍</Message></Response>", mimetype="text/xml")

    # SUBSCRIPTION CHECK
    if not client.active or client.expiry < datetime.date.today():
        return Response("<Response><Message>Subscription expired. Reply PAY.</Message></Response>", mimetype="text/xml")

    # AI
    ai = ai_reply(incoming, client)

    # BOOKING
    if ai.startswith("BOOKING_REQUEST:"):
        date = ai.replace("BOOKING_REQUEST:", "").strip()

        db.session.add(Appointment(
            phone=user,
            date=date,
            client_id=client.id
        ))
        db.session.commit()

        return Response(f"<Response><Message>Booked {date}</Message></Response>", mimetype="text/xml")

    # PAYMENT REQUEST
    if ai == "PAYMENT_REQUEST":
        s["step"] = "pay_number"
        return Response("<Response><Message>Tuma namba ya MPESA</Message></Response>", mimetype="text/xml")

    return Response(f"<Response><Message>{ai}</Message></Response>", mimetype="text/xml")

# ================= INIT =================
with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(debug=True)
