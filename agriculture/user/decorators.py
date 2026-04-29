from functools import wraps
from django.shortcuts import redirect
from django.http import HttpResponseForbidden
from user.models import StaffProfile


def admin_session_required(view_func):
    """
    Admin access decorator — triple layer verification:
    1. User must be authenticated
    2. DB check: must be superuser
    3. Session role must be 'admin'
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('admin_login')
        if not request.user.is_superuser:
            return redirect('admin_login')
        if request.session.get('role') != 'admin':
            return redirect('admin_login')
        return view_func(request, *args, **kwargs)
    return wrapper


def staff_session_required(view_func):
    """
    Staff access decorator — DB se verify karo, sirf session pe trust nahi
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('staff_login')
        if request.session.get('role') != 'staff':
            return redirect('staff_login')
        profile = StaffProfile.objects.filter(
            user=request.user,
            is_approved=True
        ).exists()
        if not profile:
            request.session.flush()
            return redirect('staff_login')
        return view_func(request, *args, **kwargs)
    return wrapper


def login_required_token(view_func):
    """
    JWT cookie se user verify karo — user views ke liye
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        from user.services.auth_service import get_user_from_token
        user = get_user_from_token(request)
        if not user:
            return redirect('login')
        request._token_user = user
        return view_func(request, *args, **kwargs)
    return wrapper