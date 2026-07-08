from flask import (
    Blueprint,
    render_template,
    redirect,
    session
    flash,
    current_app
)

from models import (
    Business,
    Service
)

services = Blueprint(
    "services",
    __name__
)

# =========================================
# SERVICES
# =========================================

@services.route("/services")
def services_page():

    if "business_id" not in session:
        return redirect("/login")

    business_id = session["business_id"]

    business = Business.query.get(
        business_id
    )

    all_services = Service.query.filter_by(
        business_id=business_id
    ).all()

    return render_template(
        "services.html",
        business=business,
        services=all_services
    )

# =========================================
# ADD SERVICE
# =========================================

@services.route("/add-service", methods=["POST"])
def add_service():

    if "business_id" not in session:
        return redirect("/login")

    image_name = ""

    image = request.files.get("image")

    if image and image.filename != "":

        filename = secure_filename(
            image.filename
        )

        extension = filename.rsplit(
            ".", 1
        )[1].lower()

        image_name = (
            str(uuid.uuid4())
            + "."
            + extension
        )

        image.save(
            os.path.join(
                current_app.config["UPLOAD_FOLDER"],
                image_name
            )
        )

    service = Service(

        business_id=session["business_id"],

        name=request.form["name"],

        category=request.form["category"],

        price=int(request.form["price"]),

        duration=request.form["duration"],

        deposit=int(
            request.form.get("deposit", 0)
        ),

        image=image_name,

        available="available" in request.form

    )

    db.session.add(service)

    db.session.commit()

    flash(
        "Service added successfully!"
    )

    return redirect("/services")
