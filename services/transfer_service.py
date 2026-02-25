from decimal import Decimal
import uuid

from database.connection import DatabaseConnection
from utils.money import to_decimal, quantize_money
from flask import current_app
from services.fraud_service import FraudService


class TransferService:

    # ================= LIMIT CHECK =================
    @staticmethod
    def _check_limits(cursor, from_account_id: int, amount: Decimal):

        if amount > MAX_TRANSFER_PER_TX:
            raise ValueError(
                f"Per transfer limit exceeded. Max ₹{MAX_TRANSFER_PER_TX:.2f}"
            )

        cursor.execute("""
            SELECT ISNULL(SUM(amount), 0)
            FROM transfers
            WHERE from_account_id = ?
              AND status = 'success'
              AND CAST(created_at AS DATE) = CAST(GETDATE() AS DATE)
        """, (from_account_id,))

        todays_total = cursor.fetchone()[0] or 0
        todays_total = quantize_money(to_decimal(todays_total))

        if todays_total + amount > MAX_TRANSFER_PER_DAY:
            raise ValueError(
                f"Daily transfer limit exceeded. "
                f"Today: ₹{todays_total:.2f}, "
                f"Max/day: ₹{MAX_TRANSFER_PER_DAY:.2f}"
            )


    # ================= MAIN TRANSFER =================
    @staticmethod
    def transfer(
        from_user_id: int,
        from_account_id: int,
        to_account_number: str,
        amount: Decimal,
        idempotency_key: str
    ):

        amount = quantize_money(to_decimal(amount))
        to_account_number = (to_account_number or "").strip().upper()

        if not to_account_number:
            raise ValueError("Receiver account number is required.")

        if not idempotency_key:
            raise ValueError("Missing idempotency key.")

        if amount <= 0:
            raise ValueError("Amount must be positive.")

        conn = DatabaseConnection.get_connection()
        cursor = conn.cursor()

        try:
            conn.autocommit = False

            # ================= IDEMPOTENCY CHECK =================
            cursor.execute("""
                SELECT reference_id
                FROM transfers
                WHERE idempotency_key = ?
            """, (idempotency_key,))

            existing = cursor.fetchone()
            if existing:
                return existing[0]

            # ================= LOCK SENDER =================
            cursor.execute("""
                SELECT id, balance, is_frozen
                FROM accounts WITH (UPDLOCK, ROWLOCK)
                WHERE id = ? AND user_id = ? AND status='active'
            """, (from_account_id, from_user_id))

            sender = cursor.fetchone()

            if not sender:
                raise ValueError("Sender account not found.")

            if sender[2] == 1:
                raise ValueError("Sender account is frozen. Transfer not allowed.")

            sender_balance = quantize_money(to_decimal(sender[1]))

            if amount > sender_balance:
                raise ValueError("Insufficient balance for transfer.")

            # ================= LOCK RECEIVER =================
            cursor.execute("""
                SELECT id, user_id, balance, is_frozen
                FROM accounts WITH (UPDLOCK, ROWLOCK)
                WHERE account_number = ? AND status='active'
            """, (to_account_number,))

            receiver = cursor.fetchone()

            if not receiver:
                raise ValueError("Receiver account not found.")

            if receiver[3] == 1:
                raise ValueError("Receiver account is frozen. Transfer not allowed.")

            to_account_id = int(receiver[0])
            to_user_id = int(receiver[1])
            receiver_balance = quantize_money(to_decimal(receiver[2]))

            if to_account_id == from_account_id:
                raise ValueError("Cannot transfer to the same account.")

            # ================= LIMIT CHECK =================
            TransferService._check_limits(cursor, from_account_id, amount)

            # ================= FRAUD CHECK =================
            risk_score = FraudService.calculate_risk(
                from_account_id,
                to_account_id,
                amount
            )

            decision = FraudService.decision(risk_score)

            if decision == "block":
                raise ValueError(
                    f"High fraud risk detected (Score: {risk_score}). Transfer blocked."
                )

            # ================= CALCULATE NEW BALANCES =================
            new_sender_balance = quantize_money(sender_balance - amount)
            new_receiver_balance = quantize_money(receiver_balance + amount)

            # ================= UPDATE BALANCES =================
            cursor.execute(
                "UPDATE accounts SET balance = ? WHERE id = ?",
                (new_sender_balance, from_account_id)
            )

            cursor.execute(
                "UPDATE accounts SET balance = ? WHERE id = ?",
                (new_receiver_balance, to_account_id)
            )

            # ================= CREATE REFERENCE =================
            ref = "TRX-" + uuid.uuid4().hex[:12].upper()

            # ================= INSERT TRANSFER =================
            cursor.execute("""
                INSERT INTO transfers
                (from_user_id, to_user_id,
                 from_account_id, to_account_id,
                 amount, status, reference_id,
                 idempotency_key, risk_score)
                VALUES (?, ?, ?, ?, ?, 'success', ?, ?, ?)
            """, (
                from_user_id,
                to_user_id,
                from_account_id,
                to_account_id,
                amount,
                ref,
                idempotency_key,
                risk_score
            ))

            # ================= INSERT TRANSACTIONS =================
            cursor.execute("""
                INSERT INTO transactions
                (user_id, account_id, transaction_type,
                 amount, previous_balance, new_balance, idempotency_key)
                VALUES (?, ?, 'withdraw', ?, ?, ?, ?)
            """, (
                from_user_id,
                from_account_id,
                amount,
                sender_balance,
                new_sender_balance,
                idempotency_key
            ))

            cursor.execute("""
                INSERT INTO transactions
                (user_id, account_id, transaction_type,
                 amount, previous_balance, new_balance, idempotency_key)
                VALUES (?, ?, 'deposit', ?, ?, ?, ?)
            """, (
                to_user_id,
                to_account_id,
                amount,
                receiver_balance,
                new_receiver_balance,
                idempotency_key
            ))

            conn.commit()
            return ref

        except Exception:
            conn.rollback()
            raise

        finally:
            cursor.close()
            conn.close()