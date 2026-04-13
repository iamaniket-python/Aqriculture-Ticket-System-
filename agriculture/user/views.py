from django.shortcuts import redirect, render
from rest_framework import generics
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import AllowAny
from django.contrib.auth.models import User
import jwt
from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.conf import settings
from django.contrib.auth.models import User
from user.models import Ticket
from .serializers import RegisterSerializer,LoginSerializer,UserSerializer
from django.contrib.auth import authenticate
from .models import Profile

# Create your views here.
class RegisterView(generics.CreateAPIView):
    queryset= User.objects.all()
    permission_classes=[AllowAny]
    serializer_class=RegisterSerializer


class LoginView(generics.GenericAPIView):
    serializer_class = LoginSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        email = request.data.get('email')
        password = request.data.get('password')

        try:
            user_obj = User.objects.get(email=email) 
        except User.DoesNotExist:
            return Response({"detail": "Invalid credentials"}, status=401)

        user = authenticate(username=user_obj.username, password=password)

        if user is not None:
            refresh = RefreshToken.for_user(user)
            user_serializer = UserSerializer(user)

            return Response({
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'user': user_serializer.data
            })
        else:
            return Response({"detail": "Invalid credentials"}, status=401)
        
def get_user_from_token(request):
    token = request.COOKIES.get('access')

    if not token:
        return None

    try:
        decoded = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        user_id = decoded.get("user_id")
        return User.objects.get(id=user_id)
    except:
        return None
    
# 📝 Register Page 
def register(request):
    if request.method == "POST":
        username = request.POST.get("username")
        email = request.POST.get("email")
        password = request.POST.get("password")
        mobile = request.POST.get("mobile")

        # ✅ validations
        if User.objects.filter(username=username).exists():
            return render(request, 'Authentication/register.html', {"error": "Username already exists"})

        if User.objects.filter(email=email).exists():
            return render(request, 'Authentication/register.html', {"error": "Email already exists"})

        # ✅ create user (NO mobile here)
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password
        )

        # ✅ create profile with mobile
        Profile.objects.create(
            user=user,
            mobile=mobile
        )

        return redirect('login')

    return render(request, 'Authentication/register.html')


# 🔐 Login Page (JWT generate + session store)
def login_page(request):
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")

        try:
            user_obj = User.objects.get(email=email)
        except User.DoesNotExist:
            return render(request, 'Authentication/login.html', {"error": "Invalid credentials"})

        user = authenticate(username=user_obj.username, password=password)

        if user is not None:
            refresh = RefreshToken.for_user(user)

            response = redirect('profile')   
            response.set_cookie(
                key='access',
                value=str(refresh.access_token),
                httponly=True,   # 🔐 can't access via JS
                secure=False,    # True in production (HTTPS)
                samesite='Lax'
            )

            response.set_cookie(
                key='refresh',
                value=str(refresh),
                httponly=True,
                secure=False,
                samesite='Lax'
            )

            return response
        else:
            return render(request, 'Authentication/login.html', {"error": "Invalid credentials"})

    return render(request, 'Authentication/login.html')


# 🏠 Dashboard (Protected)
def dashboard(request):
    token = request.session.get('access')

    if not token:
        return redirect('login')

    return render(request, 'Authentication/dashboard.html')


# 🚪 Logout
def logout_view(request):
    response = redirect('login')
    response.delete_cookie('access')
    response.delete_cookie('refresh')
    return response


# USER PROFILE
def profile(request):
    user = get_user_from_token(request)

    if not user:
        return redirect('login')

    search_query = request.GET.get('search', '')

    tickets = Ticket.objects.filter(user=user)

    if search_query:
        tickets = tickets.filter(title__icontains=search_query)

    paginator = Paginator(tickets, 5)  # 5 per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'UserProfile/profile.html', {
        # "page_obj": page_obj,
        # "search_query": search_query,
        "tickets": tickets,
        "user": user
        
    })
# CREATE TICKET
def create_ticket(request):
    user = get_user_from_token(request)

    if not user:
        return redirect('login')

    if request.method == "POST":
        title = request.POST.get("title")
        description = request.POST.get("description")
        image = request.FILES.get("image")
        document = request.FILES.get("document")

        ticket = Ticket.objects.create(
            user=user,
            title=title,
            description=description,
            image=image,
            document=document
        )

        # Send email
        send_mail(
            subject="New Ticket Created",
            message=f"Ticket '{title}' created by {user.username}",
            from_email="aniketsrivastava57@gmail.com",
            recipient_list=["aniketsrivastava57@gmail.com"],
        )

        return redirect('profile')

    return render(request, 'UserProfile/create_ticket.html')