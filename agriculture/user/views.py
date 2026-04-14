import random, time
from django.shortcuts import get_object_or_404, redirect, render
from rest_framework import generics
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import AllowAny
from django.contrib.auth.models import User
import jwt
from django.http import HttpResponse, JsonResponse
import random
from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.conf import settings
from django.contrib.auth.models import User
from user.models import Ticket
from .serializers import RegisterSerializer,LoginSerializer,UserSerializer
from django.contrib.auth import authenticate
from .models import Profile
from .models import TrackingUser

# Create your views here.
class RegisterView(generics.CreateAPIView):
    queryset= User.objects.all()
    permission_classes=[AllowAny]
    serializer_class=RegisterSerializer


def login_page(request):
    if request.method == "POST":
        mobile = request.POST.get("mobile")
        print("POST came to login_page")

        try:
            profile = Profile.objects.get(mobile=mobile)
            print("Profile found")
        except Profile.DoesNotExist:
            print("Profile not found")
            return render(request, 'Authentication/login.html', {
                "error": "Mobile not registered"
            })

        otp = random.randint(1000, 9999)
        request.session['otp'] = str(otp)
        request.session['mobile'] = mobile
        request.session['otp_time'] = time.time()

        print("OTP:", otp)
        print("Before redirect")

        return redirect('verify_otp')

    return render(request, 'Authentication/login.html')




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

    paginator = Paginator(tickets, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'UserProfile/profile.html', {
        "page_obj": page_obj, 
        "search_query": search_query,
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


def verify_otp(request):
    if request.method == "POST":
        entered_otp = request.POST.get("otp")

        session_otp = request.session.get('otp')
        mobile = request.session.get('mobile')

        if not session_otp or not mobile:
            return render(request, 'Authentication/verify_otp.html', {
                "error": "Session expired. Please login again."
            })

        if entered_otp == session_otp:
            profile = Profile.objects.get(mobile=mobile)
            user = profile.user

            refresh = RefreshToken.for_user(user)

            response = redirect('check_tracking')
            response.set_cookie('access', str(refresh.access_token), httponly=True)
            response.set_cookie('refresh', str(refresh), httponly=True)

            return response
        else:
            return render(request, 'Authentication/verify_otp.html', {
                "error": "Invalid OTP"
            })

    # ✅ ALWAYS SHOW PAGE
    return render(request, 'Authentication/verify_otp.html') 

   

def resend_otp(request):
    mobile = request.session.get('mobile')

    if not mobile:
        return redirect('login')

    otp = random.randint(1000, 9999)

    request.session['otp'] = str(otp)
    request.session['otp_time'] = time.time()

    print("New OTP:", otp)

    return redirect('verify_otp')

# TRACKING PART
def check_tracking(request):
    if request.method == "POST":
        tracking_id = request.POST.get("tracking_id")

        user = TrackingUser.objects.filter(tracking_id=tracking_id).first()

        if user:
            # SAVE SESSION (VERY IMPORTANT)
            request.session["tracking_verified"] = True
            request.session["tracking_id"] = tracking_id

            print("Verified successfully")

            # 🔥 REDIRECT TO PROFILE
            return redirect("profile")

        else:
            return render(request, "UserProfile/check_tracking.html", {
                "error": "Invalid Tracking ID"
            })
    return render(request, "UserProfile/check_tracking.html")

def get_tickets(request):
    tickets = Ticket.objects.filter(user=request.user).order_by('-id')

    data = []
    for t in tickets:
        data.append({
            "title": t.title,
            "description": t.description,
            "status": t.status
        })

    return JsonResponse({"tickets": data})

