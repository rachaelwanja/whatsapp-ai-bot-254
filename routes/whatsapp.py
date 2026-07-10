from flask import (
    Blueprint,
    request,
    redirect,
    session,
    render_template,
    Response
)

from twilio.twiml.messaging_response import MessagingResponse

from models import (
    Business,
    Service
    conversation
)

from services import ask_ai

whatsapp = Blueprint(
    "whatsapp",
    __name__
)

# =========================================
# WHATSAPP AI
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
    
# =========================================
# WHATSAPP AI RECEPTIONIST
# =========================================

@whatapp.route("/whatsapp", methods=["POST"])
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

    # -------------------------------------
    # SYSTEM PROMPT
    # -------------------------------------

    prompt = f"""
You are the official AI receptionist for this business.

Your goal is to help customers exactly like a real receptionist.

Business Name:
{business.business_name}

Business Type:
{business.business_type}

Location:
{business.location}

Opening Hours:
{business.opening_hours}

Available Services:

{services_text}

Business Instructions:

{business.ai_prompt}

Rules:

- Be friendly and professional.
- Keep replies short.
- Never invent services.
- Never invent prices.
- Recommend only listed services.
- Help customers book appointments.
- Ask only ONE question at a time.
- Continue the conversation naturally.
- Never restart the conversation.
- Never tell customers to contact the business unless absolutely necessary.
"""

    # -------------------------------------
    # BUILD CONVERSATION HISTORY
    # -------------------------------------

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
        
    # -------------------------------------
    # ASK OPENROUTER
    # -------------------------------------

    reply = ask_ai(messages)

    print("\n========== AI REPLY ==========")
    print(reply)

    # -------------------------------------
    # SAVE AI REPLY
    # -------------------------------------

    ai_chat = Conversation(
        business_id=business.id,
        customer_phone=customer_phone,
        role="assistant",
        message=reply
    )

    db.session.add(ai_chat)
    db.session.commit()

    # -------------------------------------
    # SEND WHATSAPP RESPONSE
    # -------------------------------------

    response.message(reply)

    return Response(
        str(response),
        mimetype="text/xml"
    )
