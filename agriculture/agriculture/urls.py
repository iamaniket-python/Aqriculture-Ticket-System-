from django.contrib import admin
from django.urls import path
from user import views
from django.conf import settings
from django.conf.urls.static import static
from user import admin_views
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.landing_page, name='home'),
    path('login/', views.login_page, name='login'),
    

    # APi
    path('api/auth/register/', views.RegisterView.as_view(), name="auth_register"),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),


  # Website
    path('register/', views.register, name='register'),
    path('profile/', views.profile, name='profile'),
    path('verify-otp/', views.verify_otp, name='verify_otp'),
    path('resend-otp/', views.resend_otp, name='resend_otp'),
    path('logout/', views.logout_view, name='logout'),

    # Ticket Traking
    path("check-tracking/", views.check_tracking, name="check_tracking"),
    path("create-ticket/", views.create_ticket, name="create_ticket"),
    path("api/tickets/", views.get_tickets, name="api_tickets"),
    # path('add-comment/<int:ticket_id>/', views.add_comment, name='add_comment'),

    #admin
    path('admin-login/', admin_views.admin_login, name='admin_login'),
    path('admin-dashboard/', admin_views.admin_dashboard, name='admin_dashboard'),
    path('update-ticket/<int:id>/', admin_views.update_ticket, name='update_ticket'),
    path('create-staff/', admin_views.create_staff, name='create_staff'),
    path('register/', admin_views.register, name='register'),
    path('logout/', admin_views.logout_view, name='logout'),
   
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)