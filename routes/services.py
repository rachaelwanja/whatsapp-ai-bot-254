from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    session,
    flash,
    current_app
)

from werkzeug.utils import secure_filename

import os
import uuid

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
# SERVICES PAGE
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

@services.route(
    "/add-service",
    methods=["POST"]
)
def add_service():

    # =========================================
    # CHECK LOGIN
    # =========================================

    if "business_id" not in session:
        return redirect("/login")

    business_id = session["business_id"]

    # =========================================
    # GET FORM DATA
    # =========================================

    name = request.form.get(
        "name",
        ""
    ).strip()

    category = request.form.get(
        "category",
        "Other"
    ).strip()

    duration = request.form.get(
        "duration",
        ""
    ).strip()

    try:
        price = int(
            request.form.get(
                "price",
                0
            ) or 0
        )
    except ValueError:
        price = 0

    try:
        deposit = int(
            request.form.get(
                "deposit",
                0
            ) or 0
        )
    except ValueError:
        deposit = 0

    available = (
        "available"
        in request.form
    )

    # =========================================
    # IMAGE
    # =========================================

    image_name = ""

    image = request.files.get("image")

    print(
        "IMAGE RECEIVED:",
        image
    )

    print(
        "IMAGE FILENAME:",
        image.filename
        if image
        else "NO IMAGE"
    )

    # =========================================
    # HANDLE IMAGE UPLOAD
    # =========================================

    if image and image.filename:

        filename = secure_filename(
            image.filename
        )

        # Make sure filename is valid
        if not filename:

            flash(
                "Invalid image filename."
            )

            return redirect("/services")

        # Make sure image has extension
        if "." not in filename:

            flash(
                "Please upload a valid image."
            )

            return redirect("/services")

        extension = filename.rsplit(
            ".",
            1
        )[1].lower()

        # Allowed image types
        allowed_extensions = {
            "jpg",
            "jpeg",
            "png",
            "webp"
        }

        if extension not in allowed_extensions:

            flash(
                "Please upload a JPG, JPEG, PNG, or WEBP image."
            )

            return redirect("/services")

        # =========================================
        # CREATE UNIQUE FILE NAME
        # =========================================

        image_name = (
            str(uuid.uuid4())
            + "."
            + extension
        )

        # =========================================
        # GET ABSOLUTE UPLOAD FOLDER
        # =========================================

        upload_folder = current_app.config[
            "UPLOAD_FOLDER"
        ]

        # =========================================
        # MAKE SURE UPLOAD FOLDER EXISTS
        # =========================================

        try:

            os.makedirs(
                upload_folder,
                exist_ok=True
            )

        except FileExistsError:

            # Windows can raise this when something
            # already exists at the path.

            if not os.path.isdir(
                upload_folder
            ):

                flash(
                    "Upload folder is not available."
                )

                return redirect("/services")

        # =========================================
        # IMAGE PATH
        # =========================================

        image_path = os.path.join(
            upload_folder,
            image_name
        )

        print(
            "UPLOAD FOLDER:",
            upload_folder
        )

        print(
            "UPLOAD FOLDER EXISTS BEFORE SAVE:",
            os.path.isdir(upload_folder)
        )

        print(
            "IMAGE PATH:",
            image_path
        )

        # =========================================
        # SAVE IMAGE
        # =========================================

        try:

            image.save(
                image_path
            )

        except Exception as e:

            print(
                "IMAGE SAVE ERROR:",
                e
            )

            flash(
                "The image could not be uploaded."
            )

            return redirect("/services")

        # =========================================
        # VERIFY IMAGE
        # =========================================

        print(
            "IMAGE EXISTS AFTER SAVE:",
            os.path.exists(image_path)
        )

        # If somehow the image wasn't saved
        if not os.path.exists(
            image_path
        ):

            flash(
                "Image upload failed."
            )

            return redirect("/services")

    # =========================================
    # CREATE SERVICE
    # =========================================

    service = Service(

        business_id=business_id,

        name=name,

        category=category,

        price=price,

        duration=duration,

        deposit=deposit,

        image=image_name,

        available=available
    )

    # =========================================
    # SAVE SERVICE TO DATABASE
    # =========================================

    try:

        db.session.add(
            service
        )

        db.session.commit()

    except Exception as e:

        db.session.rollback()

        print(
            "SERVICE SAVE ERROR:",
            e
        )

        # If database save fails after image upload,
        # remove the uploaded image so we don't leave
        # an orphaned file.

        if image_name:

            image_path = os.path.join(
                current_app.config[
                    "UPLOAD_FOLDER"
                ],
                image_name
            )

            if os.path.exists(
                image_path
            ):

                try:
                    os.remove(
                        image_path
                    )
                except Exception:
                    pass

        flash(
            "Could not save the service."
        )

        return redirect("/services")

    # =========================================
    # SUCCESS
    # =========================================

    flash(
        "Service added successfully!"
    )

    return redirect("/services")

# =========================================
# EDIT SERVICE
# =========================================

@services.route(
    "/edit-service/<int:id>",
    methods=["GET", "POST"]
)
def edit_service(id):

    if "business_id" not in session:
        return redirect("/login")

    service = Service.query.filter_by(
        id=id,
        business_id=session["business_id"]
    ).first_or_404()

    if request.method == "POST":

        service.name = request.form.get(
            "name",
            ""
        ).strip()

        service.category = request.form.get(
            "category",
            "Other"
        ).strip()

        service.price = int(
            request.form.get(
                "price"
            ) or 0
        )

        service.duration = request.form.get(
            "duration",
            ""
        ).strip()

        service.deposit = int(
            request.form.get(
                "deposit"
            ) or 0
        )

        service.available = (
            "available"
            in request.form
        )

        db.session.commit()

        flash(
            "Service updated successfully!"
        )

        return redirect(
            "/services"
        )

    return render_template(
        "edit_service.html",
        service=service
    )


# =========================================
# DELETE SERVICE
# =========================================

@services.route(
    "/delete-service/<int:id>"
)
def delete_service(id):

    if "business_id" not in session:
        return redirect("/login")

    service = Service.query.filter_by(
        id=id,
        business_id=session["business_id"]
    ).first_or_404()

    # =========================================
    # DELETE IMAGE
    # =========================================

    if service.image:

        image_path = os.path.join(
            current_app.config["UPLOAD_FOLDER"],
            service.image
        )

        if os.path.isfile(image_path):

            try:

                os.remove(
                    image_path
                )

            except Exception as e:

                print(
                    "IMAGE DELETE ERROR:",
                    e
                )

    # =========================================
    # DELETE SERVICE
    # =========================================

    db.session.delete(
        service
    )

    db.session.commit()

    flash(
        "Service deleted successfully!"
    )

    return redirect(
        "/services"
    )
# =========================================
# DEBUG SERVICES
# =========================================

@services.route("/debug-services")
def debug_services():

    all_services = Service.query.all()

    output = ""

    for service in all_services:

        output += f"""
        <hr>
        ID: {service.id}<br>
        Business ID: {service.business_id}<br>
        Name: {service.name}<br>
        Category: {service.category}<br>
        Price: {service.price}<br>
        Duration: {service.duration}<br>
        Deposit: {service.deposit}<br>
        Image: {service.image}<br>
        Available: {service.available}<br>
        """

    return output or "NO SERVICES FOUND"