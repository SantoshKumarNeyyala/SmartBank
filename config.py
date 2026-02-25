import os
from decimal import Decimal


class BaseConfig:
    ENV = os.getenv("ENV", "development")

    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret")

    DB_DRIVER = os.getenv("DB_DRIVER", "ODBC Driver 17 for SQL Server")
    DB_SERVER = os.getenv("DB_SERVER", r"DESKTOP-NS3OVRH\SQLEXPRESS")
    DB_NAME = os.getenv("DB_NAME", "SmartBank")

    MAX_TRANSFER_PER_TX = Decimal(os.getenv("MAX_TRANSFER_PER_TX", "50000.00"))
    MAX_TRANSFER_PER_DAY = Decimal(os.getenv("MAX_TRANSFER_PER_DAY", "500000.00"))

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = False


class DevelopmentConfig(BaseConfig):
    DEBUG = True


class ProductionConfig(BaseConfig):
    DEBUG = False
    SESSION_COOKIE_SECURE = True  # Secure cookies in HTTPS

CONFIG = DevelopmentConfig