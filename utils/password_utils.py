from utils.security import bcrypt

def normalize_hash(stored_hash):
    """
    SQL server (pyodbc) may return password hash as:
    - str
    - bytes
    - memoryview
    we normalize to str for bcrypt check.
    """
    if stored_hash is None:
        return None
    
    if isinstance(stored_hash, memoryview):
        stored_hash = stored_hash.tobytes()
    
    if isinstance(stored_hash, bytes):
        stored_hash = stored_hash.decode("utf-8", errors="ignore")
    
    return stored_hash

def verify_password(stored_hash, plain_password: str) -> bool:
    stored_hash = normalize_hash(stored_hash)
    if not stored_hash or plain_password is None:
        return False
    return bcrypt.check_password_hash(stored_hash, plain_password)
