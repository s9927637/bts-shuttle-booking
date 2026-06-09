from flask import Blueprint, request, session, redirect, render_template
from werkzeug.security import check_password_hash
from app.models.admin import Admin

auth_bp = Blueprint("auth", __name__, url_prefix="/admin")


@auth_bp.route("/login", methods=["GET"])
def login_page():
    if session.get("admin_id"):
        return redirect("/admin/")
    return render_template("auth/login.html", error=None, username="")


@auth_bp.route("/login", methods=["POST"])
def login():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")

    admin = Admin.query.filter_by(username=username).first()

    if not admin or not check_password_hash(admin.password_hash, password):
        return render_template("auth/login.html", error="帳號或密碼錯誤", username=username)

    session.permanent = True
    session["admin_id"] = admin.id
    return redirect("/admin/")


@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect("/admin/login")
