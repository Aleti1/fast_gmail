from fastapi import FastAPI, Request
from starlette.responses import RedirectResponse

from fast_gmail import GmailApi
import os
app = FastAPI()


@app.get("/")
async def index(
    request: Request
):
    gmail = GmailApi(
        credentials_file_path="/home/aleti/Desktop/work/python/development/fast-gmail/fast_gmail/credentials.json",
        port = request.url.port
    )
    if gmail.credentials and gmail.credentials.valid:
        return gmail.get_inbox_messages()
    
    return RedirectResponse(url=gmail.auth_url)

@app.get("/login")
async def login(request: Request):
    params = request.query_params
    if "code" not in params:
        return RedirectResponse(url=request.base_url)
    
    gmail = GmailApi(
        credentials_file_path="/home/aleti/Desktop/work/python/development/fast-gmail/fast_gmail/credentials.json",
        port = request.url.port,
        code = params["code"]
    )

    return gmail.get_inbox_messages()


@app.get("/inbox")
async def inbox():
    return GmailApi().get_inbox_messages()

@app.get("/logout")
async def logout(request: Request):
    # remove existing token file
    if os.path.exists("token.json"):
        os.remove("token.json")
    return RedirectResponse(url=request.base_url)