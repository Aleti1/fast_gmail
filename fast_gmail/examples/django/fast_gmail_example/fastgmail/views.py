from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpResponseBadRequest
import sys         
import importlib.util        
 
# # passing the file name and path as argument
# spec = importlib.util.spec_from_file_location(
#   "message", "/home/aleti/Desktop/work/python/development/fast_gmail/fast_gmail/message.py")    
 
# # importing the module as foo 
# Message = importlib.util.module_from_spec(spec)        
# spec.loader.exec_module(Message)


# # appending the directory of gmail.py 
# # in the sys.path list
sys.path.insert(1, '/home/aleti/Desktop/work/python/development/fast_gmail/')  
# print([x for x in sys.path])
# from gmail import GmailApi

from fast_gmail import GmailApi
from fast_gmail.helpers import *

# Create your views here.
def index(request):
    # if request.user.token:
    #     return redirect("emails")
    gmail = GmailApi(credentials_file_path="./credentials.json", application_type=ApplicationType.WEB)
    print(gmail)
    
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
            "messages": Gmail(request.user.token).get_messages()
        }
    )

