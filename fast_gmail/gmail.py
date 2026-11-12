import mimetypes
import typing
import base64
import json
import os

from email.message import EmailMessage
from email.header import Header
from email import utils

from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from googleapiclient.errors import HttpError  # noqa: F401  (re-exported by `from fast_gmail import *`)
from google_auth_oauthlib.flow import InstalledAppFlow
from google_auth_oauthlib.flow import Flow

from fast_gmail.message import MessagePartBody
from fast_gmail.message import Message
from fast_gmail.search import SearchParams
from fast_gmail.thread import Thread
from fast_gmail.draft import Draft  # noqa: F401  (re-exported by `from fast_gmail import *`)
from fast_gmail.helpers import (
    GoogleService,
    GmailProfile,
    MAX_RESULTS,
    ApplicationType,
    AttachmentFile,
    InvalidToken,
    GetMessagesResponse,
    GetThreadsResponse,
    Labels,
    GmailLabel,
    MessagesList,
    DraftsList,
    ThreadsList,
)


# Default scopes. Pass `scopes=[...]` to GmailApi to ask for less (or more).
# A stored token only works with the scopes it was granted: after changing them, log in again.
SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.settings.basic",
    "https://www.googleapis.com/auth/contacts.readonly",
    "https://www.googleapis.com/auth/contacts.other.readonly",
]

# headers fetched by get_threads(format="metadata") when no list is given
THREAD_LIST_HEADERS = ["From", "To", "Cc", "Subject", "Date", "Message-ID"]

Attachments = list[str | AttachmentFile] | str | AttachmentFile | None
Addresses = list[str] | str | None


class GmailApi(object):
    """https://googleapis.github.io/google-api-python-client/docs/dyn/gmail_v1.users.html"""

    auth_token: dict | None = None
    credentials: Credentials | None = None
    google_service: GoogleService | None = None
    max_results: int = MAX_RESULTS
    SEPARATOR_SYMBOL: str
    profile_data: GmailProfile | None = None
    redirect_uri: str | None = None
    auth_url: str | None = None  # this will be used to start the oAuth flow
    code_verifier: str | None = None  # PKCE: keep it with auth_url, send it back with the code
    flow: Flow | None = None

    def __init__(
        self,
        credentials_file_path: str = "credentials.json",
        port: int = 3000,  # set the local server port for Authorized redirect URI
        separator_symbol: str = ", ",
        user_id: str = "me",
        application_type: ApplicationType = ApplicationType.WEB,
        auth_token: str | None = None,
        code: str | None = None,
        scopes: list[str] | None = None,
        pkce: bool = False,
        code_verifier: str | None = None,
        redirect_uri: str | None = None,
    ) -> None:
        """https://github.com/googleapis/google-api-python-client/blob/main/docs/oauth-installed.md

        Args:
            credentials_file_path (str): OAuth client secrets file downloaded from Google Cloud.
            port (int): Port of the Authorized redirect URI (web) / of the local login server (installed).
            separator_symbol (str): Separator used to join the page tokens kept for pagination.
            user_id (str): Mailbox to work on, "me" = the authorized user.
            application_type (ApplicationType): WEB (two steps: auth_url, then code) or INSTALLED (local browser).
            auth_token (str | None): Token JSON from a previous get_auth_token(); skips the login.
            code (str | None): WEB flow, step 2: the `code` Google sent to the redirect URI.
            scopes (list[str] | None): OAuth scopes to ask for. Defaults to SCOPES.
            pkce (bool): WEB flow: protect the code exchange with PKCE (RFC 7636). Step 1 then sets
                `code_verifier` next to `auth_url`; store it and pass it back in step 2. Defaults to False.
            code_verifier (str | None): WEB flow with PKCE, step 2: the verifier created in step 1.
            redirect_uri (str | None): WEB flow: which Authorized redirect URI of the credentials file to use,
                when the file lists several (one client shared by dev / staging / production). It must be one
                of the file's `redirect_uris`, and the same in step 1 and step 2. Defaults to the one using `port`,
                else the first of the file.
        """  # noqa
        # set separator for spliting/joining the array of existing previous_page_tokens for pagination
        self.SEPARATOR_SYMBOL = separator_symbol
        self.scopes: list[str] = list(scopes) if scopes else SCOPES
        self.auth_url = ""
        self.code_verifier = code_verifier

        if auth_token:
            try:
                self.credentials = Credentials.from_authorized_user_info(
                    json.loads(auth_token), self.scopes
                )
            except Exception:
                raise InvalidToken("INVALID AUTH TOKEN PROVIDED")

        # an expired access token is fine as long as there is a refresh token:
        # google-auth gets a new one by itself on the first request
        usable: bool = bool(
            self.credentials
            and (self.credentials.valid or self.credentials.refresh_token)
        )
        if not usable:
            self.credentials = self._login(
                credentials_file_path, application_type, port, code, pkce, redirect_uri
            )
            if not self.credentials:
                # WEB flow, step 1: the user has to open auth_url first
                return

        # save the credentials as a dict
        self.auth_token = json.loads(self.credentials.to_json())
        # Call the Gmail API and set the instance
        self.google_service = GoogleService(
            # no on-disk discovery cache: it needs oauth2client<4 and only logs "file_cache is only supported..."
            service=build("gmail", "v1", credentials=self.credentials, cache_discovery=False),
            user_id=user_id,
        )

    # ------------------------------------------------------------------ auth

    def _login(
        self,
        credentials_file_path: str,
        application_type: ApplicationType,
        port: int,
        code: str | None,
        pkce: bool,
        redirect_uri: str | None = None,
    ) -> Credentials | None:
        """Runs the OAuth login. Returns None when the WEB flow still waits for the user (auth_url is set)."""
        if not os.path.exists(credentials_file_path):
            raise FileNotFoundError(f"{credentials_file_path=} NOT FOUND!")

        if application_type == ApplicationType.INSTALLED:
            # one Flow object does both steps here, so the library handles PKCE by itself
            flow = InstalledAppFlow.from_client_secrets_file(
                credentials_file_path, self.scopes
            )
            return flow.run_local_server(port=port)

        self.redirect_uri = self._redirect_uri(credentials_file_path, port, redirect_uri)
        if code and pkce and not self.code_verifier:
            raise ValueError(
                "pkce=True needs the `code_verifier` created together with auth_url"
            )
        self.flow = Flow.from_client_secrets_file(
            credentials_file_path,
            self.scopes,
            redirect_uri=self.redirect_uri,
            code_verifier=self.code_verifier,
            # a new verifier only when starting the flow; step 2 must reuse the one from step 1
            autogenerate_code_verifier=pkce and not code,
        )
        if code:
            self.flow.fetch_token(code=code)
            return self.flow.credentials
        self.auth_url = self.flow.authorization_url(prompt="consent")[0]
        self.code_verifier = self.flow.code_verifier
        return None

    @staticmethod
    def _redirect_uri(credentials_file_path: str, port: int, wanted: str | None = None) -> str:
        """The Authorized redirect URI to use: `wanted` when given (it must be in the credentials file),
        else the one that uses `port`, else the first one of the file."""
        cred_payload: dict[str, typing.Any] | None = None
        with open(credentials_file_path, "r") as f:
            cred_payload = json.loads(f.read())
        if not cred_payload:
            raise Exception(f"Could't read {credentials_file_path=}")
        if "web" not in cred_payload:
            raise Exception(
                f"{cred_payload=} content missing."
                "\n\033[91mDid you create credentials for Web app?\033[0m"
            )
        redirect_uris = cred_payload["web"].get("redirect_uris")
        if not redirect_uris:
            raise Exception(
                f"Missing `redirect_uris` key from {cred_payload['web']}."
                "\n\033[91mDid you define Authorized redirect URIs?\033[0m"
            )
        if wanted:
            if wanted not in redirect_uris:
                raise ValueError(f"{wanted=} is not one of the credentials file's redirect_uris")
            return wanted
        matching = [uri for uri in redirect_uris if str(port) in uri]
        return matching[-1] if matching else redirect_uris[0]

    def get_auth_token(self) -> str:
        """Returns a string JSON representation of the credentials (including a refreshed access token). Store it and pass it as `auth_token` to skip the login next time."""  # noqa
        if self.credentials:
            return self.credentials.to_json()
        return json.dumps(self.auth_token)

    # -------------------------------------------------------------- messages

    def get_message(self, id: str) -> Message | None:
        if not self.google_service:
            return None
        return Message(
            google_service=self.google_service,
            **self._execute(self._messages().get(userId=self._user_id, id=id)),
        )

    def get_draft(self, id: str) -> Message | None:
        if not self.google_service:
            return None
        draft = self._execute(self._drafts().get(userId=self._user_id, id=id))
        return Message(google_service=self.google_service, **draft["message"])

    def send_message(
        self,
        sender: str,
        to: Addresses,
        subject: str,
        html: str | None = None,
        text: str | None = None,
        cc: Addresses = None,
        bcc: Addresses = None,
        attachments: Attachments = None,
        in_reply_to: str | Message | None = None,
        headers: dict | None = None,
        signature: bool = True,
        thread_id: str | None = None,
        references: Addresses = None,
        sender_name: str | None = None,
    ) -> dict:
        """Sends an email message.
        Args:
            sender (str): Email address of the message sender.
            to (list[str] | str): Email address(es) of the recipient(s).
            subject (str): Subject line of the email.
            html (str | None, optional): HTML content of the email body. Defaults to None.
            text (str | None, optional): Plain text content of the email body. Defaults to None.
            cc (list[str] | str | None, optional): Email address(es) to carbon copy. Defaults to None.
            bcc (list[str] | str | None, optional): Email address(es) to blind carbon copy. Defaults to None.
            attachments (list | str | AttachmentFile | None, optional): File paths and/or AttachmentFile(filename, data) objects. Defaults to None.
            in_reply_to (str | Message | None, optional): The message that is replyed to: its Message.message_id, or the
                Message itself (then its thread and References are used too, so the answer stays in the conversation). Defaults to None.
            headers (dict | None, optional): Extra headers, as key: value. Defaults to None.
            signature (bool, optional): Whether to include a signature (if configured). Defaults to True.
            thread_id (str | None, optional): Message.threadId of the conversation the message belongs to. Gmail only
                keeps it in that thread when the subject matches and in_reply_to/references are set. Defaults to None.
            references (list[str] | str | None, optional): Message-IDs of the conversation so far. Defaults to in_reply_to.
            sender_name (str | None, optional): Display name shown next to the sender address. Defaults to None.
        Returns:
            dict: The sent message as Gmail answers it: {"id", "threadId", "labelIds"}.
        """  # noqa
        if isinstance(in_reply_to, Message):
            answered: Message = in_reply_to
            in_reply_to = answered.message_id
            thread_id = thread_id or answered.threadId
            if not references and in_reply_to:
                references = [*(answered.references or "").split(), in_reply_to]
        msg = EmailMessage()
        msg["To"] = _join(to)
        msg["From"] = (
            utils.formataddr((sender_name, sender))
            if sender_name
            else str(Header(f"{sender} <{sender}>"))
        )
        msg["Subject"] = _reply_subject(subject) if in_reply_to else subject
        msg["Date"] = utils.formatdate(localtime=1)
        if cc:
            msg["Cc"] = _join(cc)
        if bcc:
            msg["Bcc"] = _join(bcc)
        if in_reply_to:
            msg["In-Reply-To"] = in_reply_to
            msg["References"] = _join(references, " ") or in_reply_to
        if signature and html:
            account_signature = self._alias_info(sender)
            html = f"{html}<br/><br/>{account_signature['signature'] if 'signature' in account_signature else ''}"
        if text:
            msg.set_content(text.strip())
        if html:
            msg.add_alternative(html.strip(), subtype="html")
        for key, value in (headers or {}).items():
            msg.add_header(key, value)
        for attachment in _as_list(attachments):
            file = _load_attachment(attachment)
            maintype, _, subtype = (
                file.mimetype or "application/octet-stream"
            ).partition("/")
            msg.add_attachment(
                file.data,
                maintype=maintype,
                subtype=subtype or "octet-stream",
                filename=file.filename,
            )

        body: dict = {"raw": base64.urlsafe_b64encode(msg.as_bytes()).decode()}
        if thread_id:
            body["threadId"] = thread_id
        # the connection is left open here, exactly as before 1.5.0
        return self._messages().send(userId=self._user_id, body=body).execute()

    def reply_to_message(
        self,
        message: Message,
        sender: str,
        html: str | None = None,
        text: str | None = None,
        reply_all: bool = False,
        cc: Addresses = None,
        bcc: Addresses = None,
        attachments: Attachments = None,
        headers: dict | None = None,
        signature: bool = True,
        sender_name: str | None = None,
    ) -> dict:
        """Answers a message inside its conversation (same thread, "Re:" subject, In-Reply-To + References).
        Args:
            message (Message): The message that is answered (from get_message / get_thread, with its headers).
            sender (str): Email address the reply is sent from (the mailbox owner or one of its aliases).
            reply_all (bool, optional): Also copy everybody from the To and Cc of the answered message. Defaults to False.
            cc (list[str] | str | None, optional): Extra addresses to copy, on top of the reply_all ones.
            (html, text, bcc, attachments, headers, signature, sender_name: same as send_message)
        Returns:
            dict: The sent message as Gmail answers it: {"id", "threadId", "labelIds"}.
        """  # noqa
        to, reply_cc = reply_recipients(message, own_address=sender, reply_all=reply_all)
        known: set[str] = {_address(x) for x in to + reply_cc}
        extra_cc: list[str] = [x for x in _as_list(cc) if _address(x) not in known]
        # the chain so far + the answered message: this is what keeps a long conversation together
        references: list[str] = (
            message.references or message.in_reply_to or ""
        ).split()
        if message.message_id and message.message_id not in references:
            references.append(message.message_id)
        return self.send_message(
            sender=sender,
            to=to,
            subject=message.subject or "",
            html=html,
            text=text,
            cc=reply_cc + extra_cc,
            bcc=bcc,
            attachments=attachments,
            in_reply_to=message.message_id,
            headers=headers,
            signature=signature,
            thread_id=message.threadId,
            references=references,
            sender_name=sender_name,
        )

    def get_inbox_messages(
        self,
        max_results: int = MAX_RESULTS,
        next_page_token: str | None = None,
        existing_pages: list[str] | str | None = None,
        previous_page_token: str | None = None,
        query: SearchParams | str | None = None,
    ) -> GetMessagesResponse:
        return self._get_messages(
            max_results=max_results,
            labels=[Labels.INBOX],
            next_page_token=next_page_token,
            existing_pages=existing_pages,
            previous_page_token=previous_page_token,
            query=_query(query),
        )

    def get_trash_messages(
        self,
        max_results: int = MAX_RESULTS,
        next_page_token: str | None = None,
        existing_pages: list[str] | str | None = None,
        previous_page_token: str | None = None,
        query: SearchParams | str | None = None,
    ) -> GetMessagesResponse:
        return self._get_messages(
            max_results=max_results,
            labels=[Labels.TRASH],
            next_page_token=next_page_token,
            existing_pages=existing_pages,
            previous_page_token=previous_page_token,
            query=_query(query),
        )

    def get_spam_messages(
        self,
        max_results: int = MAX_RESULTS,
        next_page_token: str | None = None,
        existing_pages: list[str] | str | None = None,
        previous_page_token: str | None = None,
        query: SearchParams | str | None = None,
    ) -> GetMessagesResponse:
        return self._get_messages(
            max_results=max_results,
            labels=[Labels.SPAM],
            next_page_token=next_page_token,
            existing_pages=existing_pages,
            previous_page_token=previous_page_token,
            query=_query(query),
        )

    def get_messages(
        self,
        includeSpamTrash: bool = False,
        max_results: int = MAX_RESULTS,
        labels: list[Labels] | list[str] | None = None,
        next_page_token: str | None = None,
        existing_pages: list[str] | str | None = None,
        previous_page_token: str | None = None,
        query: SearchParams | str | None = None,
    ) -> GetMessagesResponse:
        return self._get_messages(
            includeSpamTrash=includeSpamTrash,
            max_results=max_results,
            labels=labels,
            next_page_token=next_page_token,
            existing_pages=existing_pages,
            previous_page_token=previous_page_token,
            query=_query(query),
        )

    def get_draft_messages(
        self,
        includeSpamTrash: bool = False,
        max_results: int = MAX_RESULTS,
        next_page_token: str | None = None,
        existing_pages: list[str] | str | None = None,
        previous_page_token: str | None = None,
        query: SearchParams | str | None = None,
    ) -> GetMessagesResponse:
        return self._get_drafts(
            includeSpamTrash=includeSpamTrash,
            max_results=max_results,
            next_page_token=next_page_token,
            existing_pages=existing_pages,
            previous_page_token=previous_page_token,
            query=_query(query),
        )

    def get_attachment(
        self, message_id: str, attachment_id: str
    ) -> MessagePartBody | None:
        return MessagePartBody(
            **self._execute(
                self._messages()
                .attachments()
                .get(userId=self._user_id, messageId=message_id, id=attachment_id)
            )
        )

    # --------------------------------------------------------------- threads

    def get_thread(
        self,
        id: str,
        format: str = "full",
        metadata_headers: list[str] | None = None,
    ) -> Thread | None:
        """Retrieves one conversation with all its messages (oldest first).
        Args:
            id (str): Thread id (Message.threadId / Thread.id).
            format (str, optional): "full" (bodies + attachments), "metadata" (headers and labels only)
                or "minimal" (ids and labels only). Defaults to "full".
            metadata_headers (list[str] | None, optional): With format="metadata": the headers to return.
        """
        if not self.google_service:
            return None
        return Thread(
            google_service=self.google_service,
            **self._execute(self._thread_request(id, format, metadata_headers)),
        )

    def get_threads(
        self,
        includeSpamTrash: bool = False,
        max_results: int = MAX_RESULTS,
        labels: list[Labels] | list[str] | None = None,
        next_page_token: str | None = None,
        existing_pages: list[str] | str | None = None,
        previous_page_token: str | None = None,
        query: SearchParams | str | None = None,
        format: str = "metadata",
        metadata_headers: list[str] | None = None,
    ) -> GetThreadsResponse:
        """Retrieves conversations from a user's mailbox, newest first, each with its messages.
        Args:
            includeSpamTrash (bool, optional): If True, includes threads from spam and trash. Defaults to False.
            max_results (int, optional): Maximum number of threads to return (Gmail allows up to 100 per batch). Defaults to MAX_RESULTS (10).
            labels (list[Labels] | list[str] | None, optional): Only threads with all these labels. Defaults to None (all).
            next_page_token (str | None, optional): Page token for fetching the next page of results.
            existing_pages (list[str] | str | None, optional): Page tokens seen so far (from the previous response).
            previous_page_token (str | None, optional): Page token for fetching the previous page of results.
            query (SearchParams | str | None, optional): Gmail search query, ex: "is:unread from:someone@example.com".
            format (str, optional): How much of each message to load: "metadata" (headers + labels, fast, good for
                a list), "full" (bodies + attachments) or "minimal". Defaults to "metadata".
            metadata_headers (list[str] | None, optional): With format="metadata": the headers to return.
                Defaults to THREAD_LIST_HEADERS.
        Returns:
            GetThreadsResponse: The threads and the pagination information.
        """  # noqa
        existing_pages, next_page_token = self._page_tokens(
            existing_pages, previous_page_token, next_page_token
        )
        listed = ThreadsList(
            **self._execute(
                self._threads().list(
                    userId=self._user_id,
                    maxResults=max_results or self.max_results,
                    labelIds=[_label_id(x) for x in labels or []],
                    includeSpamTrash=includeSpamTrash,
                    pageToken=next_page_token,
                    q=_query(query) or "",
                )
            )
        )
        responses = self._batch(
            [
                self._thread_request(thread.id, format, metadata_headers)
                for thread in listed.threads
            ]
        )
        threads: list[Thread] = []
        for identifiers, response in zip(listed.threads, responses):
            if not response:
                continue
            thread = Thread(google_service=self.google_service, **response)
            thread.snippet = identifiers.snippet  # only the list call returns it
            threads.append(thread)
        return GetThreadsResponse(
            threads=threads,
            **self._pagination(existing_pages, next_page_token, listed.nextPageToken),
        )

    def get_inbox_threads(
        self,
        max_results: int = MAX_RESULTS,
        next_page_token: str | None = None,
        existing_pages: list[str] | str | None = None,
        previous_page_token: str | None = None,
        query: SearchParams | str | None = None,
        format: str = "metadata",
        metadata_headers: list[str] | None = None,
    ) -> GetThreadsResponse:
        return self.get_threads(
            max_results=max_results,
            labels=[Labels.INBOX],
            next_page_token=next_page_token,
            existing_pages=existing_pages,
            previous_page_token=previous_page_token,
            query=query,
            format=format,
            metadata_headers=metadata_headers,
        )

    def _thread_request(
        self, id: str, format: str, metadata_headers: list[str] | None
    ):
        params: dict = {"userId": self._user_id, "id": id, "format": format}
        if format == "metadata":
            params["metadataHeaders"] = metadata_headers or THREAD_LIST_HEADERS
        return self._threads().get(**params)

    # ------------------------------------------------------ labels / profile

    @property
    def labels(self) -> list[GmailLabel] | None:
        results = self._execute(self._labels().list(userId=self._user_id))
        return [GmailLabel(**label) for label in results.get("labels", [])]

    def get_label(self, id: Labels | str) -> GmailLabel:
        """One label with its counters (messagesTotal, messagesUnread, threadsTotal, threadsUnread)."""
        return GmailLabel(
            **self._execute(
                self._labels().get(userId=self._user_id, id=_label_id(id))
            )
        )

    def create_label(self, name: str) -> GmailLabel:
        """Create a label (a "folder" of the Gmail UI), shown in the label list and on its messages.
        A `/` in the name nests it ("Clients/Offers"). Gmail answers 409 for a name that already exists."""
        return GmailLabel(
            **self._execute(
                self._labels().create(
                    userId=self._user_id,
                    body={
                        "name": name,
                        "labelListVisibility": "labelShow",
                        "messageListVisibility": "show",
                    },
                )
            )
        )

    def unread_count(
        self, label: Labels | str = Labels.INBOX, threads: bool = True
    ) -> int:
        """Number of unread conversations (or messages, with threads=False) under a label. One cheap API call."""
        counters = self.get_label(label)
        return (counters.threadsUnread if threads else counters.messagesUnread) or 0

    @property
    def profile(self) -> GmailProfile | None:
        """Retrieves and caches the authorized user's Gmail profile information.
        This property is a cached accessor for the user's Gmail profile data.
        The first call will fetch the data from the Gmail API and store it internally.
        Subsequent calls will return the cached data unless it's explicitly cleared.
        Returns:
            GmailProfile | None: An object containing the user's Gmail profile information,
            or None if there's an error fetching the data.
        Raises:
            HttpError: An exception if there is an error fetching profile information from the Gmail API.
        """
        if not self.profile_data:
            self.profile_data = GmailProfile(
                **self._execute(
                    self.google_service.service.users().getProfile(
                        userId=self._user_id
                    )
                )
            )
        return self.profile_data

    def _alias_info(self, email_address: str) -> dict:
        """Retrieves information about a specific send-as alias for the authorized user.
        Args:
            email_address (str): The email address of the send-as alias to retrieve information for.
        Raises:
            HttpError: An exception if there is an error fetching alias information from the Gmail API.
        Returns:
            dict: A dictionary containing information about the alias, or an empty dictionary if the alias is not found.
        This method is private and intended for internal use.
        """  # noqa
        return self._execute(
            self.google_service.service.users()
            .settings()
            .sendAs()
            .get(sendAsEmail=email_address, userId=self._user_id)
        )

    # ------------------------------------------------------- listing helpers

    def _get_messages(
        self,
        max_results: int,
        includeSpamTrash: bool = False,
        labels: list[Labels] | None = None,
        next_page_token: str | None = None,
        existing_pages: list[str] | str | None = None,
        previous_page_token: str | None = None,
        query: str | None = None,
    ) -> GetMessagesResponse:
        """Retrieves messages from a user's mailbox.
        Args:
            includeSpamTrash (bool, optional): If True, includes messages from spam and trash folders. Defaults to False.
            max_results (int, optional): Maximum number of messages to return. Defaults to MAX_RESULTS (10).
            labels (Union[list[Labels], list[str], None], optional): List of label IDs or strings to filter by. Defaults to None (all labels).
            next_page_token (str, optional): Page token for fetching the next page of results.
            existing_pages (list[str] | str] | None optional): Used internally for pagination. Defaults to None.
            previous_page_token (str | None, optional): Page token for fetching the previous page of results.
            query (Union[SearchParams, str], optional): Search query to filter messages. Can be a string or a SearchParams object.
        Returns:
            GetMessagesResponse: An object containing the retrieved messages and pagination information.
        """  # noqa
        existing_pages, next_page_token = self._page_tokens(
            existing_pages, previous_page_token, next_page_token
        )
        listed: MessagesList = self._get_messages_ids(
            includeSpamTrash=includeSpamTrash,
            max_results=max_results,
            next_page_token=next_page_token,
            labels=labels,
            query=query,
        )
        responses = self._batch(
            [
                self._messages().get(userId=self._user_id, id=message.id)
                for message in listed.messages
            ]
        )
        return GetMessagesResponse(
            messages=[
                Message(google_service=self.google_service, **response)
                for response in responses
                if response
            ],
            **self._pagination(existing_pages, next_page_token, listed.nextPageToken),
        )

    def _get_drafts(
        self,
        max_results: int,
        includeSpamTrash: bool = False,
        next_page_token: str | None = None,
        existing_pages: list[str] | str | None = None,
        previous_page_token: str | None = None,
        query: str | None = None,
    ) -> GetMessagesResponse:
        """Retrieves drafts from a user's mailbox."""
        existing_pages, next_page_token = self._page_tokens(
            existing_pages, previous_page_token, next_page_token
        )
        listed: DraftsList = self._get_drafts_ids(
            max_results=max_results,
            includeSpamTrash=includeSpamTrash,
            next_page_token=next_page_token,
            query=query,
        )
        responses = self._batch(
            [
                self._drafts().get(userId=self._user_id, id=draft["id"])
                for draft in listed.drafts
            ]
        )
        return GetMessagesResponse(
            messages=[
                Message(google_service=self.google_service, **response["message"])
                for response in responses
                if response
            ],
            **self._pagination(existing_pages, next_page_token, listed.nextPageToken),
        )

    def _get_messages_ids(
        self,
        max_results: int | None,
        includeSpamTrash: bool = False,
        labels: list[Labels] | None = None,
        next_page_token: str | None = None,
        query: str | None = None,
    ) -> MessagesList:
        return MessagesList(
            **self._execute(
                self._messages().list(
                    userId=self._user_id,
                    maxResults=max_results or self.max_results,
                    labelIds=[_label_id(x) for x in labels or []],
                    includeSpamTrash=includeSpamTrash,
                    pageToken=next_page_token,
                    q=query if query else "",
                )
            )
        )

    def _get_drafts_ids(
        self,
        max_results: int | None,
        includeSpamTrash: bool = False,
        next_page_token: str | None = None,
        query: str | None = None,
    ) -> DraftsList:
        return DraftsList(
            **self._execute(
                self._drafts().list(
                    userId=self._user_id,
                    maxResults=max_results or self.max_results,
                    includeSpamTrash=includeSpamTrash,
                    pageToken=next_page_token,
                    q=query,
                )
            )
        )

    def _page_tokens(
        self,
        existing_pages: list[str] | str | None,
        previous_page_token: str | None,
        next_page_token: str | None,
    ) -> tuple[list[str], str | None]:
        """The page tokens seen so far and the token of the page to request.
        Gmail only gives a token for the NEXT page, so the caller sends back the tokens it already
        went through (`existing_pages`); going back = dropping the last ones and asking that page again."""
        pages: list[str] = (
            existing_pages.split(self.SEPARATOR_SYMBOL)
            if isinstance(existing_pages, str)
            else list(existing_pages or [])
        )
        if previous_page_token:
            if previous_page_token not in pages:
                raise InvalidToken(f"{previous_page_token=} not found in {pages=}")
            pages = pages[: pages.index(previous_page_token)]
            next_page_token = pages[-1] if pages else None
        return pages, next_page_token

    def _pagination(
        self, pages: list[str], requested_token: str | None, next_page_token: str | None
    ) -> dict:
        """Pagination fields shared by the list responses."""
        if requested_token and requested_token not in pages:
            pages.append(requested_token)
        return {
            "previous_page_token": pages[-1] if pages else requested_token,
            "existing_pages": self.SEPARATOR_SYMBOL.join(pages) if pages else None,
            "next_page_token": next_page_token,
        }

    # ------------------------------------------------------- request helpers

    @property
    def _user_id(self) -> str:
        return self.google_service.user_id

    def _messages(self):
        return self.google_service.service.users().messages()

    def _drafts(self):
        return self.google_service.service.users().drafts()

    def _threads(self):
        return self.google_service.service.users().threads()

    def _labels(self):
        return self.google_service.service.users().labels()

    def _execute(self, request) -> dict:
        """Runs one API request and closes the http connection. Raises HttpError when Gmail refuses it."""
        try:
            return request.execute()
        finally:
            self.google_service.service.close()

    def _batch(self, requests: list) -> list[dict | None]:
        """Runs the requests in one http batch. Answers come back in the order of the requests;
        a request Gmail refused gives None (the others are still returned)."""
        responses: dict[str, dict] = {}

        def on_response(request_id, response, exception) -> None:
            if not exception:
                responses[request_id] = response

        if not requests:
            return []
        try:
            batch = self.google_service.service.new_batch_http_request()
            for index, request in enumerate(requests):
                batch.add(request, callback=on_response, request_id=str(index))
            batch.execute()
        finally:
            self.google_service.service.close()
        return [responses.get(str(index)) for index in range(len(requests))]

    # -------------------------------------------------------------- contacts

    def get_contacts(self) -> list | None:
        request = (
            build("people", "v1", credentials=self.credentials, cache_discovery=False)
            .otherContacts()
            .list(pageSize=1000, readMask="emailAddresses,names")
            .execute()
        )
        return request["otherContacts"] if "otherContacts" in request else None

    def search_contacts(self, query: str) -> list | None:
        request = (
            build("people", "v1", credentials=self.credentials, cache_discovery=False)
            .otherContacts()
            .search(pageSize=30, readMask="emailAddresses,names", query=query)
            .execute()
        )
        return request["results"] if "results" in request else None


def reply_recipients(
    message: Message, own_address: str, reply_all: bool = False
) -> tuple[list[str], list[str]]:
    """Who an answer to `message` goes to: (to, cc), as "Name <address>" strings.
    - to: the Reply-To of the message, else its From. When the message is one we sent ourselves
      (a follow-up in a conversation), the answer goes to the people it was sent to.
    - cc: only with reply_all: everybody else from To and Cc. Our own address is never included."""
    own: str = _address(own_address)
    sender = utils.getaddresses([message.reply_to or message.sender_header or ""])
    recipients = utils.getaddresses([message.recipient or ""])
    copied = utils.getaddresses([message.cc or ""])

    sent_by_us: bool = any(address.casefold() == own for _, address in sender)
    to = recipients if sent_by_us else sender
    others = copied if sent_by_us else recipients + copied

    seen: set[str] = {own}
    result: list[list[str]] = []
    for group in (to, others if reply_all else []):
        formatted: list[str] = []
        for name, address in group:
            if not address or address.casefold() in seen:
                continue
            seen.add(address.casefold())
            formatted.append(utils.formataddr((name, address)))
        result.append(formatted)
    return result[0], result[1]


def _address(value: str) -> str:
    """The bare, lowercased email address of "Name <address>"."""
    return utils.parseaddr(value)[1].casefold()


def _as_list(value) -> list:
    if not value:
        return []
    return list(value) if isinstance(value, (list, tuple)) else [value]


def _join(value: Addresses, separator: str = ", ") -> str:
    return separator.join(_as_list(value))


def _query(query: SearchParams | str | None) -> str | None:
    return query.query if isinstance(query, SearchParams) else query


def _label_id(label: Labels | str) -> str:
    return label.value if isinstance(label, Labels) else label


def _reply_subject(subject: str) -> str:
    """"Re: subject", without stacking a second "Re:" on a subject that already has one."""
    subject = subject or ""
    return subject if subject.casefold().startswith("re:") else f"Re: {subject}"


def _load_attachment(attachment: str | AttachmentFile) -> AttachmentFile:
    """A file path or an AttachmentFile, as an AttachmentFile with its content and mimetype."""
    if isinstance(attachment, AttachmentFile):
        file = attachment
    else:
        with open(attachment, "rb") as fp:
            file = AttachmentFile(filename=os.path.basename(attachment), data=fp.read())
    if not file.mimetype:
        # unknown extension: sent as a generic binary file
        file = AttachmentFile(
            filename=file.filename,
            data=file.data,
            mimetype=mimetypes.guess_type(file.filename)[0],
        )
    return file
