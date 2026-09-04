
from datetime import datetime, timedelta
import json
import re
from urllib import response

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
    Knowledge,
    Conversation,
    Appointment
)

from services import ask_ai
from brain.prompt_builder import build_prompt
from brain.business_hours import check_business_hours
from brain.rescheduling import process_reschedule
from brain.customer import (
    get_or_create_customer,
    update_customer_name
)
from brain.customer_history import (
    get_customer_history,
    format_customer_history
)
import services

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

        print(
            "Saving:",
            item.question,
            "->",
            item.answer
        )

        db.session.add(item)
        db.session.commit()

        return redirect("/knowledge")

    # -------------------------------
    # LOAD KNOWLEDGE
    # -------------------------------

    knowledge = Knowledge.query.filter_by(
        business_id=business.id
    ).all()

    print(
        "Knowledge records:",
        len(knowledge)
    )

    for item in knowledge:
        print(
            item.question,
            "->",
            item.answer
        )

    # -------------------------------
    # SHOW PAGE
    # -------------------------------

    return render_template(
        "sections/ai/knowledge.html",
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

    print(
        "========== INCOMING WHATSAPP =========="
    )

    print(
        "CUSTOMER PHONE:",
        customer_phone
    )

    print(
        "MESSAGE:",
        incoming_msg
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
    # GET / CREATE CUSTOMER
    # -------------------------------------

    customer = get_or_create_customer(
        business_id=business.id,
        customer_phone=customer_phone
    )
    print(
        "========== CUSTOMER =========="
    )

    print(
        "CUSTOMER ID:",
        customer.id
    )

    print(
        "CUSTOMER PHONE:",
        customer.phone
    )

    print(
        "CUSTOMER NAME:",
        customer.name
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

    db.session.add(
        customer_chat
    )

    db.session.commit()

    # -------------------------------------
    # LOAD SERVICES
    # -------------------------------------

    services = Service.query.filter_by(
        business_id=business.id
    ).all()

    print("========== SERVICE DEBUG ==========")
    print("BUSINESS ID:", business.id)
    print("BUSINESS NAME:", business.business_name)
    print("TOTAL SERVICES:", len(services))

    for service in services:

        print(
            service.id,
            "|",
            service.name,
            "|",
            service.price,
            "|",
            service.duration,
            "| AVAILABLE:",
            service.available
        )

    print("===================================")

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

        services_text = "No services are currently available."

    print("========== SERVICES ==========")
    print(services_text)

    # =====================================
    # LOAD KNOWLEDGE BASE
    # =====================================

    knowledge_items = Knowledge.query.filter_by(
        business_id=business.id
    ).all()

    if knowledge_items:

        knowledge_text = "\n\n".join(
            [
                f"""Question: {item.question}
Answer: {item.answer}"""
                for item in knowledge_items
            ]
        )

    else:

        knowledge_text = "No business knowledge configured."

    print("========== KNOWLEDGE ==========")
    print(knowledge_text)

    # =====================================
    # LOAD CUSTOMER HISTORY
    # =====================================

    customer_history = get_customer_history(
        business_id=business.id,
        customer_phone=customer_phone
    )

    customer_history_text = format_customer_history(
        customer_history,
        customer_name=customer.name
    )

    print("\n========== CUSTOMER HISTORY ==========")
    print(customer_history_text)

    # =====================================
    # BUILD AI PROMPT
    # =====================================

    prompt = build_prompt(
    business=business,
    services_text=services_text,
    knowledge_text=knowledge_text,
    customer_history_text=customer_history_text,
    current_message=incoming_msg
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
        Conversation.created_at.desc()
    ).limit(10).all()

    history.reverse()

    for chat in history:

        messages.append(
            {
                "role": chat.role,
                "content": chat.message
            }
        )

    print("\n========== SYSTEM PROMPT ==========")
    print(prompt)

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
    print("========== RAW AI REPLY ==========")
    print(reply)
    print("===================================")

    print("\n========== AI REPLY ==========")
    print(reply)

    # =====================================
    # CHECK FOR COMPLETED BOOKING
    # =====================================

    if "[BOOKING_READY]" in reply:

        booking_json = reply.split(
            "[BOOKING_READY]",
            1
        )[1].strip()

        booking_data = json.loads(
            booking_json
        )

        print(
            "========== BOOKING DATA =========="
        )

        print(
            booking_data
            )

        # =====================================
        # DETERMINE BOOKING RECIPIENT
        # =====================================

        booking_for = booking_data.get(
            "booking_for",
            "self"
        )

        booking_customer_name = booking_data.get(
            "customer_name"
        )

        if booking_for == "self":

            # Use the name collected by the AI.
            # If it is missing, fall back to the saved customer name.
            if not booking_customer_name:
                booking_customer_name = customer.name

            print(
                "========== BOOKING FOR SELF =========="
            )

            print(
                "WHATSAPP CUSTOMER:",
                customer.name
            )

            print(
                "BOOKING CUSTOMER NAME:",
                booking_customer_name
            )

        else:

            # For another person, the AI must provide
            # the recipient's name.
            if not booking_customer_name:
                print(
                    "ERROR: Booking recipient name is missing."
                )

                response.message(
                    "Sure. What is the name of the person the appointment is for?"
                )

                return Response(
                    str(response),
                    mimetype="text/xml"
                )

                print(
                    "========== BOOKING FOR ANOTHER PERSON =========="
                )

                print(
                    "WHATSAPP CUSTOMER:",
                    customer.name
                )

                print(
                    "SERVICE RECIPIENT:",
                    booking_customer_name
                )
        # =====================================
        # VALIDATE RECIPIENT NAME
        # =====================================

        if not booking_customer_name:

            print(
                "BOOKING ERROR: Missing customer name"
            )

            reply = (
                "What is the name of the person "
                "the appointment is for?"
            )

        else:

            # =====================================
            # FIND SERVICE
            # =====================================

            service = Service.query.filter_by(
                business_id=business.id,
                name=booking_data["service"]
            ).first()

            if not service:

                print(
                    "BOOKING ERROR: Service not found:",
                    booking_data["service"]
                )

                reply = (
                    f"Sorry, I couldn't find the service "
                    f"'{booking_data['service']}'."
                )

            else:

                # =====================================
                # BUILD REQUESTED TIME
                # =====================================

                requested_start = datetime.strptime(
                    f"{booking_data['date']} "
                    f"{booking_data['time']}",
                    "%Y-%m-%d %H:%M"
                )

                # =====================================
                # CALCULATE SERVICE DURATION
                # =====================================

                duration_text = str(
                    service.duration
                ).lower()

                duration_match = re.search(
                    r"\d+",
                    duration_text
                )

                duration_hours = (
                    int(duration_match.group())
                    if duration_match
                    else 1
                )

                requested_end = (
                    requested_start
                    + timedelta(
                        hours=duration_hours
                    )
                )

                # =====================================
                # CHECK BUSINESS HOURS
                # =====================================

                within_hours, hours_error = check_business_hours(
                    business.opening_hours,
                    requested_start,
                    requested_end
                )

                if not within_hours:

                    print(
                        "========== BUSINESS HOURS CONFLICT =========="
                    )

                    reply = hours_error

                else:

                    # =====================================
                    # CHECK FOR DOUBLE BOOKING
                    # =====================================

                    conflict = False

                    existing_appointments = (
                        Appointment.query.filter_by(
                            business_id=business.id,
                            status="confirmed"
                        ).all()
                    )

                    for existing in existing_appointments:

                        existing_start = datetime.strptime(
                            existing.appointment_time,
                            "%Y-%m-%d %H:%M"
                        )

                        existing_service = (
                            Service.query.filter_by(
                                business_id=business.id,
                                name=existing.service
                            ).first()
                        )

                        if existing_service:

                            existing_duration_match = re.search(
                                r"\d+",
                                str(
                                    existing_service.duration
                                ).lower()
                            )

                            existing_duration_hours = (
                                int(
                                    existing_duration_match.group()
                                )
                                if existing_duration_match
                                else 1
                            )

                        else:

                            existing_duration_hours = 1

                        existing_end = (
                            existing_start
                            + timedelta(
                                hours=existing_duration_hours
                            )
                        )

                        if (
                            requested_start < existing_end
                            and requested_end > existing_start
                        ):

                            conflict = True
                            break

                    # =====================================
                    # HANDLE BOOKING CONFLICT
                    # =====================================

                    if conflict:

                        print(
                            "========== BOOKING CONFLICT =========="
                        )

                        reply = (
                            f"Sorry, {booking_data['date']} at "
                            f"{booking_data['time']} is already booked. "
                            "Please choose another time."
                        )

                    else:

                        # =====================================
                        # CREATE APPOINTMENT
                        # =====================================

                        appointment = Appointment(
                            business_id=business.id,
                            customer_name=booking_customer_name,
                            customer_phone=customer_phone,
                            service=service.name,
                            amount=service.price,
                            appointment_time=(
                                f"{booking_data['date']} "
                                f"{booking_data['time']}"
                            ),
                            status="confirmed"
                        )

                        db.session.add(
                            appointment
                        )

                        db.session.commit()

                        # =====================================
                        # UPDATE CUSTOMER NAME ONLY FOR SELF
                        # =====================================

                        if booking_for == "self":

                            customer = update_customer_name(
                                customer,
                                booking_customer_name
                            )

                            print(
                                "========== CUSTOMER UPDATED =========="
                            )

                            print(
                                "CUSTOMER ID:",
                                customer.id
                            )

                            print(
                                "CUSTOMER NAME:",
                                customer.name
                            )

                        else:

                            print(
                                "========== CUSTOMER NOT UPDATED =========="
                            )

                            print(
                                "WhatsApp customer remains:",
                                customer.name
                            )

                            print(
                                "Appointment recipient:",
                                booking_customer_name
                            )

                        print(
                            "========== APPOINTMENT CREATED =========="
                        )

                        print(
                            "APPOINTMENT ID:",
                            appointment.id
                        )

                        print(
                            "APPOINTMENT CUSTOMER NAME:",
                            appointment.customer_name
                        )

                        print(
                            "APPOINTMENT PHONE:",
                            appointment.customer_phone
                        )

                        print(
                            "APPOINTMENT SERVICE:",
                            appointment.service
                        )

                        print(
                            "APPOINTMENT TIME:",
                            appointment.appointment_time
                        )
    # =====================================
    # CHECK FOR RESCHEDULE REQUEST
    # =====================================

    if "[RESCHEDULE_REQUEST]" in reply:

        reply = process_reschedule(
            reply=reply,
            business=business,
            customer_phone=customer_phone
        )

    # =====================================
    # REMOVE INTERNAL BOOKING MARKER
    # =====================================

    if "[BOOKING_READY]" in reply:

        reply = reply.split(
            "[BOOKING_READY]",
            1
        )[0].strip()

    # =====================================
    # SAVE AI RESPONSE
    # =====================================

    ai_chat = Conversation(
        business_id=business.id,
        customer_phone=customer_phone,
        role="assistant",
        message=reply
    )

    db.session.add(
        ai_chat
    )

    db.session.commit()

    # =====================================
    # SEND WHATSAPP RESPONSE
    # =====================================

    print("========== FINAL WHATSAPP REPLY ==========")
    print(reply)

    response.message(
        reply
    )

    twiml_response = str(response)

    print("========== TWILIO TWIML RESPONSE ==========")
    print(twiml_response)
    print("============================================")

    return Response(
        twiml_response,
        mimetype="text/xml"
    )