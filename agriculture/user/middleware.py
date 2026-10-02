import logging

from django.conf import settings
from django.shortcuts import redirect
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken

logger = logging.getLogger(__name__)


class JWTAuthMiddleware:
    """
    JWT cookie-based auth middleware.
    Public paths bypass check. Protected paths require valid access token.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    # ✅ Sirf exact match wale paths (startswith se '/' sab ko public bana deta tha)
    PUBLIC_EXACT = (
        '/',
    )

    # ✅ Prefix match wale public paths
    PUBLIC_PREFIXES = (
        '/login/',
        '/register/',
        '/verify-otp/',
        '/resend-otp/',
        '/check-tracking/',
        '/admin-login/',
        '/admin-logout/',
        '/staff/login/',
        '/staff/register/',
        '/staff/logout/',
        '/api/',          
        '/django-admin/',
        '/static/',
        '/media/',
    )

    STAFF_PREFIXES = ('/staff/',)
    ADMIN_PREFIXES = ('/admin-dashboard/', '/dashboard/')

    def __call__(self, request):
        path = request.path
        is_public = (
            path in self.PUBLIC_EXACT
            or any(path.startswith(p) for p in self.PUBLIC_PREFIXES)
        )

        if is_public:
            return self.get_response(request)

        token = request.COOKIES.get('access')

        if not token:
            return self._redirect_to_login(request, reason="no_token")

        try:
            validated = AccessToken(token)
            request._jwt_user_id = validated['user_id']

        except (TokenError, InvalidToken, KeyError):
            logger.warning(
                "Invalid/expired JWT on path '%s' from IP %s",
                path,
                request.META.get('REMOTE_ADDR'),
            )
            return self._redirect_to_login(request, reason="invalid_token", clear_cookies=True)

        return self.get_response(request)

    def _redirect_to_login(self, request, reason="", clear_cookies=False):
        path = request.path

        if any(path.startswith(p) for p in self.STAFF_PREFIXES):
            login_url = 'staff_login'
        elif any(path.startswith(p) for p in self.ADMIN_PREFIXES):
            login_url = 'admin_login'
        else:
            login_url = 'login'

        logger.info(
            "Auth redirect → '%s' | path='%s' | reason='%s' | IP=%s",
            login_url,
            path,
            reason,
            request.META.get('REMOTE_ADDR'),
        )

        response = redirect(login_url)

        if clear_cookies:
            for cookie in ('access', 'refresh'):
                response.delete_cookie(cookie, samesite='Lax')
                response.set_cookie(
                    cookie, '',
                    max_age=0,
                    httponly=True,
                    secure=not settings.DEBUG,
                    samesite='Lax',
                )

        return response