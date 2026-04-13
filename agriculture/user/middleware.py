from django.shortcuts import redirect

class JWTAuthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        
        public_paths = ['/login/', '/register/', '/admin/', '/verify-otp/', '/']

        if request.path not in public_paths:
            token = request.COOKIES.get('access')

            if not token:
                return redirect('login')

        return self.get_response(request)
