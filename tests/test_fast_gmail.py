"""Offline tests: the Gmail service is a fake that records the calls, no network and no credentials."""

import base64
import email
import json
from unittest import mock

import pytest

from fast_gmail import AttachmentFile, GmailApi, Thread, reply_recipients
from fast_gmail.helpers import GoogleService, InvalidToken
from fast_gmail.message import Message


def b64(text: str | bytes) -> str:
    raw = text.encode() if isinstance(text, str) else text
    return base64.urlsafe_b64encode(raw).decode()


def raw_message(id="m1", thread="t1", labels=("INBOX", "UNREAD"), headers=None, parts=None):
    headers = {
        "From": '"Ion Pop" <ion@example.com>',
        "To": "office@epolite.ro, Maria <maria@example.com>",
        "Subject": "Oferta RCA",
        "Message-ID": f"<{id}@mail>",
        "Date": "Tue, 10 Nov 2026 09:15:02 +0200",
        **(headers or {}),
    }
    return {
        "id": id,
        "threadId": thread,
        "labelIds": list(labels),
        "snippet": "snippet",
        "internalDate": "1794294902000",
        "payload": {
            "mimeType": "multipart/mixed",
            "headers": [{"name": k, "value": v} for k, v in headers.items()],
            "parts": parts
            if parts is not None
            else [
                {
                    "partId": "0",
                    "mimeType": "text/html",
                    "headers": [{"name": "Content-Type", "value": "text/html; charset=utf-8"}],
                    "body": {"size": 12, "data": b64("<p>Salut</p>")},
                }
            ],
        },
    }


class Request:
    def __init__(self, log, name, kwargs, response):
        self.log, self.name, self.kwargs, self.response = log, name, kwargs, response

    def execute(self):
        self.log.append((self.name, self.kwargs))
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


class Batch:
    def __init__(self):
        self.items = []

    def add(self, request, callback=None, request_id=None):
        self.items.append((request, callback, request_id))

    def execute(self):
        # answered in reverse on purpose: the order of the results must not depend on it
        for request, callback, request_id in reversed(self.items):
            try:
                callback(request_id, request.execute(), None)
            except Exception as e:
                callback(request_id, None, e)


class Resource:
    """`service.users().threads().get(...)` -> Request named "threads.get"."""

    def __init__(self, log, responses, path=""):
        self.log, self.responses, self.path = log, responses, path

    def __getattr__(self, name):
        path = f"{self.path}.{name}" if self.path else name
        if name in ("users", "messages", "threads", "drafts", "labels", "attachments", "settings", "sendAs"):
            return lambda: Resource(self.log, self.responses, "" if name == "users" else path)

        def call(**kwargs):
            response = self.responses.get(path, {})
            if callable(response):
                response = response(**kwargs)
            return Request(self.log, path, kwargs, response)

        return call

    def new_batch_http_request(self):
        return Batch()

    def close(self):
        pass


def make_api(responses=None):
    api = GmailApi.__new__(GmailApi)
    api.SEPARATOR_SYMBOL = ", "
    api.log = []
    api.google_service = GoogleService(service=Resource(api.log, responses or {}), user_id="me")
    return api


def sent_email(api):
    name, kwargs = api.log[-1]
    assert name == "messages.send"
    return kwargs["body"], email.message_from_bytes(base64.urlsafe_b64decode(kwargs["body"]["raw"]))


# ------------------------------------------------------------------ messages


def test_message_headers_are_case_insensitive():
    message = Message(make_api().google_service, **raw_message(headers={"CC": "x@example.com", "Reply-To": "r@example.com"}))
    assert message.subject == "Oferta RCA"
    assert message.cc == "x@example.com"
    assert message.reply_to == "r@example.com"
    assert message.message_id == "<m1@mail>"
    assert message.sender == "Ion Pop"
    assert message.html == "<p>Salut</p>"
    assert message.is_unread


def test_body_is_decoded_with_its_own_charset():
    part = {
        "partId": "0",
        "mimeType": "text/plain",
        "headers": [{"name": "Content-Type", "value": 'text/plain; charset="iso-8859-2"'}],
        "body": {"size": 5, "data": b64("poliţă".encode("iso-8859-2"))},
    }
    assert Message(make_api().google_service, **raw_message(parts=[part])).plain == "poliţă"


def test_unknown_charset_does_not_crash():
    part = {
        "partId": "0",
        "mimeType": "text/plain",
        "headers": [{"name": "Content-Type", "value": "text/plain; charset=x-nope"}],
        "body": {"size": 5, "data": b64(b"abc\xff")},
    }
    assert Message(make_api().google_service, **raw_message(parts=[part])).plain.startswith("abc")


def test_date_parses_received_and_date_headers():
    received = "by 2002:a05 with SMTP id x; Tue, 10 Nov 2026 09:15:02 -0800 (PST)"
    message = Message(make_api().google_service, **raw_message(headers={"Received": received}))
    assert message.date.isoformat() == "2026-11-10T09:15:02-08:00"
    assert Message(make_api().google_service, **raw_message()).date.isoformat() == "2026-11-10T09:15:02+02:00"
    assert Message(make_api().google_service, **raw_message(headers={"Date": "garbage"})).date is None


def test_message_without_payload():
    message = Message(make_api().google_service, id="m1", threadId="t1")
    assert message.subject is None and message.html == "" and message.attachments == []
    assert not message.has_attachments and not message.is_unread


def test_attachments_nested_inline_and_downloadable():
    parts = [
        {
            "partId": "0",
            "mimeType": "multipart/related",
            "body": {"size": 0},
            "parts": [
                {"partId": "0.0", "mimeType": "text/html", "body": {"size": 4, "data": b64("<p>x</p>")}},
                {
                    "partId": "0.1",
                    "mimeType": "image/png",
                    "filename": "logo.png",
                    "headers": [
                        {"name": "Content-ID", "value": "<logo@cid>"},
                        {"name": "Content-Disposition", "value": 'inline; filename="logo.png"'},
                    ],
                    "body": {"size": 3, "data": b64(b"PNG")},
                },
            ],
        },
        {"partId": "1", "mimeType": "application/pdf", "filename": "a/b.pdf", "body": {"size": 9, "attachmentId": "ATT"}},
        {"partId": "2", "mimeType": "text/plain", "filename": "note.txt", "body": {"size": 2, "data": b64("hi")}},
    ]
    api = make_api({"messages.attachments.get": {"size": 9, "data": b64(b"%PDF-data")}})
    message = Message(api.google_service, **raw_message(parts=parts))

    logo, pdf, note = message.attachments
    assert (logo.filename, logo.is_inline, logo.content_id, logo.data) == ("logo.png", True, "logo@cid", b"PNG")
    assert (pdf.filename, pdf.id, pdf.size, pdf.is_inline) == ("a_b.pdf", "ATT", 9, False)
    assert note.data == b"hi"
    assert message.html == "<p>x</p>" and message.plain == ""  # the .txt attachment is not body text

    pdf.download()
    assert pdf.data == b"%PDF-data"
    assert api.log[-1] == ("messages.attachments.get", {"userId": "me", "messageId": "m1", "id": "ATT"})


# ------------------------------------------------------------------- threads


def thread_payload(id, *messages):
    return {"id": id, "historyId": "9", "messages": list(messages)}


def test_get_thread():
    api = make_api({"threads.get": thread_payload("t1", raw_message("m1"), raw_message("m2", labels=("SENT",)))})
    thread = api.get_thread("t1")
    assert api.log == [("threads.get", {"userId": "me", "id": "t1", "format": "full"})]
    assert isinstance(thread, Thread) and len(thread) == 2
    assert thread.subject == "Oferta RCA" and thread.is_unread
    assert thread.last_message.id == "m2"
    assert thread.participants == ['"Ion Pop" <ion@example.com>']


def test_get_threads_keeps_list_order_and_skips_failures():
    def get(**kwargs):
        if kwargs["id"] == "t2":
            return RuntimeError("gone")
        return thread_payload(kwargs["id"], raw_message(f"m-{kwargs['id']}", thread=kwargs["id"]))

    api = make_api(
        {
            "threads.list": {
                "threads": [{"id": "t1", "snippet": "one"}, {"id": "t2", "snippet": "two"}, {"id": "t3", "snippet": "three"}],
                "nextPageToken": "N1",
                "resultSizeEstimate": 3,
            },
            "threads.get": get,
        }
    )
    response = api.get_inbox_threads(query="is:unread")
    assert [t.id for t in response] == ["t1", "t3"]
    assert [t.snippet for t in response] == ["one", "three"]
    assert response.next_page_token == "N1" and response.existing_pages is None

    list_call = api.log[0]
    assert list_call[0] == "threads.list"
    assert list_call[1]["labelIds"] == ["INBOX"] and list_call[1]["q"] == "is:unread"
    get_call = next(kwargs for name, kwargs in api.log if name == "threads.get")
    assert get_call["format"] == "metadata" and "Subject" in get_call["metadataHeaders"]


def test_pagination_forward_and_back():
    api = make_api({"threads.list": {"threads": [], "nextPageToken": "N2"}})
    page2 = api.get_threads(next_page_token="N1")
    assert (page2.previous_page_token, page2.existing_pages, page2.next_page_token) == ("N1", "N1", "N2")
    page3 = api.get_threads(next_page_token="N2", existing_pages=page2.existing_pages)
    assert page3.existing_pages == "N1, N2"
    back = api.get_threads(previous_page_token="N2", existing_pages=page3.existing_pages)
    assert api.log[-1][1]["pageToken"] == "N1" and back.existing_pages == "N1"
    with pytest.raises(InvalidToken):
        api.get_threads(previous_page_token="nope", existing_pages="N1")


def test_thread_mark_read_and_unread():
    api = make_api({"threads.get": thread_payload("t1", raw_message("m1"), raw_message("m2"))})
    thread = api.get_thread("t1").mark_as_read()
    assert api.log[-1] == ("threads.modify", {"userId": "me", "id": "t1", "body": {"addLabelIds": [], "removeLabelIds": ["UNREAD"]}})
    assert not thread.is_unread
    assert thread.mark_as_unread().is_unread


def test_unread_count():
    api = make_api({"labels.get": {"id": "INBOX", "name": "INBOX", "threadsUnread": 4, "messagesUnread": 7}})
    assert api.unread_count() == 4
    assert api.unread_count(threads=False) == 7
    assert api.log[0] == ("labels.get", {"userId": "me", "id": "INBOX"})


def test_list_errors_are_raised_not_hidden():
    api = make_api({"messages.list": RuntimeError("401")})
    with pytest.raises(RuntimeError):
        api.get_inbox_messages()


def test_get_messages_and_drafts():
    api = make_api(
        {
            "messages.list": {"messages": [{"id": "m1", "threadId": "t1"}, {"id": "m2", "threadId": "t1"}], "resultSizeEstimate": 2},
            "messages.get": lambda **kw: raw_message(kw["id"]),
            "drafts.list": {"drafts": [{"id": "d1", "message": {"id": "m9", "threadId": "t9"}}], "resultSizeEstimate": 1},
            "drafts.get": {"id": "d1", "message": raw_message("m9")},
        }
    )
    assert [m.id for m in api.get_messages()] == ["m1", "m2"]
    assert [m.id for m in api.get_draft_messages()] == ["m9"]
    assert api.get_draft("d1").subject == "Oferta RCA"


# ------------------------------------------------------------------- sending


def test_send_message_plain_call_is_unchanged():
    api = make_api({"messages.send": {"id": "s1", "threadId": "t5"}})
    result = api.send_message(sender="office@epolite.ro", to="a@example.com", subject="Salut", html="<b>x</b>", signature=False)
    body, msg = sent_email(api)
    assert result == {"id": "s1", "threadId": "t5"}
    assert "threadId" not in body
    assert msg["To"] == "a@example.com" and msg["Subject"] == "Salut"
    assert msg["Cc"] is None and msg["Bcc"] is None and msg["In-Reply-To"] is None


def test_send_message_addresses_as_string_or_list():
    api = make_api()
    api.send_message(sender="o@e.ro", to=["a@example.com", "b@example.com"], subject="s", text="t", cc="c@example.com", bcc=["d@example.com"])
    _, msg = sent_email(api)
    assert msg["To"] == "a@example.com, b@example.com"
    assert msg["Cc"] == "c@example.com" and msg["Bcc"] == "d@example.com"


def test_send_message_attachments_from_memory_and_disk(tmp_path):
    path = tmp_path / "talon.weird-ext"
    path.write_bytes(b"\x00\x01")
    api = make_api()
    api.send_message(
        sender="o@e.ro",
        to="a@example.com",
        subject="s",
        text="t",
        attachments=[AttachmentFile("oferta.pdf", b"%PDF"), str(path)],
    )
    _, msg = sent_email(api)
    files = {p.get_filename(): (p.get_content_type(), p.get_payload(decode=True)) for p in msg.walk() if p.get_filename()}
    assert files == {
        "oferta.pdf": ("application/pdf", b"%PDF"),
        "talon.weird-ext": ("application/octet-stream", b"\x00\x01"),
    }
    api.send_message(sender="o@e.ro", to="a@example.com", subject="s", text="t", attachments=str(path))
    assert sum(1 for p in sent_email(api)[1].walk() if p.get_filename()) == 1


def test_reply_stays_in_the_thread():
    api = make_api({"messages.send": {"id": "s1", "threadId": "t1"}})
    original = Message(
        api.google_service,
        **raw_message(headers={"Subject": "Re: Oferta RCA", "References": "<a@mail> <b@mail>", "Cc": "sef@example.com, office@epolite.ro"}),
    )
    api.reply_to_message(original, sender="office@epolite.ro", html="<p>ok</p>", signature=False, sender_name="Ana - ePolite")
    body, msg = sent_email(api)
    assert body["threadId"] == "t1"
    assert msg["Subject"] == "Re: Oferta RCA"  # no "Re: Re:"
    assert msg["In-Reply-To"] == "<m1@mail>"
    assert msg["References"] == "<a@mail> <b@mail> <m1@mail>"
    assert msg["To"] == "Ion Pop <ion@example.com>"
    assert msg["Cc"] is None  # not reply_all
    assert msg["From"] == "Ana - ePolite <office@epolite.ro>"


def test_reply_all_copies_everybody_but_us():
    api = make_api()
    original = Message(api.google_service, **raw_message(headers={"Cc": "sef@example.com, OFFICE@epolite.ro"}))
    api.reply_to_message(original, sender="office@epolite.ro", text="ok", reply_all=True, cc=["extra@example.com", "sef@example.com"])
    _, msg = sent_email(api)
    assert msg["To"] == "Ion Pop <ion@example.com>"
    assert msg["Cc"] == "Maria <maria@example.com>, sef@example.com, extra@example.com"
    assert msg["Subject"] == "Re: Oferta RCA"


def test_reply_recipients_reply_to_and_own_message():
    service = make_api().google_service
    with_reply_to = Message(service, **raw_message(headers={"Reply-To": "raspuns@example.com"}))
    assert reply_recipients(with_reply_to, "office@epolite.ro") == (["raspuns@example.com"], [])
    ours = Message(service, **raw_message(headers={"From": "office@epolite.ro", "To": "ion@example.com", "Cc": "sef@example.com"}))
    assert reply_recipients(ours, "office@epolite.ro", reply_all=True) == (["ion@example.com"], ["sef@example.com"])


# ------------------------------------------------------------------- 1.6.0


def test_send_message_accepts_the_answered_message():
    api = make_api({"messages.send": {"id": "s1"}})
    original = Message(api.google_service, **raw_message(headers={"References": "<a@mail>"}))
    api.send_message(sender="o@e.ro", to="ion@example.com", subject="Oferta RCA", text="ok", in_reply_to=original)
    body, msg = sent_email(api)
    assert body["threadId"] == "t1"
    assert msg["In-Reply-To"] == "<m1@mail>" and msg["References"] == "<a@mail> <m1@mail>"
    assert msg["Subject"] == "Re: Oferta RCA"


def test_address_lists():
    message = Message(
        make_api().google_service,
        **raw_message(headers={"To": "Ana <ana@example.com>, ana@example.com, b@example.com", "CC": '"Pop, Ion" <ion@example.com>'}),
    )
    assert message.recipient_addresses == ["ana@example.com", "b@example.com"]
    assert message.cc_addresses == ["ion@example.com"]
    assert Message(make_api().google_service, id="m1").cc_addresses == []


def test_html_with_images_embeds_cid_images():
    parts = [
        {"partId": "0", "mimeType": "text/html", "body": {"size": 9, "data": b64('<img src="cid:logo@cid"><img src="cid:big@cid"><img src="cid:nope">')}},
        {
            "partId": "1",
            "mimeType": "image/png",
            "filename": "logo.png",
            "headers": [{"name": "Content-ID", "value": "<logo@cid>"}],
            "body": {"size": 3, "data": b64(b"PNG")},
        },
        {
            "partId": "2",
            "mimeType": "image/jpeg",
            "filename": "big.jpg",
            "headers": [{"name": "Content-Id", "value": "<big@cid>"}],
            "body": {"size": 3, "attachmentId": "ATT"},
        },
    ]
    api = make_api({"messages.attachments.get": {"size": 3, "data": b64(b"JPG")}})
    message = Message(api.google_service, **raw_message(parts=parts))
    assert set(message.inline_images) == {"logo@cid", "big@cid"}
    assert message.payload.has_attachments()
    html = message.html_with_images()
    assert 'src="data:image/png;base64,UE5H"' in html and 'src="data:image/jpeg;base64,SlBH"' in html
    assert 'src="cid:nope"' in html
    # downloaded with the Gmail message id (not the Message-ID header)
    assert api.log[-1] == ("messages.attachments.get", {"userId": "me", "messageId": "m1", "id": "ATT"})


def test_short_date_string():
    import datetime

    now = datetime.datetime.now().astimezone()
    old = now.replace(year=now.year - 2, day=1)

    def at(moment):
        return Message(make_api().google_service, **raw_message(headers={"Date": moment.strftime("%a, %d %b %Y %H:%M:%S %z")}))

    assert at(now).short_date_string() == now.strftime("%H:%M")
    assert at(old).short_date_string() == old.strftime("%B %d, %Y")
    assert Message(make_api().google_service, id="m1").short_date_string() is None


def test_gmail_client_is_built_without_the_file_cache(credentials_file):
    token = json.dumps({"token": "t", "refresh_token": "r", "client_id": "id", "client_secret": "s", "token_uri": "https://oauth2.googleapis.com/token"})
    with mock.patch("fast_gmail.gmail.build") as build:
        GmailApi(credentials_file_path=credentials_file, auth_token=token)
    assert build.call_args.kwargs["cache_discovery"] is False


# ---------------------------------------------------------------------- auth

CLIENT = {
    "web": {
        "client_id": "id.apps.googleusercontent.com",
        "client_secret": "secret",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "redirect_uris": ["http://localhost:3000/callback", "http://localhost:8003/callback"],
    }
}


@pytest.fixture
def credentials_file(tmp_path):
    path = tmp_path / "credentials.json"
    path.write_text(json.dumps(CLIENT))
    return str(path)


def test_web_flow_without_pkce(credentials_file):
    api = GmailApi(credentials_file_path=credentials_file, port=8003)
    assert api.google_service is None and api.code_verifier is None
    assert "code_challenge" not in api.auth_url
    assert "prompt=consent" in api.auth_url and "access_type=offline" in api.auth_url
    assert "redirect_uri=http%3A%2F%2Flocalhost%3A8003%2Fcallback" in api.auth_url


def test_web_flow_with_pkce(credentials_file):
    api = GmailApi(credentials_file_path=credentials_file, pkce=True, scopes=["https://www.googleapis.com/auth/gmail.readonly"])
    assert "code_challenge=" in api.auth_url and "code_challenge_method=S256" in api.auth_url
    assert "gmail.readonly" in api.auth_url and "gmail.modify" not in api.auth_url
    assert api.code_verifier and len(api.code_verifier) >= 43

    with pytest.raises(ValueError):
        GmailApi(credentials_file_path=credentials_file, pkce=True, code="abc")

    with mock.patch("google_auth_oauthlib.flow.Flow.fetch_token") as fetch, mock.patch(
        "google_auth_oauthlib.flow.Flow.credentials", new_callable=mock.PropertyMock
    ) as credentials, mock.patch("fast_gmail.gmail.build"):
        credentials.return_value.to_json.return_value = '{"token": "x"}'
        step2 = GmailApi(credentials_file_path=credentials_file, pkce=True, code="abc", code_verifier=api.code_verifier)
    fetch.assert_called_once_with(code="abc")
    assert step2.flow.code_verifier == api.code_verifier  # the verifier of step 1 is the one sent to Google
    assert step2.auth_token == {"token": "x"}


def test_redirect_uri_can_be_chosen(credentials_file):
    api = GmailApi(credentials_file_path=credentials_file, redirect_uri="http://localhost:8003/callback")
    assert api.redirect_uri == "http://localhost:8003/callback"
    assert "redirect_uri=http%3A%2F%2Flocalhost%3A8003%2Fcallback" in api.auth_url
    # default: unchanged (the one using `port`, else the first)
    assert GmailApi(credentials_file_path=credentials_file).redirect_uri == "http://localhost:3000/callback"
    with pytest.raises(ValueError):
        GmailApi(credentials_file_path=credentials_file, redirect_uri="https://evil.example/callback")


def test_expired_token_with_refresh_token_does_not_ask_to_log_in(credentials_file):
    token = json.dumps(
        {
            "token": "old",
            "refresh_token": "r",
            "client_id": "id",
            "client_secret": "secret",
            "token_uri": "https://oauth2.googleapis.com/token",
            "expiry": "2020-01-01T00:00:00Z",
        }
    )
    with mock.patch("fast_gmail.gmail.build") as build:
        api = GmailApi(credentials_file_path="missing.json", auth_token=token)
    assert api.auth_url == "" and api.google_service is not None
    assert build.call_args.kwargs["credentials"].refresh_token == "r"
    assert json.loads(api.get_auth_token())["refresh_token"] == "r"


def test_invalid_token():
    with pytest.raises(InvalidToken):
        GmailApi(auth_token="not json")


def test_create_label():
    api = make_api({"labels.create": {"id": "Label_5", "name": "ToDo", "type": "user"}})
    label = api.create_label("ToDo")
    assert (label.id, label.name) == ("Label_5", "ToDo")
    assert api.log[0] == (
        "labels.create",
        {"userId": "me", "body": {"name": "ToDo", "labelListVisibility": "labelShow", "messageListVisibility": "show"}},
    )
