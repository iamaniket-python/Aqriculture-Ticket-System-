import secrets
import time
from django.contrib.auth.models import User
from django.conf import settings
from django.core.cache import cache
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken

# ─── OTP Config ───────────────────────────────────────────────
OTP_EXPIRY_SECONDS = 300      # 5 minutes
OTP_MAX_ATTEMPTS   = 3
OTP_RESEND_COOLDOWN = 60      # 1 minute between resends


# ─── JWT ──────────────────────────────────────────────────────

def get_user_from_token(request) -> User | None:
    """
    JWT cookie se user extract karo — simplejwt se properly validate karo.
    Bare except nahi, specific exceptions pakdo.
    """
    token = request.COOKIES.get('access')
    if not token:
        return None
    try:
        validated = AccessToken(token)
        user_id = validated['user_id']
        return User.objects.select_related().get(id=user_id, is_active=True)
    except (TokenError, InvalidToken, User.DoesNotExist, KeyError):
        return None


def set_auth_cookies(response, refresh_token) -> None:
    """
    Secure cookie flags ke saath JWT set karo.
    Ek jagah — har jagah same flags.
    """
    cookie_kwargs = dict(
        httponly=True,
        secure=not settings.DEBUG,   # DEBUG mein HTTP allow, production mein HTTPS only
        samesite='Lax',
    )
    response.set_cookie('access',  str(refresh_token.access_token), **cookie_kwargs)
    response.set_cookie('refresh', str(refresh_token),               **cookie_kwargs)


def delete_auth_cookies(response) -> None:
    response.delete_cookie('access')
    response.delete_cookie('refresh')


# ─── OTP ──────────────────────────────────────────────────────

def _otp_cache_key(mobile: str) -> str:
    return f"otp_data:{mobile}"

def _resend_lock_key(mobile: str) -> str:
    return f"otp_resend:{mobile}"


def generate_otp(mobile: str) -> str:
    """
    Cryptographically secure 6-digit OTP generate karo aur cache mein store karo.
    Returns OTP — caller SMS service ko bheje.
    """
    otp = str(secrets.randbelow(900_000) + 100_000)   # 100000–999999
    cache.set(_otp_cache_key(mobile), {
        "otp":      otp,
        "attempts": 0,
        "created":  time.time(),
    }, timeout=OTP_EXPIRY_SECONDS)
    cache.set(_resend_lock_key(mobile), 1, timeout=OTP_RESEND_COOLDOWN)
    return otp


def verify_otp(mobile: str, entered: str) -> tuple[bool, str]:
    """
    OTP verify karo — rate limit, expiry, constant-time compare.
    Returns (success, error_message).
    """
    key  = _otp_cache_key(mobile)
    data = cache.get(key)

    if not data:
        return False, "OTP expired. Please request a new one."

    if data["attempts"] >= OTP_MAX_ATTEMPTS:
        cache.delete(key)
        return False, "Too many attempts. Please request a new OTP."

    # Pehle attempt count badhaao (timing attack prevention)
    data["attempts"] += 1
    cache.set(key, data, timeout=OTP_EXPIRY_SECONDS)

    # Constant-time comparison — timing attack se bachao
    if not secrets.compare_digest(data["otp"], entered.strip()):
        remaining = OTP_MAX_ATTEMPTS - data["attempts"]
        return False, f"Invalid OTP. {remaining} attempt(s) remaining."

    cache.delete(key)   # One-time use — delete on success
    return True, ""


def can_resend_otp(mobile: str) -> bool:
    return not cache.get(_resend_lock_key(mobile))
