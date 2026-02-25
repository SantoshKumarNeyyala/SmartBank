from database.connection import DatabaseConnection
from utils.security import bcrypt


class UserModel:
    @staticmethod
    def create_user(full_name, email, password):
        conn = None
        cursor = None
        try:
            conn = DatabaseConnection.get_connection()
            cursor = conn.cursor()

            hashed_password = bcrypt.generate_password_hash(password).decode("utf-8")

            sql = """
                INSERT INTO users (full_name, email, password_hash)
                VALUES (?, ?, ?)
            """
            cursor.execute(sql, (full_name, email, hashed_password))
            conn.commit()
            return True

        except Exception as e:
            print("Error creating user:", repr(e))
            if conn:
                conn.rollback()
            return False

        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    @staticmethod
    def get_user_by_email(email):
        conn = None
        cursor = None
        try:
            conn = DatabaseConnection.get_connection()
            cursor = conn.cursor()

            sql = """
                SELECT id,
                    full_name, 
                    email, 
                    password_hash,
                    failed_login_attempts,
                    is_locked,
                    role
                FROM users
                WHERE email = ?
            """
            cursor.execute(sql, (email,))
            return cursor.fetchone()

        except Exception as e:
            print("Error fetching user:", repr(e))
            return None

        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()