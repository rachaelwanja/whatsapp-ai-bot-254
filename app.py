from flask import Flask, request, render_template, redirect, session
from flask_sqlalchemy import SQLAlchemy
import datetime, os, requests, base64

app = Flask(__name__)
app.secret_key = "secret"

# ================= DATABASE =================
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

# ================= MODELS =================
class Client(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    username = db.Column(db.String(50))
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

# ================= HELPERS =================
def require_login():
    return "client_id" in session

def get_client():
    return Client.query.get(session.get("client_id"))

# ================= MPESA =================
def get_access_token():
    url = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
    response = requests.get(
        url,
        auth=(os.getenv("MPESA_CONSUMER_KEY"), os.getenv("MPESA_CONSUMER_SECRET"))
    )
    return response.json().get("access_token")

def stk_push(phone, amount):
    access_token = get_access_token()

    shortcode = os.getenv("MPESA_SHORTCODE")
    passkey = os.getenv("MPESA_PASSKEY")
    callback_url = os.getenv("CALLBACK_URL")

    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    password = base64.b64encode((shortcode + passkey + timestamp).encode()).decode()

    url = "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest"

    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    payload = {
        "BusinessShortCode": shortcode,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": amount,
        "PartyA": phone,
        "PartyB": shortcode,
        "PhoneNumber": phone,
        "CallBackURL": callback_url,
        "AccountReference": "FlowAI",
        "TransactionDesc": "Subscription Payment"
    }

    requests.post(url, json=payload, headers=headers)

# ================= ROUTES =================
@app.route("/")
def home():
    return render_template("index.html")

# ===== AUTH =====
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        client = Client(
            name=request.form.get("name"),
            phone=request.form.get("phone"),
            username=request.form.get("username"),
            password=request.form.get("password"),
            expiry=datetime.date.today() + datetime.timedelta(days=7)
        )
        db.session.add(client)
        db.session.commit()
        return redirect("/login")

    return render_template("signup.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        client = Client.query.filter_by(
            username=request.form.get("username"),
            password=request.form.get("password")
        ).first()

        if client:
            session["client_id"] = client.id
            return redirect("/dashboard")

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# ===== DASHBOARD =====
@app.route("/dashboard")
def dashboard():
    if not require_login():
        return redirect("/login")

    client = get_client()

    payments = Payment.query.filter_by(client_id=client.id).all()
    appointments = Appointment.query.filter_by(client_id=client.id).all()

    revenue = sum(p.amount or 0 for p in payments)

    return render_template(
        "dashboard.html",
        revenue=revenue,
        total_bookings=len(appointments),
        total_customers=len(appointments),
        payments=payments,
        chart_labels=[p.date for p in payments],
        chart_data=[p.amount for p in payments]
    )

# ===== PAYMENTS =====
@app.route("/payments")
def payments():
    if not require_login():
        return redirect("/login")

    client = get_client()
    payments = Payment.query.filter_by(client_id=client.id).all()

    return render_template("payments.html", payments=payments)

@app.route("/pay", methods=["POST"])
def pay():
    if not require_login():
        return redirect("/login")

    phone = request.form.get("phone")
    amount = int(request.form.get("amount"))

    stk_push(phone, amount)

    return "Payment request sent 📲"

# ===== MPESA CALLBACK =====
@app.route("/callback", methods=["POST"])
def mpesa_callback():
    data = request.get_json()

    try:
        result = data["Body"]["stkCallback"]

        if result["ResultCode"] == 0:

            metadata = result["CallbackMetadata"]["Item"]

            amount = next(i["Value"] for i in metadata if i["Name"] == "Amount")
            phone = next(i["Value"] for i in metadata if i["Name"] == "PhoneNumber")

            payment = Payment(
                phone=str(phone),
                amount=int(amount),
                date=str(datetime.datetime.now()),
                client_id=1  # later make dynamic
            )

            db.session.add(payment)
            db.session.commit()

    except Exception as e:
        print("MPESA ERROR:", e)

    return "OK"

# ===== CUSTOMERS =====
@app.route("/customers")
def customers():
    if not require_login():
        return redirect("/login")

    client = get_client()
    customers = Appointment.query.filter_by(client_id=client.id).all()

    return render_template("customers.html", customers=customers)

# ===== SETTINGS =====
@app.route("/settings")
def settings():
    if not require_login():
        return redirect("/login")

    client = get_client()
    return render_template("settings.html", client=client)

# ================= INIT =================
with app.app_context():
    db.create_all()

# ================= RUN =================
if __name__ == "__main__":
    app.run(debug=True)
