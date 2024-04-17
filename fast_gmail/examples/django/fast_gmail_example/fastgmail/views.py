from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpResponseBadRequest
from django.contrib.auth import authenticate, login
from fastgmail.models import ExampleUser
from django.contrib.auth import logout
import sys
import os    

# appending the directory of gmail.py for import
sys.path.insert(1, '/home/aleti/Desktop/work/python/development/fast-gmail/')  

from fast_gmail import GmailApi
from fast_gmail.helpers import *

# Create your views here.
def index(request):
    gmail = GmailApi(
        port=request.get_port() # set the djano running app port
    )
    context = {}
    if request.user.is_authenticated:
        context["data"] = gmail.get_inbox_messages()
    else:
        context["auth_url"] = gmail.auth_url
    return render(
        request,
        "fastgmail/index.html",
        context
    )

def login_gmail(request):
    gmail = GmailApi(
        credentials_file_path="./credentials.json",
        code=request.GET.get("code", None),
        port=request.get_port()
    )
    # create new user
    user = ExampleUser.objects.create(
        username="username", 
        email="email@address.test"
    )
    # append data to created user
    user.token = gmail.credentials
    user.gmail = gmail.profile.emailAddress
    user.set_password("123456")
    # save user to db
    user.save()
    # login the new user
    login(request, user, backend='django.contrib.auth.backends.ModelBackend')
    return HttpResponse("<div>Authentication success</div><script>function c(){window.close()};c();</script>")

def logout_gmail(request):
    # remove user data
    request.user.token = None
    request.user.gmail = None
    request.user.save()
    # get user from db and remove it
    user = ExampleUser.objects.get(email="email@address.test")
    user.delete()
    # remove existing token file
    if os.path.exists("token.json"):
        os.remove("token.json")
    logout(request)
    return redirect("index")