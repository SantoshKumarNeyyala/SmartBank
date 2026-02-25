from decimal import Decimal
from database.connection import DatabaseConnection
from utils.money import to_decimal, quantize_money
import csv
import json
from io import StringIO


class BankService:


    @staticmethod
    def export_transactions(user_id: int, account_id: int):
        conn = DatabaseConnection.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT transaction_type,
                   amount,
                   previous_balance,
                   new_balance,
                   created_at
            FROM transactions
            WHERE user_id = ? AND account_id = ?
            ORDER BY created_at DESC
        """, (user_id, account_id))

        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        return rows


    @staticmethod
    def export_csv(user_id: int, account_id: int):
        rows = BankService.export_transactions(user_id, account_id)

        output = StringIO()
        writer = csv.writer(output)

        writer.writerow([
            "Type",
            "Amount",
            "Previous Balance",
            "New Balance",
            "Date"
        ])

        for r in rows:
            writer.writerow([
                r[0],
                float(r[1]),
                float(r[2]),
                float(r[3]),
                r[4]
            ])

        output.seek(0)
        return output


    @staticmethod
    def export_json(user_id: int, account_id: int):
        rows = BankService.export_transactions(user_id, account_id)

        data = []
        for r in rows:
            data.append({
                "type": r[0],
                "amount": float(r[1]),
                "previous_balance": float(r[2]),
                "new_balance": float(r[3]),
                "date": str(r[4])
            })

        output = StringIO()
        json.dump(data, output, indent=4)
        output.seek(0)

        return output

    # ================= GET BALANCE =================
    @staticmethod
    def get_balance(account_id: int) -> Decimal:
        conn = DatabaseConnection.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT balance FROM accounts WHERE id = ?",
            (account_id,)
        )

        row = cursor.fetchone()
        cursor.close()
        conn.close()

        return quantize_money(to_decimal(row[0])) if row else Decimal("0.00")


    # ================= GET TRANSACTIONS =================
    @staticmethod
    def get_transactions(
    user_id: int,
    account_id: int,
    tx_type: str = None,
    date_from: str = None,
    date_to: str = None,
    page: int = 1,
    per_page: int = 10
    ):
        conn = DatabaseConnection.get_connection()
        cursor = conn.cursor()

        query = """
            SELECT transaction_type,
                    amount,
                    previous_balance,
                    new_balance,
                    created_at
            FROM transactions
            WHERE user_id = ? AND account_id = ?
        """
        params = [user_id, account_id]

        # Filter by type
        if tx_type and tx_type in ("deposit", "withdraw"):
            query += " AND transaction_type = ?"
            params.append(tx_type)

        # Filter by date range
        if date_from:
            query += " AND CAST(created_at AS DATE) >= ?"
            params.append(date_from)

        if date_to:
            query += " AND CAST(created_at AS DATE) <= ?"
            params.append(date_to)

        # Pagination
        offset = (page - 1) * per_page
        query += """
            ORDER BY created_at DESC
            OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
        """
        params.extend([offset, per_page])

        cursor.execute(query, tuple(params))
        rows = cursor.fetchall()

        cursor.close()
        conn.close()

        return rows


    # ================= DEPOSIT =================
    @staticmethod
    def deposit(user_id: int, account_id: int, amount: Decimal, idempotency_key: str) -> Decimal:

        amount = quantize_money(to_decimal(amount))
        conn = DatabaseConnection.get_connection()
        cursor = conn.cursor()

        try:
            conn.autocommit = False

            # Idempotency check
            cursor.execute(
                "SELECT new_balance FROM transactions WHERE idempotency_key = ?",
                (idempotency_key,)
            )
            existing = cursor.fetchone()
            if existing:
                return quantize_money(to_decimal(existing[0]))

            # Lock account row and check frozen
            cursor.execute("""
                SELECT balance, is_frozen
                FROM accounts WITH (UPDLOCK, ROWLOCK)
                WHERE id = ? AND user_id = ? AND status = 'active'
            """, (account_id, user_id))

            row = cursor.fetchone()

            if not row:
                raise ValueError("Account not found.")

            if row[1] == 1:
                raise ValueError("Account is frozen. Deposit not allowed.")

            prev_balance = quantize_money(to_decimal(row[0]))
            new_balance = quantize_money(prev_balance + amount)

            cursor.execute(
                "UPDATE accounts SET balance = ? WHERE id = ?",
                (new_balance, account_id)
            )

            cursor.execute("""
                INSERT INTO transactions
                (user_id, account_id, transaction_type,
                 amount, previous_balance, new_balance, idempotency_key)
                VALUES (?, ?, 'deposit', ?, ?, ?, ?)
            """, (user_id, account_id, amount, prev_balance, new_balance, idempotency_key))

            conn.commit()
            return new_balance

        except Exception:
            conn.rollback()
            raise

        finally:
            cursor.close()
            conn.close()


    # ================= WITHDRAW =================
    @staticmethod
    def withdraw(user_id: int, account_id: int, amount: Decimal, idempotency_key: str) -> Decimal:

        amount = quantize_money(to_decimal(amount))
        conn = DatabaseConnection.get_connection()
        cursor = conn.cursor()

        try:
            conn.autocommit = False

            # Idempotency check
            cursor.execute(
                "SELECT new_balance FROM transactions WHERE idempotency_key = ?",
                (idempotency_key,)
            )
            existing = cursor.fetchone()
            if existing:
                return quantize_money(to_decimal(existing[0]))

            # Lock account row and check frozen
            cursor.execute("""
                SELECT balance, is_frozen
                FROM accounts WITH (UPDLOCK, ROWLOCK)
                WHERE id = ? AND user_id = ? AND status = 'active'
            """, (account_id, user_id))

            row = cursor.fetchone()

            if not row:
                raise ValueError("Account not found.")

            if row[1] == 1:
                raise ValueError("Account is frozen. Withdrawal not allowed.")

            prev_balance = quantize_money(to_decimal(row[0]))

            if amount > prev_balance:
                raise ValueError("Insufficient balance.")

            new_balance = quantize_money(prev_balance - amount)

            cursor.execute(
                "UPDATE accounts SET balance = ? WHERE id = ?",
                (new_balance, account_id)
            )

            cursor.execute("""
                INSERT INTO transactions
                (user_id, account_id, transaction_type,
                 amount, previous_balance, new_balance, idempotency_key)
                VALUES (?, ?, 'withdraw', ?, ?, ?, ?)
            """, (user_id, account_id, amount, prev_balance, new_balance, idempotency_key))

            conn.commit()
            return new_balance

        except Exception:
            conn.rollback()
            raise

        finally:
            cursor.close()
            conn.close()