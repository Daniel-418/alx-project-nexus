from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from accounts.views import Login, Register, UserProfile


urlpatterns = [
    path("register/", Register.as_view(), name="register"),
    path("login/", Login.as_view(), name="login"),
    path("profile/", UserProfile.as_view(), name="profile"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
]
