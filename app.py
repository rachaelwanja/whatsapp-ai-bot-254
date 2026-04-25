from flask import Flask, request, render_template, redirect, session, Response, jsonify
import json, datetime, os
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.secret_key = "super-secret-key"

# ================= DATABASE =================
uri = os.getenv("DATABASE_URL")

if uri and uri.startswith("postgres://"):
    uri = uri.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = uri
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# ================= MODELS =================
class Client(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    type = db.Column(db.String(50))
    plan = db.Column(db.String(20))
    active = db.Column(db.Boolean, default=True)
    expiry = db.Column(db.Date)
    phone = db.Column(db.String(20))
    username = db.Column(db.String(50))
    password = db.Column(db.String(50))

# ================= DEBUG =================
@app.route("/test")
def test():
    return "TEST WORKING"

@app.route("/routes")
def routes():
    return str(app.url_map)

# ================= LOGIN =================
@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        client = Client.query.filter_by(username=username, password=password).first()

        if client:
            session["client_id"] = client.id
            return redirect("/dashboard")

    return render_template("login.html")

# ================= SIGNUP (NEW) =================
@app.route("/signup", methods=["GET", "POST"])
def signup():

    if request.method == "POST":
        name = request.form["name"]
        username = request.form["username"]
        password = request.form["password"]

        new_client = Client(
            name=name,
            username=username,
            password=password,
            plan="basic",
            active=True
        )

        db.session.add(new_client)
        db.session.commit()

        return redirect("/login")

    return render_template("signup.html")

# ================= DASHBOARD =================
@app.route("/dashboard")
def dashboard():

    if "client_id" not in session:
        return redirect("/login")

    client = Client.query.get(session["client_id"])

    if not client or not client.active:
        return render_template("expired.html")

    return render_template("dashboard.html", client=client)

# ================= WHATSAPP =================
user_sessions = {}

@app.route("/whatsapp", methods=["POST"])
def whatsapp():

    msg = request.form.get("Body", "").lower()
    user = request.form.get("From")

    if msg in ["hi", "menu", "hey", "hello"]:
        return Response("""
<Response>
<Message>
Welcome 📚

1️⃣ Homework help  
2️⃣ Take a quiz  
</Message>
</Response>
""", mimetype="text/xml")

    return Response("<Response><Message>Type menu</Message></Response>", mimetype="text/xml")

# ================= HOME =================
@app.route("/")
def home():
    return render_template("index.html")

# ================= INIT DB =================
with app.app_context():
    db.create_all()

# ================= RUN =================
if __name__ == "__main__":
    app.run(debug=True)
