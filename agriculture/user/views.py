import random, time
from tokenize import Comment
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
from user.models import Ticket ,TicketComment,TicketImage
from .serializers import RegisterSerializer,LoginSerializer,UserSerializer
from django.contrib.auth import authenticate, logout
from .models import Profile, Purchase, TicketImage
from .models import TrackingUser
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.http import require_POST
from django.contrib.auth import authenticate, login



# Create your views here.
class RegisterView(generics.CreateAPIView):
    queryset= User.objects.all()
    permission_classes=[AllowAny]
    serializer_class=RegisterSerializer


def landing_page(request):
    return render(request, 'landingpage/landing.html')

def login_page(request):
    if request.method == "POST":
        mobile = request.POST.get("mobile")
        print("Mobile entered:", mobile)

        # 🔥 DEBUG: check purchases linked to this mobile
        purchases = Purchase.objects.filter(user__profile__mobile=mobile)
        print("Purchase count:", purchases.count())

        if not purchases.exists():
          
            return render(request, 'Authentication/login.html', {
               
            })

        print("✅ Purchase found, sending OTP")

        # OTP generate
        otp = random.randint(1000, 9999)
        request.session['otp'] = str(otp)
        request.session['mobile'] = mobile
        request.session['otp_time'] = time.time()

        print("OTP:", otp)

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
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password
        )
        Profile.objects.create(
            user=user,
            mobile=mobile
        )

        return redirect('login')

    return render(request, 'Authentication/register.html')


# # 🏠 Dashboard (Protected)
# def dashboard(request):
#     token = request.session.get('access')

#     if not token:
#         return redirect('login')

#     return render(request, 'Authentication/dashboard.html')


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
    has_purchase = Purchase.objects.filter(user=user).exists()

    if search_query:
        tickets = tickets.filter(title__icontains=search_query)

    paginator = Paginator(tickets, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'UserProfile/profile.html', {
        "page_obj": page_obj, 
        "search_query": search_query,
        "user": user,
        'has_purchase': has_purchase
    })


# CREATE TICKET
def create_ticket(request):
    user = get_user_from_token(request)

    if not user:
        return redirect('login')

    
    purchases = Purchase.objects.filter(user=user)

    if request.method == "POST":
        title = request.POST.get("title")
        description = request.POST.get("description")
        purchase_id = request.POST.get("purchase")
        category = request.POST.get("category") 

        image = request.FILES.get("image")
        document = request.FILES.get("document")
        other = request.POST.get("other")

        
        purchase = Purchase.objects.get(id=purchase_id, user=user)

        ticket = Ticket.objects.create(
            user=user,
            title=title,
            description=description,
            purchase=purchase,
            category=category,
            image=image,
            document=document,
            other=other 
        )

        images = request.FILES.getlist("images")
        for img in images:
            TicketImage.objects.create(ticket=ticket, image=img)

        return redirect('profile')

    
    return render(request, 'UserProfile/create_ticket.html', {
        'purchases': purchases
    })



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

            # 🔥 CHECK PROFILE EXIST OR NOT
            profile = Profile.objects.filter(mobile=mobile).first()

            if not profile:
                # 🔥 AUTO REGISTER
                user = User.objects.create(username=mobile)
                profile = Profile.objects.create(user=user, mobile=mobile)
            else:
                user = profile.user

            # 🔥 JWT TOKEN
            refresh = RefreshToken.for_user(user)

            response = redirect('profile')
            response.set_cookie('access', str(refresh.access_token), httponly=True)
            response.set_cookie('refresh', str(refresh), httponly=True)

            return response

        else:
            return render(request, 'Authentication/verify_otp.html', {
                "error": "Invalid OTP"
            })

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


def ticket_chat(request, ticket_id):
    user = get_user_from_token(request)   # 🔥 IMPORTANT

    if not user:
        return redirect("login")

    ticket = get_object_or_404(Ticket, id=ticket_id)
    chats = TicketComment.objects.filter(ticket=ticket).order_by("created_at")

    if request.method == "POST":
        message = request.POST.get("message")

        if message:
            TicketComment.objects.create(
                ticket=ticket,
                sender=get_user_from_token(request),
                message=message
            )

        return redirect("ticket_chat", ticket_id=ticket.id)

    return render(request, "Ticket/ticket_chat.html", {
        "ticket": ticket,
        "chats": chats
    })

def admin_reply(request, ticket_id):
    ticket = Ticket.objects.get(id=ticket_id)

    if request.method == "POST":
        message = request.POST.get("message")

        TicketComment.objects.create(
            ticket=ticket,
            sender=request.user,
            message=message,
            is_read=False  
        )

    return redirect("admin_dashboard")




@staff_member_required
def admin_ticket_chat(request, ticket_id):
    ticket = get_object_or_404(Ticket, id=ticket_id)
    chats = TicketComment.objects.filter(ticket=ticket).order_by("created_at")

    if request.method == "POST":
        message = request.POST.get("message")
        image = request.FILES.get("image")

        if message or image:
            TicketComment.objects.create(
                ticket=ticket,
                sender=request.user,  
                message=message,
                image=image
            )

        return redirect("admin_ticket_chat", ticket_id=ticket.id)

    return render(request, "admin_ticket_chat.html", {
        "ticket": ticket,
        "chats": chats
    })

#dashboard
def admin_login(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user is not None:
            # ✅ ONLY ADMIN / STAFF ALLOWED
            if user.is_staff or user.is_superuser:
                login(request, user)
                return redirect('admin_dashboard')
            else:
                return render(request, 'login.html', {
                    "error": "You are not authorized to access admin dashboard"
                })
        else:
            return render(request, 'login.html', {
                "error": "Invalid username or password"
            })

    return render(request, 'Dashboard/login.html')

@login_required(login_url='admin_login')
def admin_dashboard(request):

    # 🔐 only staff allowed
    if not request.user.is_staff:
        return redirect('admin_login')

    # 📊 ticket stats
    total = Ticket.objects.count()
    pending = Ticket.objects.filter(status='pending').count()
    resolved = Ticket.objects.filter(status='resolved').count()
    in_progress = Ticket.objects.filter(status='in_progress').count()

    tickets = Ticket.objects.all().order_by('-created_at')
    staff_users = User.objects.filter(is_staff=True)

    # 🔔 new tickets notifications
    new_tickets = Ticket.objects.filter(status='pending').order_by('-created_at')[:5]

    # 💬 unread messages (FIXED)
    unread_messages = TicketComment.objects.filter(
        is_read=False
    ).order_by('-created_at')[:5]

    unread_count = TicketComment.objects.filter(
        is_read=False
    ).count()

    return render(request, 'Dashboard/index.html', {
        'total': total,
        'pending': pending,
        'resolved': resolved,
        'in_progress': in_progress,
        'tickets': tickets,
        'staff_users': staff_users,

       
        'new_tickets': new_tickets,

        'unread_messages': unread_messages,
        'unread_count': unread_count
    })

def assign_ticket(request, ticket_id):
    if not request.user.is_superuser:
        return redirect('admin_dashboard')

    ticket = get_object_or_404(Ticket, id=ticket_id)

    if request.method == "POST":
        staff_id = request.POST.get("staff_id")

        staff = get_object_or_404(User, id=staff_id, is_staff=True)  

        ticket.assigned_to = staff
        ticket.status = "in_progress"
        ticket.save()

        return redirect('admin_dashboard')
    

def admin_login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user is not None and (user.is_staff or user.is_superuser):
            login(request, user)
            return redirect('admin_dashboard')
        else:
            return render(request, 'Dashboard/login.html', {
                "error": "Only admin/staff allowed"
            })

    return render(request, 'Dashboard/login.html')

def admin_ticket_chat(request, ticket_id):
    ticket = get_object_or_404(Ticket, id=ticket_id)

    # ✅ mark messages as read
    TicketComment.objects.filter(
        ticket=ticket,
        sender='user',
        is_read=False
    ).update(is_read=True)

    messages = ticket.messages.all()

    return render(request, 'Dashboard/chat.html', {
        'ticket': ticket,
        'messages': messages
    })

def admin_logout(request):
    logout(request)
    return redirect('login')