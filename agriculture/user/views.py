import random, time
from tokenize import Comment
from django.shortcuts import get_object_or_404, redirect, render
from rest_framework import generics
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import AllowAny
from django.contrib.auth.models import User
import jwt
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
import random
from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.conf import settings
from django.contrib.auth.models import User
from user.models import Ticket, TicketComment, TicketImage, StaffProfile
from .serializers import RegisterSerializer, LoginSerializer, UserSerializer
from django.contrib.auth import authenticate, logout
from .models import AdminChat, Profile, Purchase, TicketImage
from .models import TrackingUser
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.http import require_POST
from django.contrib.auth import authenticate, login
from django.db.models import Q
from django.contrib import messages


# =============================================
# ✅ CUSTOM DECORATORS
# =============================================

def admin_session_required(view_func):
    """Admin ke liye — sirf wahi access kar sakta hai jisne admin login kiya ho"""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('admin_login')
        if request.session.get('role') != 'admin':
            return redirect('admin_login')
        if not request.user.is_staff:
            return redirect('admin_login')
        return view_func(request, *args, **kwargs)
    return wrapper


def staff_session_required(view_func):
    """Staff ke liye — sirf wahi access kar sakta hai jisne staff login kiya ho"""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('staff_login')
        if request.session.get('role') != 'staff':
            return redirect('staff_login')
        profile = StaffProfile.objects.filter(user=request.user).first()
        if not profile or not profile.is_approved:
            return redirect('staff_login')
        return view_func(request, *args, **kwargs)
    return wrapper


# =============================================
# 🔐 REGISTER VIEW (API)
# =============================================
class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = [AllowAny]
    serializer_class = RegisterSerializer


# =============================================
# 🏠 LANDING PAGE
# =============================================
def landing_page(request):
    return render(request, 'landingpage/landing.html')


# =============================================
# 📱 USER LOGIN (OTP based)
# =============================================
def login_page(request):
    if request.method == "POST":
        mobile = request.POST.get("mobile", "").strip()

        if not mobile:
            return render(request, 'Authentication/login.html', {
                "error": "Mobile number required"
            })

        # ✅ Sirf profile check karo
        profile = Profile.objects.filter(mobile=mobile).first()

        if not profile:
            return render(request, 'Authentication/login.html', {
                "error": "Mobile number registered nahi hai"
            })

        otp = random.randint(1000, 9999)
        request.session['otp'] = str(otp)
        request.session['mobile'] = mobile
        request.session['otp_time'] = time.time()

        print(f"OTP: {otp}")  

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

        if User.objects.filter(username=username).exists():
            return render(request, 'Authentication/register.html', {"error": "Username already exists"})

        if User.objects.filter(email=email).exists():
            return render(request, 'Authentication/register.html', {"error": "Email already exists"})

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password
        )
        Profile.objects.create(user=user, mobile=mobile)

        return redirect('login')

    return render(request, 'Authentication/register.html')


# =============================================
# 🚪 USER LOGOUT
# =============================================
def logout_view(request):
    response = redirect('login')
    response.delete_cookie('access')
    response.delete_cookie('refresh')
    return response


# =============================================
# 👤 USER PROFILE
# =============================================
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


# =============================================
# 🎫 CREATE TICKET
# =============================================
def create_ticket(request):
    user = get_user_from_token(request)

    if not user:
        return redirect('login')

    purchases = Purchase.objects.filter(user=user).values('purchase_id').distinct()
    selected_purchase = request.GET.get('purchase')
    products = None

    if selected_purchase:
        products = Purchase.objects.filter(user=user, purchase_id=selected_purchase)

    if request.method == "POST":
        purchase_id = request.POST.get("purchase")
        product = request.POST.get("product")
        images = request.FILES.getlist("images")
        document = request.FILES.get("document")

        purchase = Purchase.objects.get(
            user=user,
            purchase_id=purchase_id,
            product_name=product
        )

        ticket = Ticket.objects.create(
            user=user,
            purchase=purchase,
            title=request.POST.get("title"),
            description=request.POST.get("description"),
            category=request.POST.get("category"),
            other=request.POST.get("other"),
            document=document
        )

        for img in images:
            TicketImage.objects.create(ticket=ticket, image=img)

        messages.success(request, "Ticket created successfully!")
        return redirect('profile')

    return render(request, 'UserProfile/create_ticket.html', {
        'purchases': purchases,
        'products': products,
        'selected_purchase': selected_purchase
    })


# =============================================
# 🔢 OTP VERIFY
# =============================================
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
            profile = Profile.objects.filter(mobile=mobile).first()

            if not profile:
                user = User.objects.create(username=mobile)
                profile = Profile.objects.create(user=user, mobile=mobile)
            else:
                user = profile.user

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


# =============================================
# 📦 TRACKING
# =============================================
def check_tracking(request):
    if request.method == "POST":
        tracking_id = request.POST.get("tracking_id")
        user = TrackingUser.objects.filter(tracking_id=tracking_id).first()

        if user:
            request.session["tracking_verified"] = True
            request.session["tracking_id"] = tracking_id
            print("Verified successfully")
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


# =============================================
# 💬 USER TICKET CHAT
# =============================================
def ticket_chat(request, ticket_id):
    user = get_user_from_token(request)

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

        return redirect('user_ticket_chat', ticket_id=ticket.id)

    return render(request, "Ticket/ticket_chat.html", {
        "ticket": ticket,
        "chats": chats
    })


# =============================================
# 🔐 ADMIN LOGIN — role = 'admin' set hoga
# =============================================
def admin_login(request):
    if request.user.is_authenticated and request.session.get('role') == 'admin':
        return redirect('admin_dashboard')

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user is not None:
            # ✅ SIRF SUPERUSER — staff allowed nahi
            if user.is_superuser:
                login(request, user)
                request.session['role'] = 'admin'
                return redirect('admin_dashboard')
            else:
                return render(request, 'Dashboard/login.html', {
                    "error": "You are not authorized to access admin dashboard"
                })
        else:
            return render(request, 'Dashboard/login.html', {
                "error": "Invalid username or password"
            })

    return render(request, 'Dashboard/login.html')


# =============================================
# 📊 ADMIN DASHBOARD — sirf admin role wala access kar sakta hai
# =============================================
@admin_session_required
def admin_dashboard(request):

    selected_user = request.GET.get('user')
    selected_purchase = request.GET.get('purchase_id')

    tickets = Ticket.objects.all().order_by('-created_at')

    if selected_user:
        tickets = tickets.filter(user_id=selected_user)

    total = tickets.count()
    pending = tickets.filter(status='pending').count()
    resolved = tickets.filter(status='resolved').count()
    in_progress = tickets.filter(status='in_progress').count()

    users = User.objects.filter(ticket__isnull=False).distinct()
    staff_users = User.objects.filter(is_staff=True)

    new_tickets = Ticket.objects.filter(status='pending').order_by('-created_at')[:5]

    unread_messages = TicketComment.objects.filter(
    is_read=False,
    sender__is_staff=False,
    sender__is_superuser=False
    ).order_by('-created_at')[:5]

    unread_count = TicketComment.objects.filter(
        is_read=False,
        sender__is_staff=False,
        sender__is_superuser=False
    ).count()

    tickets_with_messages = Ticket.objects.filter(
        chats__sender__is_staff=False
    ).distinct().order_by('-created_at')

    if selected_user:
        tickets_with_messages = tickets_with_messages.filter(user_id=selected_user)

    gallery_tickets = Ticket.objects.all().order_by('-created_at')

    if selected_user:
        gallery_tickets = gallery_tickets.filter(user_id=selected_user)

    if selected_purchase:
        gallery_tickets = gallery_tickets.filter(purchase__purchase_id=selected_purchase)

    if selected_user:
        purchases = Purchase.objects.filter(user_id=selected_user).distinct()
    else:
        purchases = Purchase.objects.none()

    return render(request, 'Dashboard/index.html', {
        'total': total,
        'pending': pending,
        'resolved': resolved,
        'in_progress': in_progress,
        'tickets': tickets,
        'staff_users': staff_users,
        'new_tickets': new_tickets,
        'unread_messages': unread_messages,
        'unread_count': unread_count,
        'tickets_with_messages': tickets_with_messages,
        'users': users,
        'purchases': purchases,
        'selected_user': selected_user,
        'selected_purchase': selected_purchase,
        'gallery_tickets': gallery_tickets,
    })


# =============================================
# 🚪 ADMIN LOGOUT — sirf admin ka session clear
# =============================================
def admin_logout(request):
    request.session.flush()
    return redirect('admin_login')


# =============================================
# 🎟️ ADMIN TICKET VIEWS
# =============================================
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


@admin_session_required
def admin_ticket_chat(request, ticket_id):
    ticket = get_object_or_404(Ticket, id=ticket_id)
    tickets = Ticket.objects.all()
    messages = TicketComment.objects.filter(ticket=ticket).order_by('created_at')

    if request.method == "POST":
        msg = request.POST.get("message")

        TicketComment.objects.create(
            ticket=ticket,
            message=msg,
            sender=request.user
        )

        return redirect('admin_ticket_chat', ticket_id=ticket.id)

    return render(request, 'Dashboard/chat.html', {
        'ticket': ticket,
        'tickets': tickets,
        'messages': messages
    })


@admin_session_required
def admin_view_ticket(request, id):
    ticket = get_object_or_404(Ticket, id=id)
    messages = TicketComment.objects.filter(ticket=ticket).order_by('created_at')


    TicketComment.objects.filter(
        ticket=ticket,
        is_read=False,
        sender__is_staff=False,
        sender__is_superuser=False
    ).update(is_read=True)

    if request.method == "POST":
        msg = request.POST.get("message")

        if msg:
            TicketComment.objects.create(
                ticket=ticket,
                message=msg,
                sender=request.user
            )

        return redirect('admin_view_ticket', id=id)

    return render(request, 'Dashboard/view_ticket.html', {
        't': ticket,
        'messages': messages
    })


@admin_session_required
def view_image(request, ticket_id):
    ticket = get_object_or_404(Ticket, id=ticket_id)

    return render(request, 'Dashboard/index.html', {
        'ticket': ticket
    })


def update_ticket_status(request, ticket_id):
    if not request.user.is_staff or request.session.get('role') != 'admin':
        return redirect('admin_login')

    ticket = get_object_or_404(Ticket, id=ticket_id)

    if request.method == "POST":
        status = request.POST.get("status")

        if status in ["pending", "in_progress", "resolved"]:
            ticket.status = status
            ticket.save()

    return redirect('admin_dashboard')


def assign_ticket(request, ticket_id):
    if not request.user.is_superuser or request.session.get('role') != 'admin':
        return redirect('admin_dashboard')

    ticket = get_object_or_404(Ticket, id=ticket_id)

    if request.method == "POST":
        staff_id = request.POST.get("staff_id")
        staff = User.objects.get(id=staff_id)

        ticket.assigned_to = staff
        ticket.status = "in_progress"
        ticket.save()

        return redirect('admin_dashboard')


# =============================================
# 💬 ADMIN CHAT
# =============================================
@admin_session_required
def admin_chat_list(request):
    users = User.objects.filter(is_staff=True).exclude(id=request.user.id)

    return render(request, 'Dashboard/chat_list.html', {
        'users': users
    })


@admin_session_required
def admin_chat_detail(request, user_id):
    other_user = get_object_or_404(User, id=user_id)

    messages = AdminChat.objects.filter(
        Q(sender=request.user, receiver=other_user) |
        Q(sender=other_user, receiver=request.user)
    ).order_by('created_at')

    AdminChat.objects.filter(
        sender=other_user,
        receiver=request.user,
        is_read=False
    ).update(is_read=True)

    return render(request, 'Dashboard/chat_detail.html', {
        'messages': messages,
        'other_user': other_user
    })


def send_admin_message(request, user_id):
    if request.method == "POST":
        msg = request.POST.get("message")
        receiver = User.objects.get(id=user_id)

        AdminChat.objects.create(
            sender=request.user,
            receiver=receiver,
            message=msg
        )

    return redirect('admin_chat_detail', user_id=user_id)


# =============================================
# 👥 ADMIN STAFF MANAGEMENT
# =============================================
@admin_session_required
def admin_staff_list(request):
    staffs = StaffProfile.objects.all().order_by('-id')

    pending_staff_count = StaffProfile.objects.filter(is_approved=False).count()
    approved_staff_count = StaffProfile.objects.filter(is_approved=True).count()

    return render(request, "Dashboard/manage_staff.html", {
        "staffs": staffs,
        "pending_staff_count": pending_staff_count,
        "approved_staff_count": approved_staff_count,
    })


@admin_session_required
def approve_staff(request, id):
    if not request.user.is_superuser:
        return redirect("admin_login")

    profile = get_object_or_404(StaffProfile, id=id)
    profile.is_approved = True
    profile.user.is_staff = True
    profile.user.save()
    profile.save()

    return redirect("admin_staff_list")


@admin_session_required
def reject_staff(request, id):
    if not request.user.is_superuser:
        return redirect("admin_login")

    profile = get_object_or_404(StaffProfile, id=id)
    profile.delete()

    return redirect("admin_staff_list")


# =============================================
# 🧑‍💻 STAFF REGISTER
# =============================================
def staff_register(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        if User.objects.filter(username=username).exists():
            return render(request, "Staff_dashboard/register.html", {
                "error": "Username already exists"
            })

        user = User.objects.create_user(username=username, password=password)
        user.is_staff = False
        user.is_superuser = False
        user.save()

        StaffProfile.objects.create(user=user)

        return render(request, "Staff_dashboard/register.html", {
            "msg": "✅ Request sent to admin"
        })

    return render(request, "Staff_dashboard/register.html")


# =============================================
# 🔐 STAFF LOGIN — role = 'staff' set hoga
# =============================================
def staff_login(request):
    # ✅ Agar already staff session hai toh dashboard pe bhejo
    if request.user.is_authenticated and request.session.get('role') == 'staff':
        return redirect('staff_dashboard')

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user is None:
            return render(request, "staff_dashboard/login.html", {
                "error": "Invalid credentials"
            })

        if not user.is_staff:
            return render(request, "staff_dashboard/login.html", {
                "error": "Not a staff account"
            })

        profile = StaffProfile.objects.filter(user=user).first()

        if not profile:
            return render(request, "staff_dashboard/login.html", {
                "error": "Profile not found"
            })

        if not profile.is_approved:
            return render(request, "staff_dashboard/login.html", {
                "error": "Waiting for admin approval"
            })

        login(request, user)
        # ✅ IMPORTANT: Staff ka role session mein save karo
        request.session['role'] = 'staff'

        return redirect("staff_dashboard")

    return render(request, "staff_dashboard/login.html")


# =============================================
# 📊 STAFF DASHBOARD — sirf staff role wala access kar sakta hai
# =============================================
@staff_session_required
def staff_dashboard(request):
    user = request.user

    try:
        profile = StaffProfile.objects.get(user=user)
    except StaffProfile.DoesNotExist:
        return redirect("staff_login")

    if not profile.is_approved:
        return redirect("staff_login")

    tickets = Ticket.objects.filter(
        assigned_to=user
    ).select_related("user", "purchase").order_by("-id")

    total = tickets.count()
    pending = tickets.filter(status="pending").count()
    in_progress = tickets.filter(status="in_progress").count()
    resolved = tickets.filter(status="resolved").count()

    recent_messages = TicketComment.objects.filter(
        ticket__assigned_to=user
    ).select_related("ticket", "ticket__user").order_by("-id")[:5]

    unread_messages_count = TicketComment.objects.filter(
        ticket__assigned_to=user,
        is_read=False
    ).count()

    assigned_tickets = tickets[:5]
    assigned_count = tickets.count()

    return render(request, "staff_dashboard/staff_dashboard.html", {
        "tickets": tickets,
        "total": total,
        "pending": pending,
        "in_progress": in_progress,
        "resolved": resolved,
        "recent_messages": recent_messages,
        "unread_messages_count": unread_messages_count,
        "assigned_tickets": assigned_tickets,
        "assigned_count": assigned_count,
    })


# =============================================
# 🚪 STAFF LOGOUT — sirf staff ka session clear
# =============================================
def staff_logout(request):
    request.session.flush()
    return redirect('staff_login')


# =============================================
# 🎟️ STAFF TICKET VIEWS
# =============================================
@staff_session_required
def staff_ticket_chat(request, ticket_id):
    ticket = Ticket.objects.get(id=ticket_id, assigned_to=request.user)
    messages = TicketComment.objects.filter(ticket=ticket)

    if request.method == "POST":
        msg = request.POST.get("message")

        TicketComment.objects.create(
            ticket=ticket,
            sender=request.user,
            message=msg
        )

        return redirect('staff_ticket_chat', ticket_id=ticket.id)

    return render(request, "staff_dashboard/staff_ticket_chat.html", {
        "ticket": ticket,
        "messages": messages
    })


@staff_session_required
def staff_view_ticket(request, id):
    ticket = get_object_or_404(Ticket, id=id)

    if ticket.assigned_to != request.user:
        return HttpResponseForbidden("Not allowed")

    TicketComment.objects.filter(
        ticket=ticket,
        sender=ticket.user,
        is_read=False
    ).update(is_read=True)

    if request.method == "POST":
        msg = request.POST.get("message")
        if msg:
            TicketComment.objects.create(
                ticket=ticket,
                sender=request.user,
                message=msg
            )
        return redirect("staff_view_ticket", id=id)

    comments = TicketComment.objects.filter(ticket=ticket).order_by("created_at")

    return render(request, 'staff_dashboard/view_ticket.html', {
        'ticket': ticket,
        'comments': comments,
    })


@staff_session_required
def update_ticket(request, id):
    ticket = get_object_or_404(Ticket, id=id)

    if request.method != "POST":
        return HttpResponseForbidden("Invalid request")

    if ticket.assigned_to != request.user:
        return HttpResponseForbidden("Not allowed")

    status = request.POST.get("status")
    if status in ["pending", "in_progress", "resolved"]:
        ticket.status = status
        ticket.save()

    return redirect("staff_dashboard")


# =============================================
# 🛡️ HELPER DECORATORS (backup)
# =============================================
def staff_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("staff_login")
        if not request.user.is_staff:
            return redirect("staff_login")
        if request.session.get('role') != 'staff':
            return redirect("staff_login")
        profile = StaffProfile.objects.filter(user=request.user).first()
        if not profile or not profile.is_approved:
            return redirect("staff_login")
        return view_func(request, *args, **kwargs)
    return wrapper


def admin_only(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_staff or request.session.get('role') != 'admin':
            return HttpResponseForbidden("Access Denied")
        return view_func(request, *args, **kwargs)
    return wrapper