from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    session,
    flash,
    Response
)

from twilio.twiml.messaging_response import MessagingResponse

from models import (
    db,
    Business,
    Service,
    Conversation,
    Knowledge
)

from services import ask_ai
from brain.prompt_builder import build_prompt


whatsapp = Blueprint(
    "whatsapp",
    __name__
)

# =========================================
# WHATSAPP AI PAGE
# =========================================

@whatsapp.route("/whatsapp-ai")
def whatsapp_ai():

    if "business_id" not in session:
        return redirect("/login")

    business = Business.query.get(
        session["business_id"]
    )

    return render_template(
        "whatsapp_ai.html",
        business=business
    )
    
@whatsapp.route("/knowledge", methods=["GET", "POST"])
def knowledge():

    if "business_id" not in session:
        return redirect("/login")

    business = Business.query.get(
        session["business_id"]
    )

    # -------------------------------
    # SAVE NEW KNOWLEDGE
    # -------------------------------
    if request.method == "POST":

        item = Knowledge(
            business_id=business.id,
            question=request.form.get("question"),
            answer=request.form.get("answer")
        )

        print("Saving:", item.question, "->", item.answer)

        db.session.add(item)
        db.session.commit()

        return redirect("/knowledge")

    # -------------------------------
    # LOAD KNOWLEDGE
    # -------------------------------
    knowledge = Knowledge.query.filter_by(
        business_id=business.id
    ).all()

    print("Knowledge records:", len(knowledge))

    for item in knowledge:
        print(item.question, "->", item.answer)

    # -------------------------------
    # SHOW PAGE
    # -------------------------------
    return render_template(
        "knowledge.html",
        business=business,
        knowledge=knowledge
    )


# =========================================
# WHATSAPP AI RECEPTIONIST
# =========================================

@whatsapp.route("/whatsapp", methods=["POST"])
def whatsapp_route():

    # -------------------------------------
    # CUSTOMER MESSAGE
    # -------------------------------------

    incoming_msg = request.form.get(
        "Body",
        ""
    ).strip()

    customer_phone = request.form.get(
        "From",
        ""
    )

    response = MessagingResponse()

    # -------------------------------------
    # LOAD BUSINESS
    # -------------------------------------

    business = Business.query.first()

    if not business:

        response.message(
            "No business has been configured yet."
        )

        return Response(
            str(response),
            mimetype="text/xml"
        )

    # -------------------------------------
    # SAVE CUSTOMER MESSAGE
    # -------------------------------------

    customer_chat = Conversation(
        business_id=business.id,
        customer_phone=customer_phone,
        role="user",
        message=incoming_msg
    )

    db.session.add(customer_chat)
    db.session.commit()

    # -------------------------------------
    # LOAD SERVICES
    # -------------------------------------

    services = Service.query.filter_by(
        business_id=business.id
    ).all()

    if services:

        services_text = "\n\n".join(
            [
                f"""Service: {service.name}
Price: KES {service.price}
Duration: {service.duration}"""
                for service in services
            ]
        )

    else:

        services_text = "No services configured."

    print("========== SERVICES ==========")
    print(services_text)

    # =====================================
    # BUILD AI PROMPT
    # =====================================

    prompt = build_prompt(
        business=business,
        services_text=services_text
    )

    # =====================================
    # BUILD CONVERSATION HISTORY
    # =====================================

    messages = [
        {
            "role": "system",
            "content": prompt
        }
    ]

    history = Conversation.query.filter_by(
        business_id=business.id,
        customer_phone=customer_phone
    ).order_by(
        Conversation.created_at.asc()
    ).limit(20).all()

    for chat in history:

        messages.append(
            {
                "role": chat.role,
                "content": chat.message
            }
        )

    print("\n========== MESSAGES SENT TO OPENROUTER ==========")

    for i, msg in enumerate(messages, start=1):

        print(f"\nMessage {i}")
        print("ROLE:", msg["role"])
        print("CONTENT:")
        print(msg["content"])
    
    # =====================================
    # ASK OPENROUTER
    # =====================================

    reply = ask_ai(messages)

    print("\n========== AI REPLY ==========")
    print(reply)

    # =====================================
    # SAVE AI RESPONSE
    # =====================================

    ai_chat = Conversation(
        business_id=business.id,
        customer_phone=customer_phone,
        role="assistant",
        message=reply
    )

    db.session.add(ai_chat)
    db.session.commit()

    # =====================================
    # SEND WHATSAPP RESPONSE
    # =====================================

    response.message(reply)

    return Response(
        str(response),
        mimetype="text/xml"
    )