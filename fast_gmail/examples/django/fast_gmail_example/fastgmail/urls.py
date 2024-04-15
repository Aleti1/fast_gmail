from django.urls import path
from fastgmail.views import index, emails



urlpatterns = [
    path("", index, name="index"),
    path("emails/", emails, name="emails"),
]
