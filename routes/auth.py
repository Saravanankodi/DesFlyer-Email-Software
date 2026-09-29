from flask import Blueprint, render_template, request, redirect, url_for, flash

from flask_login import login_user, logout_user, current_user

from models import db
from models.user import User


auth_bp = Blueprint(
    "auth",
    __name__,
    url_prefix="/auth"
)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():

    if current_user.is_authenticated:
        return redirect(url_for("dashboard.dashboard"))


    if request.method == "POST":

        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not email or not password:
            flash("Please enter email and password.", "error")
            return render_template("login.html")


        user = User.query.filter_by(email=email).first()


        if user and user.check_password(password):

            login_user(user)

                        
            return redirect(url_for("dashboard.dashboard"))


        flash("Invalid email or password.", "error")


    return render_template("login.html")


@auth_bp.route("/logout")
def logout():

    logout_user()

    return redirect(url_for("auth.login"))