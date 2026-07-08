from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    session,
    flash
)

from werkzeug.utils import secure_filename

from models import (
    db,
    Business,
    Service
)

import os
import uuid

services = Blueprint(
    "services",
    __name__
)

