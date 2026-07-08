from flask import Blueprint, render_template, redirect, session

from models import Business, Appointment, Service, Payment

dashboard = Blueprint("dashboard", __name__)
