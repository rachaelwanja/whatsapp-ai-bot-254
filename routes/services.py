from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    session,
    flash,
    current_app
)

from models import (
    db,
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

# =========================================
# EDIT SERVICE
# =========================================

@services.route("/edit-service/<int:id>", methods=["GET", "POST"])
def edit_service(id):

    if "business_id" not in session:
        return redirect("/login")

    service = Service.query.filter_by(
        id=id,
        business_id=session["business_id"]
    ).first_or_404()

    if request.method == "POST":

        service.name = request.form["name"]
        service.category = request.form["category"]
        service.price = request.form["price"]
        service.duration = request.form["duration"]
        service.deposit = request.form["deposit"]

        service.available = (
            "available" in request.form
        )

        db.session.commit()

        flash(
            "Service updated successfully!"
        )

        return redirect("/services")

    return render_template(
        "edit_service.html",
        service=service
    )
