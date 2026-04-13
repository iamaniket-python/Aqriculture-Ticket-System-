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
    path('', views.login_page, name='home'),
    path('login/', views.login_page, name='login'),
    
    path('api/auth/register/', views.RegisterView.as_view(), name="auth_register"),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),


   
    path('register/', views.register, name='register'),
    path('profile/', views.profile, name='profile'),
    path('create-ticket/', views.create_ticket, name='create_ticket'),
    path('verify-otp/', views.verify_otp, name='verify_otp'),
    path('resend-otp/', views.resend_otp, name='resend_otp'),
    path('logout/', views.logout_view, name='logout'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)