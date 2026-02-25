from decimal import Decimal
from database.connection import DatabaseConnection
from utils.money import to_decimal, quantize_money
import datetime

class FraudService:

    @staticmethod
    def calculate_risk(from_account_id: int, to_account_id: int, amount: Decimal):
        risk_score = 0

        conn = DatabaseConnection.get_connection()
        cursor = conn.cursor()

        try:
            amount = quantize_money(to_decimal(amount))

            # Rule 1: Large amount
            if amount > 100000:
                risk_score += 25

            # Rule 2: Multiple transfers in last 5 minutes
            cursor.execute("""
                SELECT COUNT(*)
                FROM transfers
                WHERE from_account_id = ?
                AND created_at >= DATEADD(MINUTE, -5, GETDATE())
            """, (from_account_id,))
            recent_count = cursor.fetchone()[0]
            if recent_count >= 3:
                risk_score += 30

            # Rule 3: Daily total > 150k
            cursor.execute("""
                SELECT ISNULL(SUM(amount),0)
                FROM transfers
                WHERE from_account_id = ?
                AND CAST(created_at AS DATE) = CAST(GETDATE() AS DATE)
                AND status='success'
            """, (from_account_id,))
            daily_total = cursor.fetchone()[0] or 0
            daily_total = quantize_money(to_decimal(daily_total))
            if daily_total > 150000:
                risk_score += 10

            # Rule 4: New receiver (first time transfer)
            cursor.execute("""
                SELECT COUNT(*)
                FROM transfers
                WHERE from_account_id = ?
                AND to_account_id = ?
            """, (from_account_id, to_account_id))
            previous_transfers = cursor.fetchone()[0]
            if previous_transfers == 0:
                risk_score += 15

            return risk_score

        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def decision(risk_score: int):
        if risk_score > 60:
            return "block"
        if risk_score >= 30:
            return "stepup"
        return "allow"