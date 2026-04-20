from django.shortcuts import redirect

class JWTAuthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        public_paths = [
            '/login/',
            '/register/',
            '/admin/',
            '/verify-otp/',
            '/',
        ]

        # ✅ Allow public pages
        if request.path in public_paths:
            return self.get_response(request)

        # ✅ Allow static/media files (IMPORTANT)
        if request.path.startswith('/static/') or request.path.startswith('/media/'):
            return self.get_response(request)

        # 🔐 Check token
        token = request.COOKIES.get('access')

        if not token:
            return redirect('/login/')  # FIXED PATH

        return self.get_response(request)