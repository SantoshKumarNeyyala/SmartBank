from flask_bcrypt import Bcrypt

bcrypt = Bcrypt()

def hash_password(password: str) -> str:
    """Generate secure bcrypt hash."""
    return bcrypt.generate_password_hash(password).decode("utf-8")

def verify_password(hashed_password: str, plain_password: str) -> bool:
    """Verify bcrypt password."""
    return bcrypt.check_password_hash(hashed_password, plain_password)