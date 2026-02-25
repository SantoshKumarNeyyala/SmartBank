from flask import Blueprint, render_template, session, redirect, url_for, request, flash, send_file
from extension import limiter
from utils.validators import parse_positive_amount
from utils.decorators import login_required, account_required
from utils.request_meta import get_request_meta

from services.bank_service import BankService
from services.analytics_service import AnalyticsService
from services.transfer_service import TransferService
from services.account_service import AccountService
from services.otp_service import OTPService
from services.fraud_service import FraudService
from services.audit_service import AuditService

from database.connection import DatabaseConnection

from reportlab.pdfgen import canvas
from flask import send_file
from io import BytesIO
import uuid


bank = Blueprint("bank", __name__)


# =========================================================
# DASHBOARD
# =========================================================
@bank.route("/dashboard")
@login_required
def dashboard():
    user_id = session["user_id"]
    accounts = AccountService.get_user_accounts(user_id)

    if accounts and "account_id" not in session:
        session["account_id"] = accounts[0][0]

    account_id = session.get("account_id")
    balance = BankService.get_balance(account_id) if account_id else 0

    return render_template(
        "dashboard.html",
        name=session.get("user_name"),
        accounts=accounts,
        selected_account_id=account_id,
        balance=balance
    )


@bank.route("/select-account/<int:account_id>")
@login_required
def select_account(account_id):
    user_id = session["user_id"]
    acct = AccountService.get_account_by_id(account_id, user_id)

    if not acct:
        flash("Invalid account selection.", "danger")
        return redirect(url_for("bank.dashboard"))

    session["account_id"] = account_id
    flash("Account selected successfully.", "success")
    return redirect(url_for("bank.dashboard"))


# =========================================================
# ACCOUNT MANAGEMENT
# =========================================================
@bank.route("/accounts/new", methods=["GET", "POST"])
@login_required
def create_account():
    if request.method == "POST":
        try:
            acc_type = request.form.get("account_type")
            acc_no = AccountService.create_account(session["user_id"], acc_type)

            ip, ua = get_request_meta()
            AuditService.log(
                user_id=session["user_id"],
                action="CREATE_ACCOUNT",
                description=f"Created account {acc_no}",
                ip=ip,
                user_agent=ua
            )

            flash(f"Account created: {acc_no}", "success")
            return redirect(url_for("bank.dashboard"))

        except Exception as e:
            flash(str(e), "danger")

    return render_template("create_account.html")


@bank.route("/accounts/close/<int:account_id>")
@login_required
def close_account(account_id):
    try:
        AccountService.close_account(session["user_id"], account_id)

        if session.get("account_id") == account_id:
            session.pop("account_id", None)

        ip, ua = get_request_meta()
        AuditService.log(
            user_id=session["user_id"],
            account_id=account_id,
            action="CLOSE_ACCOUNT",
            description="Account closed",
            ip=ip,
            user_agent=ua
        )

        flash("Account closed successfully.", "success")

    except Exception as e:
        flash(str(e), "danger")

    return redirect(url_for("bank.dashboard"))


# =========================================================
# DEPOSIT
# =========================================================
@bank.route("/deposit", methods=["GET", "POST"])
@login_required
@account_required
def deposit():
    if request.method == "POST":
        try:
            amount = parse_positive_amount(request.form.get("amount"))
            account_id = session["account_id"]

            BankService.deposit(
                session["user_id"],
                account_id,
                amount,
                request.form.get("idempotency_key")
            )

            ip, ua = get_request_meta()
            AuditService.log(
                user_id=session["user_id"],
                account_id=account_id,
                action="DEPOSIT",
                description=f"Deposit ₹{amount}",
                ip=ip,
                user_agent=ua
            )

            flash("Deposit successful!", "success")
            return redirect(url_for("bank.dashboard"))

        except Exception as e:
            flash(str(e), "danger")

    return render_template("deposit.html", idempotency_key=str(uuid.uuid4()))


# =========================================================
# WITHDRAW
# =========================================================
@bank.route("/withdraw", methods=["GET", "POST"])
@login_required
@account_required
def withdraw():
    if request.method == "POST":
        try:
            amount = parse_positive_amount(request.form.get("amount"))
            account_id = session["account_id"]

            BankService.withdraw(
                session["user_id"],
                account_id,
                amount,
                request.form.get("idempotency_key")
            )

            ip, ua = get_request_meta()
            AuditService.log(
                user_id=session["user_id"],
                account_id=account_id,
                action="WITHDRAW",
                description=f"Withdraw ₹{amount}",
                ip=ip,
                user_agent=ua
            )

            flash("Withdraw successful!", "success")
            return redirect(url_for("bank.dashboard"))

        except Exception as e:
            flash(str(e), "danger")

    return render_template("withdraw.html", idempotency_key=str(uuid.uuid4()))


# =========================================================
# TRANSACTIONS
# =========================================================
@bank.route("/transactions")
@login_required
@account_required
def transactions():
    txns = BankService.get_transactions(session["user_id"], session["account_id"])
    return render_template("transactions.html", txns=txns)


# =========================================================
# TRANSFER (OTP + FRAUD)
# =========================================================
@bank.route("/transfer", methods=["GET", "POST"])
@login_required
@account_required
@limiter.limit("10 per minute")
def transfer():
    if request.method == "POST":
        try:
            from_account_id = session["account_id"]
            to_account_number = (request.form.get("to_account_number") or "").strip().upper()
            amount = parse_positive_amount(request.form.get("amount"))
            idem = request.form.get("idempotency_key")

            if not to_account_number:
                raise ValueError("Receiver account number is required.")

            # Lookup receiver account
            conn = DatabaseConnection.get_connection()
            cur = conn.cursor()
            cur.execute(
                "SELECT id FROM accounts WHERE account_number = ? AND status='active'",
                (to_account_number,)
            )
            rec = cur.fetchone()
            cur.close()
            conn.close()

            if not rec:
                raise ValueError("Receiver account not found.")

            to_account_id = int(rec[0])

            risk_score = FraudService.calculate_risk(from_account_id, to_account_id, amount)
            decision = FraudService.decision(risk_score)

            if decision == "block":
                raise ValueError(f"High fraud risk detected (Score: {risk_score}). Transfer blocked.")

            session["pending_transfer"] = {
                "from_account_id": from_account_id,
                "to_account_number": to_account_number,
                "amount": float(amount),
                "idempotency_key": idem,
                "risk_decision": decision
            }

            session.pop("stepup_done", None)

            otp = OTPService.create_otp_session(session)
            print("OTP:", otp)

            flash("OTP sent successfully.", "info")
            return redirect(url_for("bank.verify_otp"))

        except Exception as e:
            flash(str(e), "danger")

    return render_template("transfer.html", idempotency_key=str(uuid.uuid4()))


@bank.route("/verify-otp", methods=["GET", "POST"])
@login_required
def verify_otp():
    if request.method == "POST":
        entered_otp = request.form.get("otp")
        is_valid, message = OTPService.verify_otp(session, entered_otp)

        if not is_valid:
            flash(message, "danger")
            return redirect(url_for("bank.verify_otp"))

        data = session.get("pending_transfer")
        if not data:
            flash("Transfer session expired.", "danger")
            return redirect(url_for("bank.dashboard"))

        if data["risk_decision"] == "stepup" and not session.get("stepup_done"):
            session["stepup_done"] = True
            OTPService.create_otp_session(session)
            flash("Step-up OTP required.", "info")
            return redirect(url_for("bank.verify_otp"))

        data = session.pop("pending_transfer")
        session.pop("stepup_done", None)

        ref = TransferService.transfer(
            session["user_id"],
            data["from_account_id"],
            data["to_account_number"],
            data["amount"],
            data["idempotency_key"]
        )

        ip, ua = get_request_meta()
        AuditService.log(
            user_id=session["user_id"],
            account_id=data["from_account_id"],
            action="TRANSFER",
            description=f"Transfer ₹{data['amount']} to {data['to_account_number']} Ref={ref}",
            ip=ip,
            user_agent=ua
        )

        flash(f"Transfer successful! Ref: {ref}", "success")
        return redirect(url_for("bank.dashboard"))

    return render_template("verify_otp.html")


# =========================================================
# ADMIN PAGES
# =========================================================
@bank.route("/admin/fraud")
@login_required
def admin_fraud_dashboard():
    conn = DatabaseConnection.get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT reference_id, from_account_id, to_account_id,
               amount, risk_score, status, created_at
        FROM transfers
        ORDER BY created_at DESC
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return render_template("admin_fraud.html", transfers=rows)


@bank.route("/admin/audit")
@login_required
def admin_audit():
    logs = AuditService.latest(300)
    return render_template("admin_audit.html", logs=logs)


# =========================================================
# ANALYTICS PAGE
# =========================================================
@bank.route("/analytics")
@login_required
@account_required
def analytics():
    #This loads the page UI (charts fetch data from /api/analytics/last7days)
    return render_template("analytics.html")

# =========================================================
# ANALYTICS API
# =========================================================
@bank.route("/api/analytics/last7days")
@login_required
@account_required
def api_analytics_last7days():
    conn = DatabaseConnection.get_connection()
    cur = conn.cursor()

    cur.execute("""
      SELECT CAST(created_at AS DATE),
             SUM(CASE WHEN transaction_type='deposit' THEN amount ELSE 0 END),
             SUM(CASE WHEN transaction_type='withdraw' THEN amount ELSE 0 END)
      FROM transactions
      WHERE account_id = ?
        AND created_at >= DATEADD(DAY, -7, GETDATE())
      GROUP BY CAST(created_at AS DATE)
      ORDER BY 1
    """, (session["account_id"],))

    rows = cur.fetchall()
    cur.close()
    conn.close()

    labels = [str(r[0]) for r in rows]
    deposits = [float(r[1] or 0) for r in rows]
    withdraws = [float(r[2] or 0) for r in rows]

    return {"labels": labels, "deposits": deposits, "withdraws": withdraws}

# =========================================================
# EXPORT_CSV
# =========================================================
@bank.route("/export/csv", endpoint="export_csv")
@login_required
@account_required
def export_csv_route():
    rows = BankService.get_transactions(session["user_id"], session["account_id"])

    output = BytesIO()
    output.write(b"Type,Amount,Previous Balance,New Balance,Date\n")

    for r in rows:
        line = f"{r[0]},{float(r[1])},{float(r[2])},{float(r[3])},{str(r[4])}\n"
        output.write(line.encode("utf-8"))

    output.seek(0)

    return send_file(
        output,
        mimetype="text/csv",
        as_attachment=True,
        download_name="transactions.csv"
    )

# =========================================================
# EXPORT_JSON
# =========================================================

@bank.route("/export/json", endpoint="export_json")
@login_required
@account_required
def export_json_route():
    rows = BankService.get_transactions(session["user_id"], session["account_id"])

    data = []
    for r in rows:
        data.append({
            "type": r[0],
            "amount": float(r[1]),
            "previous_balance": float(r[2]),
            "new_balance": float(r[3]),
            "date": str(r[4])
        })

    import json
    output = BytesIO()
    output.write(json.dumps(data, indent=4).encode("utf-8"))
    output.seek(0)

    return send_file(
        output,
        mimetype="application/json",
        as_attachment=True,
        download_name="transactions.json"
    )

# =========================================================
# PDF STATEMENT
# =========================================================
@bank.route("/statement/pdf")
@login_required
@account_required
def statement_pdf():
    conn = DatabaseConnection.get_connection()
    cur = conn.cursor()

    cur.execute("""
      SELECT transaction_type, amount, previous_balance,
             new_balance, created_at
      FROM transactions
      WHERE account_id = ?
      ORDER BY created_at DESC
    """, (session["account_id"],))

    txns = cur.fetchall()
    cur.close()
    conn.close()

    buffer = BytesIO()
    c = canvas.Canvas(buffer)

    c.drawString(50, 800, "SmartBank Statement")
    y = 770

    for t in txns[:40]:
        c.drawString(50, y, f"{t[0]} | {float(t[1]):.2f} | {t[4]}")
        y -= 15

    c.save()
    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name="statement.pdf",
        mimetype="application/pdf"
    )

