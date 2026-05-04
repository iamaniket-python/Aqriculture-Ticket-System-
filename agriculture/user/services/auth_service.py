import logging
import secrets
import time

import requests

from django.conf import settings
from django.contrib.auth.models import User
from django.core.cache import cache

from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken

logger = logging.getLogger(__name__)


# ─── OTP Config ───────────────────────────────────────────────
OTP_EXPIRY_SECONDS   = 300  
OTP_MAX_ATTEMPTS     = 3
OTP_RESEND_COOLDOWN  = 60   
OTP_LOCKOUT_SECONDS  = 900   

# ─── Cookie Config ────────────────────────────────────────────
ACCESS_TOKEN_COOKIE_AGE  = 30 * 60         
REFRESH_TOKEN_COOKIE_AGE = 7 * 24 * 3600  


# ==============================================================
# 🔑 JWT
# ==============================================================

def get_user_from_token(request) -> User | None:
    """
    JWT cookie se user extract karo.
    Returns User if valid, None otherwise.
    """
    token = request.COOKIES.get('access')
    if not token:
        return None
    try:
        validated = AccessToken(token)
        user_id   = validated['user_id']
        return User.objects.get(id=user_id, is_active=True)
    except (TokenError, InvalidToken, User.DoesNotExist, KeyError):
        return None


def set_auth_cookies(response, refresh_token) -> None:
    """
    JWT cookies set karo with secure flags + expiry.
    """
    is_secure = not settings.DEBUG

    cookie_kwargs = dict(
        httponly = True,
        secure   = is_secure,
        samesite = 'Lax',
    )

    response.set_cookie(
        'access',
        str(refresh_token.access_token),
        max_age=ACCESS_TOKEN_COOKIE_AGE,
        **cookie_kwargs,
    )
    response.set_cookie(
        'refresh',
        str(refresh_token),
        max_age=REFRESH_TOKEN_COOKIE_AGE,
        **cookie_kwargs,
    )


def delete_auth_cookies(response) -> None:
    """
    Cookies properly delete karo — same flags as set karte waqt.
    Browser tabhi delete karta hai jab flags match karein.
    """
    is_secure = not settings.DEBUG

    for cookie_name in ('access', 'refresh'):
        response.delete_cookie(cookie_name, samesite='Lax')
        # Force expire as backup
        response.set_cookie(
            cookie_name,
            value    = '',
            max_age  = 0,
            httponly = True,
            secure   = is_secure,
            samesite = 'Lax',
        )


# ==============================================================
# 📱 FAST2SMS
# ==============================================================

def send_otp_sms(mobile: str, otp: str) -> bool:
    """
    Fast2SMS se OTP send karo.
    Returns True on success, False on any failure.
    Never raises — always returns bool.
    """
    api_key = getattr(settings, 'FAST2SMS_API_KEY', None)

    if not api_key:
        logger.error("FAST2SMS_API_KEY is not set in settings!")
        return False

    try:
        response = requests.post(
            url     = "https://www.fast2sms.com/dev/bulkV2",
            headers = {
                "authorization": api_key,
                "Content-Type":  "application/json",
            },
            json = {
                "route":            "otp",   # Fast2SMS OTP route
                "variables_values": otp,     # OTP value
                "numbers":          mobile,  # 10-digit mobile number
                "flash":            0,
            },
            timeout = 10,  # 10 second timeout — never hang
        )

        data = response.json()

        if data.get("return") is True:
            logger.info("OTP SMS sent successfully to ...%s", mobile[-3:])
            return True
        else:
            logger.error(
                "Fast2SMS rejected request for ...%s | response: %s",
                mobile[-3:],
                data.get("message", "Unknown error"),
            )
            return False

    except requests.Timeout:
        logger.error("Fast2SMS timeout for ...%s", mobile[-3:])
        return False

    except requests.ConnectionError:
        logger.error("Fast2SMS connection error — check internet/API availability")
        return False

    except requests.RequestException as e:
        logger.error("Fast2SMS unexpected error: %s", str(e))
        return False

    except Exception as e:
        logger.error("Unexpected error in send_otp_sms: %s", str(e))
        return False


# ==============================================================
# 🔢 OTP — Cache Keys
# ==============================================================

def _otp_cache_key(mobile: str) -> str:
    return f"otp_data:{mobile}"

def _resend_lock_key(mobile: str) -> str:
    return f"otp_resend:{mobile}"

def _lockout_key(mobile: str) -> str:
    return f"otp_lockout:{mobile}"


# ==============================================================
# 🔢 OTP — Generate
# ==============================================================

def generate_otp(mobile: str) -> str:
    """
    Cryptographically secure 6-digit OTP generate karo.

    - DEBUG=True  → OTP console mein print hoga (dev mode, SMS nahi jaayega)
    - DEBUG=False → Real SMS Fast2SMS se jaayega

    Raises:
        PermissionError — if mobile is locked out
        RuntimeError    — if SMS sending fails in production
    """

    # ✅ Check lockout first
    if cache.get(_lockout_key(mobile)):
        logger.warning("OTP blocked — mobile ...%s is locked out", mobile[-3:])
        raise PermissionError(
            "Too many OTP attempts. Please wait 15 minutes before trying again."
        )

    # Generate cryptographically secure OTP
    otp = str(secrets.randbelow(900_000) + 100_000)

    # Store in cache BEFORE sending SMS
    # (so verify works even if there's a slight delay)
    cache.set(_otp_cache_key(mobile), {
        "otp":      otp,
        "attempts": 0,
        "created":  time.time(),
    }, timeout=OTP_EXPIRY_SECONDS)

    cache.set(_resend_lock_key(mobile), 1, timeout=OTP_RESEND_COOLDOWN)

    if settings.DEBUG:
        # ✅ Development — log OTP, don't waste SMS credits
        logger.debug("DEV OTP for ...%s → %s", mobile[-3:], otp)
        print(f"\n[DEV] OTP for {mobile}: {otp}\n")   # visible in terminal
    else:
        # ✅ Production — send real SMS via Fast2SMS
        sms_sent = send_otp_sms(mobile, otp)

        if not sms_sent:
            # Clean up cache — OTP was never delivered
            cache.delete(_otp_cache_key(mobile))
            cache.delete(_resend_lock_key(mobile))
            raise RuntimeError(
                "Failed to send OTP. Please try again in a moment."
            )

    return otp


# ==============================================================
# 🔢 OTP — Verify
# ==============================================================

def verify_otp(mobile: str, entered: str) -> tuple[bool, str]:
    """
    OTP verify karo with:
    - Lockout check
    - Expiry check
    - Rate limiting (max 3 attempts)
    - Constant-time comparison (timing attack protection)

    Returns (True, "") on success
    Returns (False, error_message) on failure
    """

    # ✅ Check lockout
    if cache.get(_lockout_key(mobile)):
        return False, "Too many failed attempts. Please wait 15 minutes."

    key  = _otp_cache_key(mobile)
    data = cache.get(key)

    if not data:
        return False, "OTP expired. Please request a new one."

    # ✅ Increment BEFORE comparing — prevents timing attacks
    data["attempts"] += 1
    cache.set(key, data, timeout=OTP_EXPIRY_SECONDS)

    # ✅ Too many attempts — trigger lockout
    if data["attempts"] > OTP_MAX_ATTEMPTS:
        cache.delete(key)
        cache.set(_lockout_key(mobile), 1, timeout=OTP_LOCKOUT_SECONDS)
        logger.warning("OTP lockout triggered for ...%s", mobile[-3:])
        return False, "Too many attempts. Please wait 15 minutes before trying again."

    # ✅ Constant-time comparison — prevents timing attacks
    if not secrets.compare_digest(data["otp"], entered.strip()):
        remaining = OTP_MAX_ATTEMPTS - data["attempts"]
        return False, f"Invalid OTP. {remaining} attempt(s) remaining."

    # ✅ Success — clean up all OTP keys
    cache.delete(key)
    cache.delete(_resend_lock_key(mobile))
    logger.info("OTP verified successfully for ...%s", mobile[-3:])
    return True, ""


# ==============================================================
# 🔢 OTP — Resend Check
# ==============================================================

def can_resend_otp(mobile: str) -> bool:
    """
    Returns True if resend is allowed.
    False if cooldown active OR mobile is locked out.
    """
    if cache.get(_lockout_key(mobile)):
        return False
    return not cache.get(_resend_lock_key(mobile))