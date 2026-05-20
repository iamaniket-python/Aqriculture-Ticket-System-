import logging
from xml.dom import ValidationErr
from django.utils import timezone
from datetime import timedelta
import json
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.views.decorators.cache import never_cache
from datetime import datetime
from rest_framework import generics
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from django.core.exceptions import ValidationError

from user.models import (
    AdminChat, Profile, Purchase,
    Ticket, TicketComment, TicketImage, StaffProfile, TrackingUser,
)
from .serializers import RegisterSerializer
from .decorators import (
    admin_session_required, staff_session_required,
    login_required_token, clear_staff_cache,
)
from .services.auth_service import (
    get_user_from_token, set_auth_cookies, delete_auth_cookies,
    generate_otp, verify_otp, can_resend_otp,
)
from .services.ticket_service import TicketService

logger = logging.getLogger(__name__)


# =============================================
# 🔐 REGISTER VIEW (API)
# =============================================

class RegisterView(generics.CreateAPIView):
    queryset           = User.objects.all()
    permission_classes = [AllowAny]
    serializer_class   = RegisterSerializer


# =============================================
# 🏠 LANDING PAGE
# =============================================

def landing_page(request):
    return render(request, 'landingpage/landing.html')


# =============================================
# 📱 USER REGISTER
# =============================================

def register(request):
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        email    = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")
        mobile   = request.POST.get("mobile", "").strip()

        if not username or not email or not password or not mobile:
            return render(request, 'Authentication/register.html', {
                "error": "All fields are required."
            })

        if not mobile.isdigit() or len(mobile) != 10:
            return render(request, 'Authentication/register.html', {
                "error": "Enter a valid 10-digit mobile number."
            })

        if User.objects.filter(username=username).exists():
            return render(request, 'Authentication/register.html', {
                "error": "Username already exists"
            })

        if User.objects.filter(email=email).exists():
            return render(request, 'Authentication/register.html', {
                "error": "Email already exists"
            })

        user = User.objects.create_user(username=username, email=email, password=password)
        Profile.objects.create(user=user, mobile=mobile)
        messages.success(request, "Account created! Please login.")
        return redirect('login')

    return render(request, 'Authentication/register.html')


# =============================================
# 📱 USER LOGIN (OTP based)
# =============================================

@never_cache
def login_page(request):
    if request.method == "POST":
        mobile = request.POST.get("mobile", "").strip()

        if not mobile or not mobile.isdigit() or len(mobile) != 10:
            return render(request, 'Authentication/login.html', {
                "error": "Valid 10-digit mobile number required"
            })


       


        # if not Profile.objects.filter(mobile=mobile).exists():
        #     return render(request, 'Authentication/login.html', {
        #         "error": "Mobile number is not registered"
        #     })

        # ✅ TEMPORARY: Skip OTP for testing
        profile = Profile.objects.filter(mobile=mobile).first()
        user = profile.user
        refresh = RefreshToken.for_user(user)
        response = redirect('profile')
        set_auth_cookies(response, refresh)
        return response

    return render(request, 'Authentication/login.html')


# =============================================
# 🔢 OTP VERIFY
# =============================================

@never_cache
def verify_otp_view(request):
    if request.method == "POST":
        entered = request.POST.get("otp", "").strip()
        mobile  = request.session.get('pending_mobile')

        if not mobile:
            return render(request, 'Authentication/verify_otp.html', {
                "error": "Session expired. Please login again."
            })

        if not entered or not entered.isdigit():
            return render(request, 'Authentication/verify_otp.html', {
                "error": "Invalid OTP format."
            })

        success, error_msg = verify_otp(mobile, entered)

        if not success:
            return render(request, 'Authentication/verify_otp.html', {
                "error": error_msg
            })

        profile = Profile.objects.filter(mobile=mobile).first()
        if profile:
            user = profile.user
        else:
            user = User.objects.create(username=mobile)
            Profile.objects.create(user=user, mobile=mobile)

        request.session.pop('pending_mobile', None)

        refresh  = RefreshToken.for_user(user)
        response = redirect('profile')
        set_auth_cookies(response, refresh)
        return response

    return render(request, 'Authentication/verify_otp.html')


# =============================================
# 🔁 RESEND OTP
# =============================================

def resend_otp(request):
    mobile = request.session.get('pending_mobile')

    if not mobile:
        return redirect('login')

    if not can_resend_otp(mobile):
        messages.error(request, "Please wait 60 seconds before requesting a new OTP.")
        return redirect('verify_otp')

    try:
        generate_otp(mobile)
        # ✅ Fast2SMS handles delivery automatically
        messages.success(request, "OTP resent successfully.")

    except PermissionError as e:
        messages.error(request, str(e))

    except RuntimeError:
        messages.error(request, "Could not resend OTP. Please try again.")

    return redirect('verify_otp')


# =============================================
# 🚪 USER LOGOUT
# =============================================

def logout_view(request):
    response = redirect('login')
    delete_auth_cookies(response)
    return response


# =============================================
# 👤 USER PROFILE
# =============================================

@login_required_token
def profile(request):
    user          = request._token_user
    product_query = request.GET.get('product', '')
    date_from     = request.GET.get('date_from', '')
    date_to       = request.GET.get('date_to', '')
    status_filter = request.GET.get('status', '')

    hour = datetime.now().hour

    if hour < 12:
        greeting = "Good Morning"
        emoji = "☀️"
    elif hour < 18:
        greeting = "Good Afternoon"
        emoji = "🌤️"
    else:
        greeting = "Good Evening"
        emoji = "🌙"

    has_purchase = Purchase.objects.filter(user=user).exists()

    # Cached tickets
    tickets = TicketService.get_user_tickets_cached(
        user,
        product=product_query,
        date_from=date_from,
        date_to=date_to,
    )

    # Status filter
    if status_filter:
        tickets = [t for t in tickets if t.status == status_filter]

    # Pagination
    per_page = int(request.GET.get('per_page', 10))
    paginator = Paginator(tickets, per_page)

    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Counts from DB
    base_qs = Ticket.objects.filter(user=user)

    pending_count = base_qs.filter(status='pending').count()
    progress_count = base_qs.filter(status='in_progress').count()
    resolved_count = base_qs.filter(status='resolved').count()

    return render(request, 'UserProfile/profile.html', {
        "page_obj": page_obj,
        "product_query": product_query,
        "date_from": date_from,
        "date_to": date_to,
        "status_filter": status_filter,
        "user": user,
        "has_purchase": has_purchase,
        "greeting": greeting,
        "emoji": emoji,
        "pending_count": pending_count,
        "progress_count": progress_count,
        "resolved_count": resolved_count,
    })

# =============================================
# 🎫 CREATE TICKET
# =============================================

@login_required_token
def create_ticket(request):

    user = request._token_user

    purchases = (
        Purchase.objects
        .filter(user=user)
        .values('purchase_id')
        .distinct()
    )

    selected_purchase = request.GET.get('purchase')

    products = None

    if selected_purchase:
        products = Purchase.objects.filter(
            user=user,
            purchase_id=selected_purchase
        )

    if request.method == "POST":

        selected_purchase_id = request.POST.get('purchase')
        selected_product     = request.POST.get('product')

        # ✅ Prevent duplicate pending ticket
        if selected_purchase_id and selected_product:

            pending_exists = Ticket.objects.filter(
                user=user,
                purchase__purchase_id=selected_purchase_id,
                purchase__product_name=selected_product,
                status='pending'
            ).exists()

            if pending_exists:

                messages.error(
                    request,
                    "❌ You already have a pending ticket for this product."
                )

                return render(request, 'UserProfile/create_ticket.html', {
                    'purchases': purchases,
                    'products': products,
                    'selected_purchase': selected_purchase,
                })

        try:

            TicketService.create_ticket(
                user=user,
                data=request.POST,
                images=request.FILES.getlist("images"),
                document=request.FILES.get("document"),
            )

            messages.success(request, "✅ Ticket created successfully!")

            return redirect('profile')

        except Purchase.DoesNotExist:

            messages.error(request, "Invalid purchase selected.")

        except ValidationError as e:

            messages.error(request, str(e))

        except Exception as e:

            logger.error(
                "Ticket creation failed for user %s: %s",
                user.id,
                str(e)
            )

            messages.error(
                request,
                "Something went wrong. Please try again."
            )

    return render(request, 'UserProfile/create_ticket.html', {
        'purchases': purchases,
        'products': products,
        'selected_purchase': selected_purchase,
    })
# =============================================
# 💬 USER TICKET CHAT
# =============================================

@login_required_token
def ticket_chat(request, ticket_id):
    user   = request._token_user
    ticket = get_object_or_404(Ticket, id=ticket_id, user=user)
    chats  = TicketComment.objects.filter(ticket=ticket)\
                                  .select_related('sender')\
                                  .order_by('created_at')

    if request.method == "POST":
        message = request.POST.get("message", "").strip()
        image   = request.FILES.get("image")
        if message:
            TicketService.add_comment(ticket, user, message, image=image)
        return redirect('user_ticket_chat', ticket_id=ticket.id)

    return render(request, "Ticket/ticket_chat.html", {
        "ticket": ticket,
        "chats":  chats,
    })


# =============================================
# 📦 TRACKING
# =============================================

def check_tracking(request):
    if request.method == "POST":
        tracking_id = request.POST.get("tracking_id", "").strip()

        if not tracking_id:
            return render(request, "UserProfile/check_tracking.html", {
                "error": "Please enter a tracking ID."
            })

        if TrackingUser.objects.filter(tracking_id=tracking_id).exists():
            request.session["tracking_verified"] = True
            request.session["tracking_id"]       = tracking_id
            return redirect("profile")

        logger.warning("Failed tracking attempt: %s", tracking_id)
        return render(request, "UserProfile/check_tracking.html", {
            "error": "Invalid Tracking ID"
        })

    return render(request, "UserProfile/check_tracking.html")


# =============================================
# 🔐 ADMIN LOGIN
# =============================================

@never_cache
def admin_login(request):
    if request.user.is_authenticated and request.session.get('role') == 'admin':
        return redirect('admin_dashboard')

    if request.method == "POST":
        email    = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")

        # ✅ Email ya username dono se login
        try:
            user_obj = User.objects.get(email=email)
            user     = authenticate(request, username=user_obj.username, password=password)
        except User.DoesNotExist:
            # ✅ Username se bhi try karo (fallback)
            user = authenticate(request, username=email, password=password)

        if user is not None and user.is_superuser:
            login(request, user)
            request.session['role'] = 'admin'
            logger.info("Admin login: %s from IP %s", email,
                        request.META.get('REMOTE_ADDR'))
            return redirect('admin_dashboard')

        logger.warning("Failed admin login: %s from IP %s",
                       email, request.META.get('REMOTE_ADDR'))
        return render(request, 'Dashboard/login.html', {
            "error": "Email or Password is Incorrect"
        })

    return render(request, 'Dashboard/login.html')


# =============================================
# 📊 ADMIN DASHBOARD
# =============================================

@admin_session_required
def admin_dashboard(request):
    # ✅ Save filters to session
    if request.method == 'GET' and any(k in request.GET for k in ['search', 'status', 'user', 'date_from', 'date_to', 'assigned']):
        request.session['admin_filters'] = {
            'search':            request.GET.get('search', ''),
            'status':            request.GET.get('status', ''),
            'selected_user':     request.GET.get('user', ''),
            'date_from':         request.GET.get('date_from', ''),
            'date_to':           request.GET.get('date_to', ''),
            'selected_assigned': request.GET.get('assigned', ''),
            'selected_purchase': request.GET.get('purchase_id', ''),
        }

    # ✅ Reset filters
    if 'reset' in request.GET:
        request.session.pop('admin_filters', None)

    # ✅ Load filters from session
    filters           = request.session.get('admin_filters', {})
    search            = filters.get('search', '')
    selected_status   = filters.get('status', '')
    selected_user     = filters.get('selected_user', '')
    date_from         = filters.get('date_from', '')
    date_to           = filters.get('date_to', '')
    selected_assigned = filters.get('selected_assigned', '')
    selected_purchase = filters.get('selected_purchase', '')

    stats   = TicketService.get_dashboard_stats(user_filter=selected_user)
    tickets = TicketService.get_dashboard_tickets(user_filter=selected_user)

    if search:
        tickets = tickets.filter(
            Q(user__username__icontains=search) |
            Q(title__icontains=search) |
            Q(description__icontains=search) |
            Q(purchase__purchase_id__icontains=search)
        )
    if date_from:
        tickets = tickets.filter(created_at__date__gte=date_from)
    if date_to:
        tickets = tickets.filter(created_at__date__lte=date_to)
    if selected_status:
        tickets = tickets.filter(status=selected_status)
    if selected_assigned == 'unassigned':
        tickets = tickets.filter(assigned_to__isnull=True)
    elif selected_assigned:
        tickets = tickets.filter(assigned_to__id=selected_assigned)

    paginator = Paginator(tickets, 10)
    page_obj  = paginator.get_page(request.GET.get('page'))

    users       = User.objects.filter(tickets__isnull=False).distinct()
    staff_users = User.objects.filter(is_staff=True)
    new_tickets = Ticket.objects.filter(status='pending').order_by('-created_at')[:5]

    unread_count = TicketService.get_unread_count_cached()

    # ✅ Sirf apne assigned ya unassigned tickets ke messages dikhao
    # Dusre staff ke assigned tickets ke messages hide honge
    unread_messages = TicketComment.objects.filter(
        is_read=False,
        sender__is_staff=False,
        sender__is_superuser=False,
    ).filter(
        Q(ticket__assigned_to=request.user) |   # apne assigned tickets
        Q(ticket__assigned_to__isnull=True)     # ya unassigned tickets
    ).select_related('ticket', 'sender').order_by('-created_at')[:5]

    gallery_tickets = Ticket.objects.select_related('user', 'purchase').order_by('-created_at')
    if selected_user:
        gallery_tickets = gallery_tickets.filter(user_id=selected_user)
    if selected_purchase:
        gallery_tickets = gallery_tickets.filter(purchase__purchase_id=selected_purchase)

    purchases = Purchase.objects.filter(user_id=selected_user).distinct() \
                if selected_user else Purchase.objects.none()

    # ✅ Per Day Chart — last 30 days data (7/14/30 filter frontend pe hoga)
    today = timezone.now().date()
    daily_chart_data = []
    for i in range(29, -1, -1):
        day = today - timedelta(days=i)
        daily_chart_data.append({
            'date':        day.strftime('%d %b'),
            'count':       Ticket.objects.filter(created_at__date=day).count(),
            'resolved':    Ticket.objects.filter(created_at__date=day, status='resolved').count(),
            'in_progress': Ticket.objects.filter(created_at__date=day, status='in_progress').count(),
        })

    # ✅ My Tickets — current admin/staff ko assign tickets
    my_tickets_count = Ticket.objects.filter(assigned_to=request.user).count()

    return render(request, 'Dashboard/index.html', {
        **stats,
        'page_obj':          page_obj,
        'tickets':           page_obj,
        'staff_users':       staff_users,
        'new_tickets':       new_tickets,
        'unread_messages':   unread_messages,
        'unread_count':      unread_count,
        'users':             users,
        'purchases':         purchases,
        'selected_user':     selected_user,
        'selected_purchase': selected_purchase,
        'gallery_tickets':   gallery_tickets,
        'search':            search,
        'date_from':         date_from,
        'date_to':           date_to,
        'selected_status':   selected_status,
        'selected_assigned': selected_assigned,
        'daily_chart_data':  json.dumps(daily_chart_data),
        'my_tickets_count':  my_tickets_count,
    })


def get_daily_chart_data():


    today = timezone.now().date()

    daily_chart_data = []

    for i in range(13, -1, -1):

        day = today - timedelta(days=i)

        daily_chart_data.append({
            "date": day.strftime('%d %b'),

            "count": Ticket.objects.filter(
                created_at__date=day
            ).count(),

            "resolved": Ticket.objects.filter(
                created_at__date=day,
                status='resolved'
            ).count(),

            "in_progress": Ticket.objects.filter(
                created_at__date=day,
                status='in_progress'
            ).count(),
        })

    return json.dumps(daily_chart_data)
# =============================================
# 🚪 ADMIN LOGOUT
# =============================================

def admin_logout(request):
    request.session.flush()
    return redirect('admin_login')


# =============================================
# 🎟️ ADMIN TICKET VIEWS
# =============================================

@admin_session_required
def admin_ticket_chat(request, ticket_id):
    ticket   = get_object_or_404(Ticket, id=ticket_id)
    tickets  = Ticket.objects.select_related('user').all()
    comments = TicketComment.objects.filter(ticket=ticket)\
                                    .select_related('sender')\
                                    .order_by('created_at')

    if request.method == "POST":
        msg = request.POST.get("message", "").strip()
        if msg:
            TicketService.add_comment(ticket, request.user, msg)
        return redirect('admin_ticket_chat', ticket_id=ticket.id)

    return render(request, 'Dashboard/chat.html', {
        'ticket':   ticket,
        'tickets':  tickets,
        'messages': comments,
    })


@admin_session_required
def admin_view_ticket(request, id):
    ticket = get_object_or_404(Ticket, id=id)

    # ✅ Access lock — agar ticket assigned hai
    # toh sirf assigned staff/admin hi dekh sakta hai
    if ticket.assigned_to is not None:
        if request.user != ticket.assigned_to and not request.user.is_superuser:
            from django.contrib import messages as django_messages
            django_messages.error(request, "⛔ Yeh ticket kisi aur ko assigned hai — aap access nahi kar sakte.")
            return redirect('admin_dashboard')

    comments = TicketComment.objects.filter(ticket=ticket)\
                                    .select_related('sender')\
                                    .order_by('created_at')

    TicketService.mark_comments_read(ticket, exclude_staff=True)

    if request.method == "POST":
        msg = request.POST.get("message", "").strip()
        if msg:
            TicketService.add_comment(ticket, request.user, msg)
        return redirect('admin_view_ticket', id=id)

    return render(request, 'Dashboard/view_ticket.html', {
        't':        ticket,
        'messages': comments,
    })

@admin_session_required
@require_POST
def update_ticket_status(request, ticket_id):
    ticket = get_object_or_404(Ticket, id=ticket_id)
    try:
        TicketService.update_status(ticket, request.POST.get("status", ""))
        messages.success(request, "Status updated successfully.")
    except ValueError as e:
        messages.error(request, str(e))
    return redirect('admin_dashboard')


@admin_session_required
@require_POST
def assign_ticket(request, ticket_id):
    if not request.user.is_superuser:
        return redirect('admin_dashboard')

    ticket = get_object_or_404(Ticket, id=ticket_id)
    staff  = get_object_or_404(User, id=request.POST.get("staff_id"))
    TicketService.assign_to_staff(ticket, staff)
    return redirect('admin_dashboard')


# =============================================
# 💬 ADMIN CHAT
# =============================================

@admin_session_required
def admin_chat_list(request):
    users = User.objects.filter(is_staff=True).exclude(id=request.user.id)
    return render(request, 'Dashboard/chat_list.html', {'users': users})


@admin_session_required
def admin_chat_detail(request, user_id):
    other_user    = get_object_or_404(User, id=user_id)
    chat_messages = AdminChat.objects.filter(
        Q(sender=request.user, receiver=other_user) |
        Q(sender=other_user,   receiver=request.user)
    ).order_by('created_at')

    AdminChat.objects.filter(
        sender=other_user, receiver=request.user, is_read=False
    ).update(is_read=True)

    return render(request, 'Dashboard/chat_detail.html', {
        'messages':   chat_messages,
        'other_user': other_user,
    })


@admin_session_required
@require_POST
def send_admin_message(request, user_id):
    msg      = request.POST.get("message", "").strip()
    receiver = get_object_or_404(User, id=user_id)
    if msg:
        AdminChat.objects.create(sender=request.user, receiver=receiver, message=msg)
    return redirect('admin_chat_detail', user_id=user_id)


# =============================================
# 👥 ADMIN STAFF MANAGEMENT
# =============================================

@admin_session_required
def admin_staff_list(request):
    staffs = StaffProfile.objects.select_related('user').order_by('-id')
    return render(request, "Dashboard/manage_staff.html", {
        "staffs":               staffs,
        "pending_staff_count":  staffs.filter(is_approved=False).count(),
        "approved_staff_count": staffs.filter(is_approved=True).count(),
    })


@admin_session_required
@require_POST
def approve_staff(request, id):
    if not request.user.is_superuser:
        return redirect("admin_login")

    profile               = get_object_or_404(StaffProfile, id=id)
    profile.is_approved   = True
    profile.user.is_staff = True
    profile.user.save(update_fields=['is_staff'])
    profile.save(update_fields=['is_approved'])
    clear_staff_cache(profile.user.id)   # ✅ clear stale cache immediately
    messages.success(request, "Staff approved successfully.")
    return redirect("admin_staff_list")


@admin_session_required
@require_POST
def reject_staff(request, id):
    if not request.user.is_superuser:
        return redirect("admin_login")

    profile = get_object_or_404(StaffProfile, id=id)
    clear_staff_cache(profile.user.id)   # ✅ clear cache before delete
    profile.delete()
    messages.success(request, "Staff rejected and removed.")
    return redirect("admin_staff_list")


# =============================================
# 🧑‍💻 STAFF REGISTER
# =============================================
def staff_register(request):
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        email    = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")

        if not username or not password or not email:
            return render(request, "Staff_dashboard/register.html", {
                "error": "All fields are required."
            })

        if User.objects.filter(username=username).exists():
            return render(request, "Staff_dashboard/register.html", {
                "error": "Username already exists"
            })

        if User.objects.filter(email=email).exists():
            return render(request, "Staff_dashboard/register.html", {
                "error": "Email already exists"
            })

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            is_staff=False,
            is_superuser=False,
        )
        StaffProfile.objects.create(user=user)
        return render(request, "Staff_dashboard/register.html", {
            "msg": "✅ Request sent to admin for approval."
        })

    return render(request, "Staff_dashboard/register.html")


# =============================================
# 🔐 STAFF LOGIN
# =============================================
@never_cache
def staff_login(request):

    if request.user.is_authenticated and request.session.get('role') == 'staff':
        return redirect('staff_dashboard')

    if request.method == "POST":

        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")

        user_obj = User.objects.filter(email=email).first()

        if user_obj:
            user = authenticate(
                request,
                username=user_obj.username,
                password=password
            )
        else:
            user = None

        if not user:
            return render(request, "Staff_dashboard/login.html", {
                "error": "Invalid email or password"
            })

        if not user.is_staff:
            return render(request, "Staff_dashboard/login.html", {
                "error": "Not a staff account"
            })

        # ✅ Staff profile check
        profile, created = StaffProfile.objects.get_or_create(user=user)

        if not profile.is_approved:
            return render(request, "Staff_dashboard/login.html", {
                "error": "Account not approved yet. Please wait for admin approval."
            })

        login(request, user)

        request.session['role'] = 'staff'

        return redirect("staff_dashboard")

    return render(request, "Staff_dashboard/login.html")

# =============================================
# 📊 STAFF DASHBOARD
# =============================================
@staff_session_required
def staff_dashboard(request):
    user      = request.user
    profile   = get_object_or_404(StaffProfile, user=user, is_approved=True)
    search    = request.GET.get('search', '')
    date_from = request.GET.get('date_from', '')
    date_to   = request.GET.get('date_to', '')

    tickets = Ticket.objects.filter(assigned_to=user)\
                             .select_related("user", "purchase")\
                             .order_by("-id")

    # ✅ Search filter
    if search:
        tickets = tickets.filter(
            Q(user__username__icontains=search) |
            Q(title__icontains=search) |
            Q(purchase__purchase_id__icontains=search)
        )

    # ✅ Date filter
    if date_from:
        tickets = tickets.filter(created_at__date__gte=date_from)
    if date_to:
        tickets = tickets.filter(created_at__date__lte=date_to)

    stats = tickets.aggregate(
        total       = Count('id'),
        pending     = Count('id', filter=Q(status='pending')),
        in_progress = Count('id', filter=Q(status='in_progress')),
        resolved    = Count('id', filter=Q(status='resolved')),
    )

    paginator = Paginator(tickets, 10)
    page_obj  = paginator.get_page(request.GET.get('page'))

    recent_messages = TicketComment.objects.filter(ticket__assigned_to=user)\
                                           .select_related("ticket", "ticket__user")\
                                           .order_by("-id")[:5]

    unread_count = TicketComment.objects.filter(
        ticket__assigned_to=user, is_read=False
    ).count()

    return render(request, "Staff_dashboard/staff_dashboard.html", {
        **stats,
        "tickets":               page_obj,
        "page_obj":              page_obj,
        "recent_messages":       recent_messages,
        "unread_messages_count": unread_count,
        "assigned_tickets":      page_obj,
        "assigned_count":        stats['total'],
        "search":                search,
        "date_from":             date_from,
        "date_to":               date_to,
    })


# =============================================
# 🚪 STAFF LOGOUT
# =============================================

def staff_logout(request):
    request.session.flush()
    return redirect('staff_login')


# =============================================
# 🎟️ STAFF TICKET VIEWS
# =============================================

@staff_session_required
def staff_ticket_chat(request, ticket_id):
    ticket   = get_object_or_404(Ticket, id=ticket_id, assigned_to=request.user)
    comments = TicketComment.objects.filter(ticket=ticket)\
                                    .select_related('sender')\
                                    .order_by('created_at')

    if request.method == "POST":
        msg = request.POST.get("message", "").strip()
        if msg:
            TicketService.add_comment(ticket, request.user, msg)
        return redirect('staff_ticket_chat', ticket_id=ticket.id)

    return render(request, "Staff_dashboard/staff_ticket_chat.html", {
        "ticket":   ticket,
        "messages": comments,
    })


@staff_session_required
def staff_view_ticket(request, id):
    ticket = get_object_or_404(Ticket, id=id)

    if ticket.assigned_to != request.user:
        return HttpResponseForbidden("You are not assigned to this ticket.")

    TicketService.mark_comments_read(ticket, exclude_staff=False)

    if request.method == "POST":
        msg = request.POST.get("message", "").strip()
        if msg:
            TicketService.add_comment(ticket, request.user, msg)
        return redirect("staff_view_ticket", id=id)

    comments = TicketComment.objects.filter(ticket=ticket)\
                                    .select_related('sender')\
                                    .order_by('created_at')
    return render(request, 'Staff_dashboard/view_ticket.html', {
        'ticket':   ticket,
        'comments': comments,
    })


@staff_session_required
@require_POST
def update_ticket(request, id):
    ticket = get_object_or_404(Ticket, id=id, assigned_to=request.user)
    try:
        TicketService.update_status(ticket, request.POST.get("status", ""))
        messages.success(request, "Status updated.")
    except ValueError as e:
        messages.error(request, str(e))
    return redirect("staff_dashboard")


# =============================================
# 🔌 API ENDPOINTS
# =============================================

@login_required_token
def get_tickets(request):
    tickets   = TicketService.get_user_tickets(request._token_user)
    paginator = Paginator(tickets, 10)
    page      = paginator.get_page(request.GET.get('page', 1))

    data = [
        {"title": t.title, "description": t.description, "status": t.status}
        for t in page
    ]
    return JsonResponse({
        "tickets":  data,
        "page":     page.number,
        "pages":    paginator.num_pages,
        "has_next": page.has_next(),
    })


@login_required_token
@require_POST
def close_ticket(request, ticket_id):
    user   = request._token_user
    ticket = get_object_or_404(Ticket, id=ticket_id, user=user)
    ticket.status = 'resolved'
    ticket.save(update_fields=['status'])
    TicketService.invalidate_user_cache(user.id)  
    messages.success(request, "Ticket closed successfully!")
    return redirect('profile')


@admin_session_required
@require_POST
def mark_notifications_read(request):
    TicketComment.objects.filter(
        is_read=False,
        sender__is_staff=False,
        sender__is_superuser=False,
    ).update(is_read=True)
    TicketService.invalidate_dashboard_cache()   
    return JsonResponse({"status": "ok"})

@admin_session_required
def edit_staff_info(request, staff_id):
    staff_profile = get_object_or_404(StaffProfile, id=staff_id)
    if request.method == 'POST':
        user = staff_profile.user

        # ✅ Username update — duplicate check
        new_username = request.POST.get('username', '').strip()
        if new_username and new_username != user.username:
            if User.objects.filter(username=new_username).exclude(id=user.id).exists():
                from django.contrib import messages as django_messages
                django_messages.error(request, f'Username "{new_username}" already taken.')
                return redirect('admin_staff_list')
            user.username = new_username

      
        user.email      = request.POST.get('email', '').strip()
        user.save()

    return redirect('admin_staff_list')


# =============================================
# ❌ ERROR PAGES
# =============================================

def error_404(request, exception):
    return render(request, 'Dashboard/error-404.html', status=404)

def error_500(request):
    return render(request, 'Dashboard/error-500.html', status=500)
