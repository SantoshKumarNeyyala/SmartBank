import random
import time

class OTPService:

    OTP_EXPIRY_SECONDS = 120  # 2 minutes
    MAX_ATTEMPTS = 3

    @staticmethod
    def generate_otp():
        return str(random.randint(100000, 999999))

    @staticmethod
    def create_otp_session(session):
        otp = OTPService.generate_otp()
        session["transfer_otp"] = otp
        session["transfer_otp_expiry"] = time.time() + OTPService.OTP_EXPIRY_SECONDS
        session["transfer_otp_attempts"] = 0
        return otp

    @staticmethod
    def verify_otp(session, entered_otp):
        if "transfer_otp" not in session:
            return False, "OTP not generated."

        if time.time() > session.get("transfer_otp_expiry", 0):
            return False, "OTP expired."

        if session.get("transfer_otp_attempts", 0) >= OTPService.MAX_ATTEMPTS:
            return False, "Maximum OTP attempts exceeded."

        if entered_otp != session.get("transfer_otp"):
            session["transfer_otp_attempts"] += 1
            return False, "Invalid OTP."

        # OTP correct
        session.pop("transfer_otp", None)
        session.pop("transfer_otp_expiry", None)
        session.pop("transfer_otp_attempts", None)
        return True, "OTP verified."