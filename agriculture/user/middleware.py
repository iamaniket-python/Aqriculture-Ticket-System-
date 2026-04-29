from django.shortcuts import redirect
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken
from django.contrib.auth.models import User


class JWTAuthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    # Ye paths bina login ke accessible hain
    PUBLIC_PATHS = [
        '/',
        '/login/',
        '/register/',
        '/verify-otp/',
        '/resend-otp/',         # ✅ Add kiya — pehle missing tha
        '/check-tracking/',
        '/admin-login/',
        '/admin-logout/',
        '/staff/login/',        # ✅ Fix kiya — pehle '/staff-login/' tha (wrong)
        '/staff/register/',     # ✅ Fix kiya — pehle '/staff-register/' tha (wrong)
        '/staff/logout/',       # ✅ Add kiya
        '/api/',                # ✅ Add kiya — API block ho rahi thi
        '/admin/',              # Django admin panel
    ]

    def __call__(self, request):
        # Public path hai toh check mat karo
        is_public = any(request.path.startswith(path) for path in self.PUBLIC_PATHS)

        if not is_public:
            token = request.COOKIES.get('access')

            if not token:
                # Staff ya admin path pe hai toh unke login pe bhejo
                if request.path.startswith('/staff/'):
                    return redirect('staff_login')
                if request.path.startswith('/admin-dashboard/') or request.path.startswith('/dashboard/'):
                    return redirect('admin_login')
                return redirect('login')

            # ✅ Token properly validate karo — simplejwt se
            try:
                validated = AccessToken(token)
                user_id = validated['user_id']
                request._jwt_user_id = user_id   # views mein use kar sakte ho
            except (TokenError, InvalidToken, KeyError):
                # Invalid/expired token — login pe bhejo
                response = redirect('login')
                response.delete_cookie('access')
                response.delete_cookie('refresh')
                return response

        response = self.get_response(request)
        return response