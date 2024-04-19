from django.urls import path
from fastgmail.views import index, login_gmail, logout_gmail



urlpatterns = [
    path("", index, name="index"),
    path("login/", login_gmail, name="login"),
    path("logout/", logout_gmail, name="logout"),
]
