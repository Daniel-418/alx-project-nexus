from django.urls import path

from accounts.views import Login, Register, UserProfile


urlpatterns = [
    path("register/", Register.as_view(), name="register"),
    path("login/", Login.as_view(), name="login"),
    path("profile/", UserProfile.as_view(), name="profile"),
]
