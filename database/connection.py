import pyodbc
from flask import current_app

class DatabaseConnection:
    @staticmethod
    def get_connection():
        try:
            cfg = current_app.config

            connection = pyodbc.connect(
                f"DRIVER={{{cfg['DB_DRIVER']}}};"
                f"SERVER={cfg['DB_SERVER']};"
                f"DATABASE={cfg['DB_NAME']};"
                "Trusted_Connection=yes;"
            )
            return connection
        except pyodbc.Error as e:
            # Don’t print in production; we’ll switch to logging in Phase 7.1
            raise RuntimeError(f"Database connection failed: {e}") from e