from functools import wraps
from flask import session, redirect, url_for, flash, request

def login_required(view_func):
    """
    Protect routes that require authentication.
    If user is not logged in, redirect to login page.
    """
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            flash("Please login first.", "info")
            return redirect(url_for("auth.login", next=request.path))
        return view_func(*args, **kwargs)
    return wrapper


def account_required(view_func):
    """
    Protect routes that require an active selected account in session.
    Useful for deposit/withdraw/transactions/statement, etc.
    """
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            flash("Please login first.", "info")
            return redirect(url_for("auth.login"))

        if "account_id" not in session or not session.get("account_id"):
            flash("Select an account first.", "danger")
            return redirect(url_for("bank.dashboard"))

        return view_func(*args, **kwargs)
    return wrapper