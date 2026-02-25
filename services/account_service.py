import os
from database.connection import DatabaseConnection

class AccountService:
    @staticmethod
    def get_user_accounts(user_id: int):
        conn = DatabaseConnection.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
                       SELECT id, account_number, account_type, balance, is_frozen
                       FROM accounts
                       WHERE user_id = ? AND status = 'active'
                       """, (user_id,))
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return rows

    @staticmethod
    def get_account_by_id(account_id: int, user_id: int):
        conn = DatabaseConnection.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, account_number, account_type, balance, status
            FROM accounts
            WHERE id = ? AND user_id = ? AND status = 'active'
        """, (account_id, user_id))
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        return row

    @staticmethod
    def get_account_by_number(account_number: str):
        conn = DatabaseConnection.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, user_id, account_number, account_type, balance, status
            FROM accounts
            WHERE account_number = ? AND status = 'active'
        """, (account_number,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        return row

    @staticmethod
    def create_account(user_id: int, account_type: str):
        account_type = (account_type or "").strip().lower()
        if account_type not in ("savings", "current"):
            raise ValueError("Invalid account type.")

        temp_no = f"TEMP-{user_id}-{os.urandom(4).hex()}"

        conn = DatabaseConnection.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO accounts (user_id, account_number, account_type, balance)
                OUTPUT INSERTED.id
                VALUES (?, ?, ?, 0)
            """, (user_id, temp_no, account_type))

            row = cursor.fetchone()
            if not row or row[0] is None:
                raise Exception("Failed to create account (no ID returned).")

            new_id = int(row[0])
            acc_no = f"SB{new_id:08d}"

            cursor.execute("UPDATE accounts SET account_number = ? WHERE id = ?", (acc_no, new_id))

            conn.commit()
            return acc_no

        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def close_account(user_id: int, account_id: int):
        conn = DatabaseConnection.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT balance FROM accounts
                WHERE id = ? AND user_id = ? AND status='active'
            """, (account_id, user_id))
            row = cursor.fetchone()
            if not row:
                raise ValueError("Account not found.")

            bal = float(row[0] or 0)
            if bal != 0:
                raise ValueError("Account balance must be 0 to close.")

            cursor.execute("""
                UPDATE accounts SET status='closed'
                WHERE id = ? AND user_id = ?
            """, (account_id, user_id))
            conn.commit()

        finally:
            cursor.close()
            conn.close()

# ================= FREEZE ACCOUNT =================
@staticmethod
def freeze_account(user_id: int, account_id: int):
    conn = DatabaseConnection.get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE accounts
        SET is_frozen = 1
        WHERE id = ? AND user_id = ?
    """, (account_id, user_id))

    if cursor.rowcount == 0:
        conn.close()
        raise ValueError("Account not found or unauthorized.")

    conn.commit()
    cursor.close()
    conn.close()


# ================= UNFREEZE ACCOUNT =================
@staticmethod
def unfreeze_account(user_id: int, account_id: int):
    conn = DatabaseConnection.get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE accounts
        SET is_frozen = 0
        WHERE id = ? AND user_id = ?
    """, (account_id, user_id))

    if cursor.rowcount == 0:
        conn.close()
        raise ValueError("Account not found or unauthorized.")

    conn.commit()
    cursor.close()
    conn.close()