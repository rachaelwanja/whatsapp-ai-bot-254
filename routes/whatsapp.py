from urllib import response
from datetime import datetime, timedelta
import json
import re

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
    print("========== INCOMING WHATSAPP ==========")
    print("CUSTOMER PHONE:", customer_phone)
    print("MESSAGE:", incoming_msg)
    
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
    # BUILD AI PROMPT
    # =====================================

    prompt = build_prompt(
        business=business,
        services_text=services_text,
        knowledge_text=knowledge_text
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

            service = Service.query.filter_by(
                business_id=business.id,
                name=booking_data["service"]
            ).first()

            if not service:

                print(
                    "BOOKING ERROR: Service not found:",
                    booking_data["service"]
                )

            else:

                # =====================================
                # CHECK FOR DOUBLE BOOKING
                # =====================================

                requested_start = datetime.strptime(
                    f"{booking_data['date']} {booking_data['time']}",
                    "%Y-%m-%d %H:%M"
                )

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
                    + timedelta(hours=duration_hours)
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

                    conflict = False

                    existing_appointments = Appointment.query.filter_by(
                        business_id=business.id,
                        status="confirmed"
                    ).all()

                    for existing in existing_appointments:

                        existing_start = datetime.strptime(
                            existing.appointment_time,
                            "%Y-%m-%d %H:%M"
                        )

                        existing_service = Service.query.filter_by(
                            business_id=business.id,
                            name=existing.service
                        ).first()

                        if existing_service:

                            existing_duration_match = re.search(
                                r"\d+",
                                str(existing_service.duration).lower()
                            )

                            existing_duration_hours = (
                                int(existing_duration_match.group())
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

                        appointment = Appointment(
                            business_id=business.id,
                            customer_name=booking_data["customer_name"],
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

                        print(
                            "========== APPOINTMENT CREATED =========="
                        )

                        print(
                            appointment.id
                        )
    # =====================================
    # SAVE AI RESPONSE
    # =====================================

    ai_chat = Conversation(
        business_id=business.id,
        customer_phone=customer_phone,
        role="assistant",
        message=reply
    )

    # =====================================
    # SEND WHATSAPP RESPONSE
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
    # CHECK FOR CANCELLATION REQUEST
    # =====================================

    if "[CANCEL_REQUEST]" in reply:

        try:

            cancel_json = reply.split(
                "[CANCEL_REQUEST]",
                1
            )[1].strip()

            cancel_data = json.loads(
                cancel_json
            )

            cancel_time = datetime.strptime(
                f"{cancel_data['date']} {cancel_data['time']}",
                "%Y-%m-%d %H:%M"
            )

            appointment = Appointment.query.filter_by(
                business_id=business.id,
                customer_phone=customer_phone,
                appointment_time=cancel_time.strftime(
                    "%Y-%m-%d %H:%M"
                ),
                status="confirmed"
            ).first()

            if appointment:

                appointment.status = "cancelled"

                db.session.commit()

                reply = (
                    f"Your appointment for "
                    f"{appointment.service} on "
                    f"{cancel_data['date']} at "
                    f"{cancel_data['time']} "
                    "has been cancelled successfully."
                )

                print(
                    "========== APPOINTMENT CANCELLED =========="
                )

                print(
                    appointment.id
                )

            else:

                reply = (
                    "I couldn't find a confirmed appointment "
                    "for that date and time. Please check the "
                    "details and try again."
                )

        except Exception as e:

            print(
                "CANCELLATION ERROR:",
                e
            )

            reply = (
                "Sorry, I couldn't process the cancellation. "
                "Please check the appointment details and try again."
            )
    # =====================================
    # CHECK FOR RESCHEDULE REQUEST
    # =====================================

    if "[RESCHEDULE_REQUEST]" in reply:

        try:

            reschedule_json = reply.split(
                "[RESCHEDULE_REQUEST]",
                1
            )[1].strip()

            reschedule_data = json.loads(
                reschedule_json
            )

            old_time = datetime.strptime(
                f"{reschedule_data['old_date']} "
                f"{reschedule_data['old_time']}",
                "%Y-%m-%d %H:%M"
            )

            new_start = datetime.strptime(
                f"{reschedule_data['new_date']} "
                f"{reschedule_data['new_time']}",
                "%Y-%m-%d %H:%M"
            )

            # -------------------------------------
            # FIND EXISTING APPOINTMENT
            # -------------------------------------

            appointment = Appointment.query.filter_by(
                business_id=business.id,
                customer_phone=customer_phone,
                appointment_time=old_time.strftime(
                    "%Y-%m-%d %H:%M"
                ),
                status="confirmed"
            ).first()

            if not appointment:

                reply = (
                    "I couldn't find a confirmed appointment "
                    "for that date and time. Please check the "
                    "details and try again."
                )

            else:

                # -------------------------------------
                # FIND SERVICE
                # -------------------------------------

                service = Service.query.filter_by(
                    business_id=business.id,
                    name=appointment.service
                ).first()

                if service:

                    duration_match = re.search(
                        r"\d+",
                        str(service.duration).lower()
                    )

                    duration_hours = (
                        int(duration_match.group())
                        if duration_match
                        else 1
                    )

                else:

                    duration_hours = 1

                new_end = (
                    new_start
                    + timedelta(hours=duration_hours)
                )

                # -------------------------------------
                # CHECK BUSINESS HOURS
                # -------------------------------------

                within_hours, hours_error = (
                    check_business_hours(
                        business.opening_hours,
                        new_start,
                        new_end
                    )
                )

                if not within_hours:

                    reply = hours_error

                else:

                    # -------------------------------------
                    # CHECK FOR DOUBLE BOOKING
                    # -------------------------------------

                    conflict = False

                    existing_appointments = (
                        Appointment.query.filter_by(
                            business_id=business.id,
                            status="confirmed"
                        ).all()
                    )

                    for existing in existing_appointments:

                        # Ignore the appointment being moved
                        if existing.id == appointment.id:
                            continue

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
                                str(existing_service.duration).lower()
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
                            new_start < existing_end
                            and new_end > existing_start
                        ):

                            conflict = True
                            break

                    if conflict:

                        reply = (
                            f"Sorry, {reschedule_data['new_date']} "
                            f"at {reschedule_data['new_time']} "
                            "is already booked. Please choose "
                            "another time."
                        )

                    else:

                        appointment.appointment_time = (
                            new_start.strftime(
                                "%Y-%m-%d %H:%M"
                            )
                        )

                        db.session.commit()

                        reply = (
                            f"Your appointment for "
                            f"{appointment.service} has been "
                            f"rescheduled successfully to "
                            f"{reschedule_data['new_date']} at "
                            f"{reschedule_data['new_time']}."
                        )

                        print(
                            "========== APPOINTMENT RESCHEDULED =========="
                        )

                        print(
                            appointment.id
                        )

        except Exception as e:

            print(
                "RESCHEDULE ERROR:",
                e
            )

            reply = (
                "Sorry, I couldn't process the rescheduling. "
                "Please check the appointment details and try again."
            )
    # =====================================
    # SEND WHATSAPP RESPONSE
    # =====================================

    response.message(reply)

    return Response(
        str(response),
        mimetype="text/xml"
    )