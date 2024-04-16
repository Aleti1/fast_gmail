from django.urls import path
from fastgmail.views import index, emails, login



urlpatterns = [
    path("", index, name="index"),
    path("emails/", emails, name="emails"),
    path("login/", login, name="login"),
]
