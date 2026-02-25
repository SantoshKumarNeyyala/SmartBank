from flask import Blueprint, render_template, request, redirect, flash, session, url_for
from models.user_model import UserModel
from database.connection import DatabaseConnection
from extension import limiter
from utils.security import hash_password, verify_password
from services.audit_service import AuditService
from utils.request_meta import get_request_meta
from services.audit_service import AuditService
from utils.request_meta import get_request_meta

auth = Blueprint("auth", __name__)


# ================= REGISTER =================
@auth.route("/register", methods=["GET", "POST"])
def register():
    """
    Handles user registration.
    Validates input, checks for duplicate email,
    and creates new user record.
    """
    if request.method == "POST":
        full_name: str = (request.form.get("full_name") or "").strip()
        email: str = (request.form.get("email") or "").strip().lower()
        password: str = request.form.get("password") or ""

        if not full_name or not email or not password:
            flash("All fields are required!", "danger")
            return redirect(url_for("auth.register"))

        if UserModel.get_user_by_email(email):
            flash("Email already registered!", "danger")
            return redirect(url_for("auth.register"))

        # Hash password before saving
        hashed_password = hash_password(password)

        success = UserModel.create_user(full_name, email, hashed_password)
        if success:
            flash("Registration successful! Please login.", "success")
            return redirect(url_for("auth.login"))

        flash("Something went wrong!", "danger")
        return redirect(url_for("auth.register"))

    return render_template("register.html")


# ================= LOGIN =================
@auth.route("/login", methods=["GET", "POST"])
@limiter.limit("5 per minute")
def login():
    """
    Handles user login.
    Includes:
    - Account lock after 3 failed attempts
    - Rate limiting
    - Session creation
    """
    if request.method == "POST":
        email: str = (request.form.get("email") or "").strip().lower()
        password: str = request.form.get("password") or ""

        user = UserModel.get_user_by_email(email)
        if not user:
            flash("Invalid email or password", "danger")
            ip, ua = get_request_meta()
            AuditService.log(
                user_id=user_id,
                action="LOGIN_FAIL",
                description=f"Wrong password attempt. Count={failed_attempts}",
                ip=ip,
                user_agent=ua
            )
            return redirect(url_for("auth.login"))

        user_id = user[0]
        full_name = user[1]
        stored_password = user[3]
        failed_attempts = user[4]
        is_locked = user[5]
        role = user[6]

        if is_locked:
            flash("Account is locked due to multiple failed attempts!", "danger")
            return redirect(url_for("auth.login"))

        # Verify password using abstraction layer
        if verify_password(stored_password, password):

            _reset_failed_attempts(user_id)

            session["user_id"] = user_id
            session["user_name"] = full_name
            session["role"] = role

            flash("Login successful!", "success")
            ip, ua = get_request_meta()
            AuditService.log(
                user_id=user_id,
                action="LOGIN_SUCCESS",
                description="User logged in successfully",
                ip=ip,
                user_agent=ua
            )
            return redirect(url_for("bank.dashboard"))

        # Wrong password handling
        _increment_failed_attempts(user_id, failed_attempts)

        return redirect(url_for("auth.login"))

    return render_template("login.html")


# ================= LOGOUT =================
@auth.route("/logout")
def logout():
    """Clears session and logs user out."""

    ip, ua = get_request_meta()
    AuditService.log(
        user_id=session.get("user_id"),
        action="LOGOUT",
        description="User logged out",
        ip=ip,
        user_agent=ua
        )
    session.clear()
    flash("Logged out successfully!", "info")
    return redirect(url_for("auth.login"))


# ================= HELPER FUNCTIONS =================

def _reset_failed_attempts(user_id: int) -> None:
    """Reset failed login attempts after successful login."""
    conn = DatabaseConnection.get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE users
        SET failed_login_attempts = 0,
            is_locked = 0
        WHERE id = ?
    """, (user_id,))
    conn.commit()
    cursor.close()
    conn.close()


def _increment_failed_attempts(user_id: int, failed_attempts: int) -> None:
    """Increment failed login attempts and lock account if needed."""
    failed_attempts += 1

    conn = DatabaseConnection.get_connection()
    cursor = conn.cursor()

    if failed_attempts >= 3:
        cursor.execute("""
            UPDATE users
            SET failed_login_attempts = ?, is_locked = 1
            WHERE id = ?
        """, (failed_attempts, user_id))
        flash("Account locked after 3 failed attempts!", "danger")
    else:
        cursor.execute("""
            UPDATE users
            SET failed_login_attempts = ?
            WHERE id = ?
        """, (failed_attempts, user_id))
        flash("Invalid password!", "danger")

    conn.commit()
    cursor.close()
    conn.close()