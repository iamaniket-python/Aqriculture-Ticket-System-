from django.shortcuts import redirect
from django.contrib.auth.models import User
import jwt
from django.conf import settings


class JWTAuthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        public_paths = [
            '/login/', '/register/', '/admin/', '/verify-otp/', '/',
            '/admin-login/', '/staff-login/', '/staff-register/',
        ]

        if not any(request.path.startswith(path) for path in public_paths):
            token = request.COOKIES.get('access')
            if not token:
                return redirect('login')

        response = self.get_response(request)
        return response