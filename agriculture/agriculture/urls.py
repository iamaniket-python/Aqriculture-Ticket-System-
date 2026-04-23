from django.contrib import admin
from django.urls import path
from user import views
from django.conf import settings
from django.conf.urls.static import static
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

urlpatterns = [
    path('admin/', admin.site.urls),

    # User
    path('', views.landing_page, name='home'),
    path('login/', views.login_page, name='login'),
    path('register/', views.register, name='register'),
    path('profile/', views.profile, name='profile'),
    path('verify-otp/', views.verify_otp, name='verify_otp'),
    path('resend-otp/', views.resend_otp, name='resend_otp'),
    path('logout/', views.logout_view, name='logout'),

    # API
    path('api/auth/register/', views.RegisterView.as_view(), name="auth_register"),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # Ticket
    path("check-tracking/", views.check_tracking, name="check_tracking"),
    path("create-ticket/", views.create_ticket, name="create_ticket"),
    path("api/tickets/", views.get_tickets, name="api_tickets"),

    # Chat
    path("ticket/chat/<int:ticket_id>/", views.ticket_chat, name="ticket_chat"),
    path("admin/ticket/chat/<int:ticket_id>/", views.admin_ticket_chat, name="admin_ticket_chat"),
    
    #Dashboard
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('assign-ticket/<int:ticket_id>/', views.assign_ticket, name='assign_ticket'),
    path('admin-login/', views.admin_login_view, name='admin_login'),
    path('admin-logout/', views.admin_logout, name='logout'),
    path('assign-ticket/<int:ticket_id>/', views.assign_ticket, name='assign_ticket'),
    path('update-ticket/<int:ticket_id>/', views.update_ticket_status, name='update_ticket'),

    #chatsystem
    path('admin-chat/', views.admin_chat_list, name='admin_chat'),
   
    path('dashboard/chat/<int:ticket_id>/', views.admin_ticket_chat, name='admin_ticket_chat'),
    path('send-message/<int:user_id>/', views.send_admin_message, name='send_admin_message'),
    path('dashboard/gallery/image/<int:ticket_id>/', views.view_image, name='view_image'),
   
   
]

# Media files
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)