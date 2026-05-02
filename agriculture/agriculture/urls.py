from django.contrib import admin
from django.urls import path
from user import views
from django.conf import settings
from django.conf.urls.static import static
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

# ✅ Custom error pages (create these templates later)
handler404 = 'user.views.error_404'
handler500 = 'user.views.error_500'

urlpatterns = [

    # =========================
    # 🔧 DJANGO ADMIN PANEL
    # =========================
    path('django-admin/', admin.site.urls),   # ✅ Renamed from 'admin/' — harder to find by bots

    # =========================
    # 👤 USER AUTH
    # =========================
    path('', views.landing_page, name='home'),
    path('login/', views.login_page, name='login'),
    path('register/', views.register, name='register'),
    path('verify-otp/', views.verify_otp_view, name='verify_otp'),
    path('resend-otp/', views.resend_otp, name='resend_otp'),
    path('logout/', views.logout_view, name='user_logout'),

    # =========================
    # 👤 USER PANEL
    # =========================
    path('profile/', views.profile, name='profile'),
    path('create-ticket/', views.create_ticket, name='create_ticket'),
    path('check-tracking/', views.check_tracking, name='check_tracking'),

    # =========================
    # 💬 USER CHAT
    # =========================
    path('user/ticket/chat/<int:ticket_id>/', views.ticket_chat, name='user_ticket_chat'),

    # =========================
    # ⚙️ API
    # =========================
    path('api/auth/register/', views.RegisterView.as_view(), name='auth_register'),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/tickets/', views.get_tickets, name='api_tickets'),

    # =========================
    # 🔴 ADMIN AUTH
    # =========================
    path('admin-login/', views.admin_login, name='admin_login'),
    path('admin-logout/', views.admin_logout, name='admin_logout'),

    # =========================
    # 🔴 ADMIN DASHBOARD
    # =========================
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),

    # =========================
    # 🔴 ADMIN TICKET
    # =========================
    path('dashboard/ticket/view/<int:id>/', views.admin_view_ticket, name='admin_view_ticket'),
    path('dashboard/ticket/chat/<int:ticket_id>/', views.admin_ticket_chat, name='admin_ticket_chat'),
    path('dashboard/ticket/update/<int:ticket_id>/', views.update_ticket_status, name='admin_update_ticket'),
    path('dashboard/ticket/assign/<int:ticket_id>/', views.assign_ticket, name='assign_ticket'),

    # =========================
    # 🔴 ADMIN CHAT SYSTEM
    # =========================
    path('dashboard/chat/', views.admin_chat_list, name='admin_chat'),                          # ✅ moved from admin/chat/
    path('dashboard/chat/send/<int:user_id>/', views.send_admin_message, name='send_admin_message'),  # ✅ moved

    # =========================
    # 🔴 ADMIN NOTIFICATIONS
    # =========================
    path('dashboard/notifications/read/', views.mark_notifications_read, name='mark_notifications_read'),  # ✅ moved

    # =========================
    # 🔴 ADMIN STAFF MANAGEMENT
    # =========================
    path('dashboard/staff/', views.admin_staff_list, name='admin_staff_list'),
    path('dashboard/staff/approve/<int:id>/', views.approve_staff, name='approve_staff'),
    path('dashboard/staff/reject/<int:id>/', views.reject_staff, name='reject_staff'),

    # =========================
    # 🔵 STAFF AUTH
    # =========================
    path('staff/register/', views.staff_register, name='staff_register'),
    path('staff/login/', views.staff_login, name='staff_login'),
    path('staff/logout/', views.staff_logout, name='staff_logout'),

    # =========================
    # 🔵 STAFF DASHBOARD
    # =========================
    path('staff/dashboard/', views.staff_dashboard, name='staff_dashboard'),

    # =========================
    # 🔵 STAFF TICKET
    # =========================
    path('staff/ticket/<int:id>/', views.staff_view_ticket, name='staff_view_ticket'),
    path('staff/ticket/update/<int:id>/', views.update_ticket, name='staff_update_ticket'),
    path('staff/ticket/chat/<int:ticket_id>/', views.staff_ticket_chat, name='staff_ticket_chat'),
    path('ticket/close/<int:ticket_id>/', views.close_ticket, name='close_ticket'),
]


# =========================
# 📁 STATIC & MEDIA FILES
# =========================
if settings.DEBUG:
    # Local development only
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.BASE_DIR / 'user' / 'static')
else:
    # ✅ Production: serve media files via Django
    # (For large projects, use AWS S3 instead — ask me about it)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)