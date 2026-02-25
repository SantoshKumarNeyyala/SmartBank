from database.connection import DatabaseConnection


class AuditService:
    @staticmethod
    def log(user_id=None, account_id=None, action="UNKNOWN", description=None, ip=None, user_agent=None):
        conn = DatabaseConnection.get_connection()
        cur = conn.cursor()
        try:
            cur.execute("""
                INSERT INTO audit_logs (user_id, account_id, action, description, ip_address, user_agent)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (user_id, account_id, action, description, ip, user_agent))
            conn.commit()
        finally:
            cur.close()
            conn.close()

    @staticmethod
    def latest(limit=200):
        conn = DatabaseConnection.get_connection()
        cur = conn.cursor()
        try:
            cur.execute("""
                SELECT TOP (?) user_id, account_id, action, description, ip_address, created_at
                FROM audit_logs
                ORDER BY created_at DESC
            """, (limit,))
            return cur.fetchall()
        finally:
            cur.close()
            conn.close()

    @staticmethod
    def for_user(user_id, limit=200):
        conn = DatabaseConnection.get_connection()
        cur = conn.cursor()
        try:
            cur.execute("""
                SELECT TOP (?) account_id, action, description, ip_address, created_at
                FROM audit_logs
                WHERE user_id = ?
                ORDER BY created_at DESC
            """, (limit, user_id))
            return cur.fetchall()
        finally:
            cur.close()
            conn.close()