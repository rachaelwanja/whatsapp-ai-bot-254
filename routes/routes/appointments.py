from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    session,
    flash
)

from models import (
    db,
    Business,
    Appointment
)

appointments = Blueprint(
    "appointments",
    __name__
)
