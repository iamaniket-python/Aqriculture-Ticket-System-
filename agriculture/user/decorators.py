import logging
from functools import wraps

from django.contrib import messages
from django.core.cache import cache
from django.shortcuts import redirect

from user.services.auth_service import get_user_from_token 

logger = logging.getLogger(__name__)


def admin_session_required(view_func):
    """
    Admin access — triple layer verification:
    1. Must be authenticated
    2. Must be superuser AND is_staff (DB check)
    3. Session role must be 'admin'
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.warning(request, "Please login to access the admin panel.")
            return redirect('admin_login')

        # ✅ Check both is_superuser AND is_staff
        if not request.user.is_superuser or not request.user.is_staff:
            logger.warning(
                "Unauthorized admin access attempt by user '%s' (id=%s) from IP %s",
                request.user.username,
                request.user.id,
                request.META.get('REMOTE_ADDR'),
            )
            request.session.flush()   # ✅ kill suspicious session
            return redirect('admin_login')

        if request.session.get('role') != 'admin':
            return redirect('admin_login')

        return view_func(request, *args, **kwargs)
    return wrapper


def staff_session_required(view_func):
    """
    Staff access — DB verify with caching to avoid per-request DB hit
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.warning(request, "Please login to continue.")
            return redirect('staff_login')

        if request.session.get('role') != 'staff':
            return redirect('staff_login')

        # ✅ Cache staff approval status for 5 minutes
        # Avoids hitting DB on every single staff page load
        cache_key = f"staff_approved_{request.user.id}"
        is_approved = cache.get(cache_key)

        if is_approved is None:
            # Cache miss — check DB and store result
            from user.models import StaffProfile
            is_approved = StaffProfile.objects.filter(
                user=request.user,
                is_approved=True
            ).exists()
            cache.set(cache_key, is_approved, timeout=300)  # cache for 5 minutes

        if not is_approved:
            logger.warning(
                "Unapproved staff access attempt by user '%s' (id=%s) from IP %s",
                request.user.username,
                request.user.id,
                request.META.get('REMOTE_ADDR'),
            )
            request.session.flush()
            messages.error(request, "Your account is not approved yet.")
            return redirect('staff_login')

        return view_func(request, *args, **kwargs)
    return wrapper


def login_required_token(view_func):
    """
    JWT cookie verification for user-facing views.
    Attaches verified user to request._token_user
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        user = get_user_from_token(request)

        if not user:
            messages.warning(request, "Your session has expired. Please login again.")
            return redirect('login')

        if not user.is_active:
            # ✅ Reject deactivated accounts even with valid token
            logger.warning(
                "Inactive user '%s' (id=%s) tried to access %s",
                user.username,
                user.id,
                request.path,
            )
            messages.error(request, "Your account has been deactivated.")
            return redirect('login')

        request._token_user = user
        return view_func(request, *args, **kwargs)
    return wrapper


# =============================================
# 🔧 UTILITY — clear staff cache on approval/rejection
# =============================================

def clear_staff_cache(user_id: int):
    """
    Call this whenever a staff member is approved or rejected
    so the cache doesn't serve stale approval status.

    Usage in views:
        from .decorators import clear_staff_cache
        clear_staff_cache(staff.user.id)
    """
    cache.delete(f"staff_approved_{user_id}")