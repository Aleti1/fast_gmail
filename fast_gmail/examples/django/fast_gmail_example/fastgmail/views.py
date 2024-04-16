from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpResponseBadRequest
import sys         

# appending the directory of gmail.py
sys.path.insert(1, '/home/aleti/Desktop/work/python/development/fast-gmail/')  

from fast_gmail import GmailApi
from fast_gmail.helpers import *

# Create your views here.
def index(request):
    # if request.user.token:
    #     return redirect("emails")
    gmail = GmailApi(
        credentials_file_path="./credentials.json",
        port=request.get_port(),
        application_type=ApplicationType.WEB
    )
    print(gmail.__dict__)
    
    return render(
        request,
        "fastgmail/index.html",
        {
            "auth_url": gmail.auth_url
        }
    )

def emails(request):
    if not request.user.token:
        return HttpResponseBadRequest("Need to login with gmail first")
    return render(
        request,
        "fastgmail/emails.html",
        {
            "messages": GmailApi(request.user.token).get_messages()
        }
    )

def login(request):
    print(request.GET)
    gmail = GmailApi(
        credentials_file_path="./credentials.json",
        port=request.get_port(),
        code=request.GET.get("code", None)
    )
    print(gmail.__dict__)
    request.user.token = gmail.credentials
    request.user.gmail = gmail.profile.emailAddress
    request.user.save()
    return HttpResponse("Dai dai dai")