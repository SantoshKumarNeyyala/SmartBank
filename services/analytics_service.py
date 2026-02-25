from database.connection import DatabaseConnection
from utils.money import to_decimal, quantize_money

class AnalyticsService:
    @staticmethod
    def get_user_analytics(user_id: int) -> dict:
        conn = DatabaseConnection.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                SUM(CASE WHEN transaction_type='deposit' THEN amount ELSE 0 END),
                SUM(CASE WHEN transaction_type='withdraw' THEN amount ELSE 0 END),
                COUNT(*)
            FROM transactions
            WHERE user_id = ?
        """, (user_id,))

        row = cursor.fetchone()
        cursor.close()
        conn.close()

        total_deposit = quantize_money(to_decimal(row[0] or 0))
        total_withdraw = quantize_money(to_decimal(row[1] or 0))
        total_transactions = int(row[2] or 0)

        return {
            "total_deposit": f"{total_deposit:.2f}",
            "total_withdraw": f"{total_withdraw:.2f}",
            "total_transactions": total_transactions
        }