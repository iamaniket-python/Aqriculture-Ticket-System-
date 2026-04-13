from django.contrib import admin
from django.urls import path
from user.views import RegisterView, LoginView, create_ticket, profile, register, login_page, dashboard
from django.conf import settings
from django.conf.urls.static import static
from user.views import logout_view

from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from user.views import RegisterView, LoginView
urlpatterns = [
    path('admin/', admin.site.urls),

    path('', login_page, name='home'),

    # ✅ API routes
    path('api/auth/register/', RegisterView.as_view(), name="auth_register"),
    path('api/auth/login/', LoginView.as_view(), name="auth_login"),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),



    # ✅ Template routes
    path('register/', register, name='register'),
    path('login/', login_page, name='login'),
    path('dashboard/', dashboard, name='dashboard'),
    path('logout/', logout_view, name='logout'),
    path('profile/', profile, name='profile'),
    path('create-ticket/', create_ticket, name='create_ticket'),
]
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
