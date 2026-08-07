import hashlib
import hmac
import secrets

from app.core.config import settings


OTP_DIGITS = "0123456789"


def generate_otp() -> str:
    return "".join(secrets.choice(OTP_DIGITS) for _ in range(settings.OTP_LENGTH))


def hash_otp(otp: str) -> str:
    return hashlib.sha256(otp.encode("utf-8")).hexdigest()


def verify_otp(
    plain_otp: str,
    otp_hash: str,
) -> bool:
    return hmac.compare_digest(hash_otp(plain_otp), otp_hash)
