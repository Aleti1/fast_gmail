# Fast-gmail a simple python wrapper for gmailapi

---
## Functionalities:
- Send text/html messages
- Send messages with signature & attachments & custom headers
- Get messages with pagination
- Filter messages
- Get drafts
- Edit message labels
- Get message attachments
- Conversations (threads): list, read, mark read/unread
- Reply / reply all inside a conversation
- Unread counter
- Custom OAuth scopes and PKCE


## Instalation:
`pip install fast-gmail`

---

## Usage:

### Initialization
- Go to https://console.developers.google.com/apis/credentials and login with correct account
- Setup Oauth consent screen
- Create new credentials with OAuth client ID for web or installed app
- Set Authorized redirect URIs to http://localhost:3000/ (Notice the trailing slash)
- Download the credentials.json file
- Go to Enable APIs & services and enable GmailAPI & PeopleApi(used for contacts)

With credentials.json file downloaded we can connect to Gmail
```python
gmail = GmailApi(
    credentials_file_path = __path_to_credentials_json_file__,  # Defaults to ./credentials.json
    port = 3000, # Defaults to 3000  !IMPORTANT: if you change this default value don't forget to also changed on Authorized redirect URIs
)
```

Optional arguments:
```python
gmail = GmailApi(
    scopes = ["https://www.googleapis.com/auth/gmail.readonly"],  # Defaults to fast_gmail.SCOPES (gmail.modify + settings + contacts)
)
```
A stored token only works with the scopes it was granted: after changing them, log in again.

#### Web login (two steps)
```python
# step 1: no token yet -> send the user to Google
gmail = GmailApi(credentials_file_path=path)
redirect(gmail.auth_url)

# step 2: Google calls your redirect URI with ?code=...
gmail = GmailApi(credentials_file_path=path, code=request.GET["code"])
save(gmail.get_auth_token())           # keep it, it holds the refresh token

# later: no login needed
gmail = GmailApi(credentials_file_path=path, auth_token=saved_token)
```

#### One credentials file, several redirect URIs
When the client lists more than one Authorized redirect URI (dev, staging, production), say which one this
environment uses. Pass the same value in both steps.
```python
gmail = GmailApi(credentials_file_path=path, redirect_uri="https://app.example.com/gmail/callback")
```
Without it, the URI containing `port` is used, else the first one of the file.

#### Web login with PKCE
PKCE (RFC 7636) protects the `code` exchange. It is off by default; with `pkce=True` step 1 also creates
a `code_verifier` that step 2 must send back, so keep it (in the user session, for example) next to the login.
```python
gmail = GmailApi(credentials_file_path=path, pkce=True)
session["code_verifier"] = gmail.code_verifier
redirect(gmail.auth_url)

gmail = GmailApi(
    credentials_file_path=path,
    pkce=True,
    code=request.GET["code"],
    code_verifier=session.pop("code_verifier"),
)
```
The installed-app login (`application_type=ApplicationType.INSTALLED`) uses PKCE by itself.

### Examples
- FastAPI
- Django
- Flask (comming soon)

### Send message
```python
    from fast_gmail import GmailApi

    messages = GmailApi().send_message(
        sender: str,
        to: List[str] | str,
        subject: str,
        html: Optional[str]=None,
        text: Optional[str]=None,
        cc: Optional[List[str] | str]=None,
        bcc: Optional[List[str] | str]=None,
        attachments: Optional[List[str | AttachmentFile] | str | AttachmentFile]=None,
        in_reply_to: Optional[str] = None,
        headers: Optional[dict] = None,
        signature: bool = True,
        thread_id: Optional[str] = None,
        references: Optional[List[str] | str] = None,
        sender_name: Optional[str] = None,
    )
    """Sends an email message.
        Args:
            sender (str): Email address of the message sender.
            to (List[str] | str): Email address(es) of the recipient(s).
            subject (str): Subject line of the email.
            html (Optional[str], optional): HTML content of the email body. Defaults to None.
            text (Optional[str], optional): Plain text content of the email body. Defaults to None.
            cc (Optional[List[str] | str], optional): List of email addresses to carbon copy. Defaults to None.
            bcc (Optional[List[str] | str], optional): List of email addresses to blind carbon copy. Defaults to None.
            attachments (optional): File paths and/or AttachmentFile(filename, data, mimetype=None) objects (content kept in memory). Defaults to None.
            in_reply_to (Optional[str], optional): Message.message_id value that is replyed to. Defaults to None.
            headers (Optional[str], optional): Custom headers for message. Ex: {"List-Subscribe": "example.com/unsubscribe"}
            signature (bool, optional): Whether to include a signature (if configured). Defaults to True.
            thread_id (Optional[str], optional): Message.threadId of the conversation the message belongs to.
            references (Optional[List[str] | str], optional): Message-IDs of the conversation so far. Defaults to in_reply_to.
            sender_name (Optional[str], optional): Display name shown next to the sender address.
        Returns:
            dict: The sent message as Gmail answers it: {"id", "threadId", "labelIds"}.
    """
```

### Reply to a message
Answers inside the same conversation: "Re:" subject, `In-Reply-To` + `References` headers and the thread id are set for you.
```python
    from fast_gmail import GmailApi, AttachmentFile

    gmail = GmailApi()
    message = gmail.get_message(id)
    gmail.reply_to_message(
        message,
        sender="office@example.com",
        html="<p>Thank you!</p>",
        reply_all=True,                 # also copy everybody from To and Cc (never your own address)
        cc=["boss@example.com"],        # extra addresses
        attachments=[AttachmentFile("offer.pdf", pdf_bytes), "/path/to/file.png"],
        sender_name="Ana from Example",
    )
```
The reply goes to the `Reply-To` of the message, else to its `From`. `fast_gmail.reply_recipients(message, own_address, reply_all)`
returns the same `(to, cc)` lists without sending anything (handy to pre-fill a reply form).

### Inline images and address lists
```python
    message = gmail.get_message(id)
    message.html_with_images()      # html with <img src="cid:..."> replaced by the embedded images (data: URIs)
    message.inline_images           # {content_id: Attachment}
    message.recipient_addresses     # ["a@example.com", "b@example.com"]
    message.cc_addresses
    message.short_date_string()     # "14:05" today, "Nov 10" this year, "November 10, 2025" older
```

### Threads (conversations)
```python
    gmail = GmailApi()

    # list: newest first, same pagination arguments as get_messages
    response = gmail.get_inbox_threads(max_results=20, query="is:unread")
    for thread in response:
        print(thread.subject, thread.message_count, thread.is_unread, thread.snippet)
    next_page = gmail.get_inbox_threads(next_page_token=response.next_page_token, existing_pages=response.existing_pages)

    # any label / search
    gmail.get_threads(labels=[Labels.SENT], query="from:someone@example.com")

    # one conversation with full bodies and attachments, oldest message first
    thread = gmail.get_thread(thread_id)
    for message in thread:
        print(message.sender, message.html)

    thread.mark_as_read()
    thread.mark_as_unread()
    thread.modify_labels(labels_to_add=[Labels.STARRED], labels_to_remove=[Labels.INBOX])
    thread.move_to_trash()
```
`get_threads` loads only headers and labels of each message by default (`format="metadata"`, fast); pass `format="full"` to also get the bodies.

### Unread counter
```python
    gmail.unread_count()                              # unread conversations in INBOX
    gmail.unread_count(Labels.SPAM, threads=False)    # unread messages in SPAM
    gmail.get_label(Labels.INBOX)                     # GmailLabel with all four counters
```

### Get messages
```python
    messages = GmailApi().get_messages(
        includeSpamTrash: bool = False,
        max_results: int = 10,
        labels: Union[List[Labels], List[str], None] = None,
        next_page_token: str = None,
        existing_pages: Optional[List[str] | str] = None,
        previous_page_token: Optional[str] = None,
        query: Union[SearchParams, str] = None,
    )
    """Retrieves messages from a user's mailbox.
        Args:
            includeSpamTrash (bool, optional): If True, includes messages from spam and trash folders. Defaults to False.
            max_results (int, optional): Maximum number of messages to return. Defaults to MAX_RESULTS (10).
            labels (Union[List[Labels], List[str], None], optional): List of label IDs or strings to filter by. Defaults to None (all labels).
            next_page_token (str, optional): Page token for fetching the next page of results.
            existing_pages (Optional[List[str] | str], optional): Used internally for pagination. Defaults to None.
            previous_page_token (Optional[str], optional): Page token for fetching the previous page of results.
            query (Union[SearchParams, str], optional): Search query to filter messages. Can be a string or a SearchParams object. 
        Returns:
            GetMessagesResponse: An object containing the retrieved messages and pagination information.
    """
```

### Get INBOX/SPAM/TRASH messages
```python
    messages = GmailApi().get_inbox_messages(
        max_results: int = MAX_RESULTS,
        next_page_token: str = None,
        existing_pages: Optional[List[str] | str] = None,
        previous_page_token: Optional[str] = None,
        query: Union[SearchParams, str] = None
    )

    # helpers for spam or trash
    messages = GmailApi().get_spam_messages()
    messages = GmailApi().get_trash_messages()
```

### GET message
```python
    message = GmailApi().get_message(id)
    # returns a Message object
```

### GET attachment
```python
    message = GmailApi().get_message(id)
    attachment_id = None
    attachment_name = None
    for attacment in message.attachments:
        attachment_id = attachment.part_id
        attachment_name = attachment.filename

    # get attachment by id
    by_id = message.get_attachment(id=attachment_id)
    # or by filename
    by_name = message.get_attachment(filename=attachment_name) # returns an Attachment object

    # save file to disk
    by_id.save(filepath=f"/tmp/{attachment.filename}", overwrite=True)
```

### GET contacts
```python
    contacts = GmailApi().get_contacts()
    for contact in contacts:
        if "emailAddresses" in contact and contact["emailAddresses"]:
            print(contact["emailAddresses"][0]["value"])
```

### Search contacts
```python
    contacts = GmailApi().search_contacts(query="example@gmail.com")
    for contact in contacts:
        if "person" in contact and contact["person"]:
            print(contact["person"]["emailAddresses"][0]["value"])
```

### Message actions
```python
    message = GmailApi().get_message(id)

    # mark read or unread
    message.toggle_read_unread
    # or
    message.mark_as_read
    # or
    message.mark_as_unread

    # spam
    message.toggle_spam
    # or
    message.mark_spam
    message.mark_not_spam

    # trash
    message.toggle_trash
    # or
    message.move_to_trash
    message.move_from_trash

    # starred
    message.toggle_starred
    message.mark_starred
    message.mark_not_starred

    #important
    message.toggle_important
    message.mark_important
    message.mark_not_important

    # other properties
    message.body
    message.html
    message.plain
    message.recipient
    message.subject
    message.sender
    message.snippet
    message.is_starred
    message.is_important
    message.is_spam
    message.is_unread
    ...

```

---

## Classes:

### class GmailApi:
###### Attributes:

- **credentials (Optional[Credentials])**: Stores user credentials (OAuth tokens) for accessing Gmail.
- **google_service (GoogleService)**: An instance of GoogleService used for making API requests.
- **max_results (int)**: Maximum number of messages to retrieve per request (default 10).
- **SEPARATOR_SYMBOL (str)**: String used for separating page tokens during pagination.
- **profile_data (Optional[GmailProfile])**: Caches the user's Gmail profile information.
- **application_type: ApplicationType = ApplicationType.WEB**: Type of application WEB or INSTALLED,
- **code: Optional[str] = None**: gmail oAuth response code, exchanged for the token after a successful login
- **scopes: Optional[List[str]] = None**: OAuth scopes to ask for (defaults to fast_gmail.SCOPES)
- **pkce: bool = False** / **code_verifier: Optional[str] = None**: PKCE for the web login (see Initialization)
- **auth_url (str)**: Web login, step 1: the Google page the user has to open

###### Constructor (__init__):
- Initializes the GmailApi object.
- Reads credentials from the `auth_token` argument, else starts the login with the credentials file.
- An expired token with a refresh token is refreshed automatically on the first request; `get_auth_token()` returns the current one.
- Creates a GoogleService instance for making API calls.

###### Methods:
###### Message Retrieval:
- **get_message(id: str)-> Optional[Message]**: Retrieves a message by its ID.
- **get_draft(id: str)-> Optional[Message]**: Retrieves a draft by its ID.
###### Message Sending:
- **send_message(sender, to, subject, ...)-> dict**: Sends an email message with various options (text, HTML, attachments, signature).
- **reply_to_message(message, sender, ...)-> dict**: Answers a message inside its conversation (reply / reply all).
###### Threads:
- **get_threads() / get_inbox_threads()-> GetThreadsResponse**: Retrieves conversations with pagination and filtering.
- **get_thread(id: str)-> Optional[Thread]**: Retrieves one conversation with all its messages.
###### Inbox Management:
- **get_inbox_messages()-> GetMessagesResponse**: Retrieves messages from the inbox.
Similar methods exist for getting trash, spam, and all messages with various filtering options.
###### Drafts Management:
- **get_draft_messages()**: Retrieves draft messages.
###### Attachment Management:
- **get_attachment(message_id: str, attachment_id: str) -> Optional[MessagePartBody]**: Retrieves an attachment from a message.
###### Profile and Label Management:
- **labels**: Returns a list of user labels.
- **get_label(id)-> GmailLabel**: One label with its total/unread counters.
- **unread_count(label=Labels.INBOX, threads=True)-> int**: Unread conversations (or messages) under a label.
- **profile**: Retrieves and caches the user's Gmail profile information.

Overall, this code provides a well-structured and functional interface for interacting with Gmail using the Gmail API.

---

### class Message:
###### Properties:
- **id**: Unique identifier for the message.
- **snippet**: Shortened summary of the message content.
- **threadId**: Thread ID that groups related messages together.
- **historyId**: Unique identifier for a specific message history change.
- **sizeEstimate**: Approximate size of the message in bytes.
- **internalDate**: Internal timestamp representing when the message was created.
- **payload**: Object of type MessagePart containing the parsed content of the message body and attachments.
- **raw**: Optional property containing the raw email data (if available).
- **labelIds**: List of label IDs associated with the message.
- **labels**: List of GmailLabel objects representing the message's labels (fetched on demand).

###### Additional Message Properties:
- **message_headers**: Returns a list of MessageHeader objects from the message's payload (if available).
- **body**: Returns the message body content (combines plain text and HTML if both exist).
- **html**: Returns the HTML content of the message body (if available).
- **plain**: Returns the plain text content of the message body (if available).
- **alternative**: Returns the text content of the most appropriate alternative part (if message uses multipart/alternative).
- **recipient**: Extracts the recipient's email address from the "To" header (if available).
- **message_id**: Extracts the message ID from the message headers (if available).
- **subject**: Extracts the subject line from the message headers (if available).
- **sender**: Extracts the sender's email address from the "From" header (if available).
- **has_attachments**: Checks if the message or its nested parts contain attachments.
- **attachments**: Returns a list of Attachment objects for all attachments within the message.
- **is_unread, is_starred, is_important, etc.**: Boolean properties indicating the message's label status (unread, starred, important, spam, draft, trash).
- **created_date**: Converts the internalDate to a datetime object representing the message creation time.
- **date**: Parses the "Received" or "Date" header to get the message delivery date (if available).
- **date_string**: Formats the delivery date according to a specified format string (defaults to "%a, %d %b %Y %H:%M:%S %z").

---

###### Methods:
- **mark_as_read, mark_as_unread**: Toggles the unread flag for the message.
- **toogle_read_unread**: Shortcut to toggle the unread flag based on the current state.
- **mark_spam, mark_not_spam**: Toggles the spam label for the message.
- **toggle_spam**: Shortcut to toggle the spam label based on the current state.
- **move_to_trash, move_from_trash**: Toggles the trash label for the message.
- **toggle_trash**: Shortcut to toggle the trash label based on the current state.
- **mark_important, mark_not_important**: Toggles the important label for the message.
- **toggle_important**: Shortcut to toggle the important label based on the current state.
- **mark_starred, mark_not_starred**: Toggles the starred label for the message.
- **toggle_starred**: Shortcut to toggle the starred label based on the current state.
- **get_attachment(filename=None, id=None)**: Retrieves an attachment by filename or internal part ID.
- **get_labels**: Fetches and returns a list of GmailLabel objects for all labels associated with the message.
- **add_label(label), add_labels(labels)**: Adds labels to the message.
- **remove_label(label), remove_labels(labels)**: Removes labels from the message.
- **modify_labels(labels_to_add=None, labels_to_remove=None)**: Updates message labels by adding and/or removing labels.

Overall, this Message class provides a comprehensive way to access and manage individual email messages within a Gmail account. It allows you to retrieve message details, content, attachments, labels, and perform various actions like marking as read/unread, starring, labeling, and trash management.

---

### class Attachment:
###### Properties:
- **filename (str)**: This attribute stores the filename of the attachment.
- **mimeType (str)**: This attribute stores the MIME type of the attachment content, which specifies the format of the data (e.g., image/jpeg, text/plain).
- **part_id (str)**: This attribute stores the internal identifier for the attachment within the message parts. This ID is used to download the attachment using the Gmail API.
- **google_service (GoogleService)**: This attribute holds a reference to the GoogleService object used for downloading the attachment. This object likely encapsulates authentication and communication details with the Gmail API.
- **id (Optional[str])**: This optional attribute stores the ID of the attachment generated by Gmail after a message is fetched using the .get() method. This ID might change for the same attachment across different fetches.
- **data (Optional[bytes])**: This optional attribute stores the content of the attachment (set for small attachments, or after download()).
- **size (Optional[int])**: Size in bytes, as reported by Gmail.
- **is_inline (bool)** / **content_id (Optional[str])**: Set for images shown inside the html body (`cid:` references).

###### Methods:
- **download() -> None**: This method downloads the attachment data from the Gmail API if it hasn't been downloaded already. It raises exceptions for errors like missing message ID or HTTP errors during download.
- **save(filepath: Optional[str] = None, overwrite: bool = False) -> None**: This method saves the attachment data to a file. It allows specifying the filepath and whether to overwrite existing files. It raises an error if the file already exists and overwrite is set to False.

Overall, the Attachment class provides functionality to manage attachments associated with Gmail messages. It handles downloading attachments from the API, storing downloaded data, and saving them to local files.

---

### class Thread:
###### Attributes / properties:
- **id, historyId, snippet**, **messages (List[Message])**: the conversation, oldest message first.
- **subject, message_count, first_message, last_message, participants, is_unread, has_attachments, attachments**
###### Methods:
- **mark_as_read() / mark_as_unread()**, **modify_labels(labels_to_add, labels_to_remove)**, **move_to_trash() / move_from_trash()**: applied to every message of the conversation in one API call.

---

### class GetMessagesResponse:
###### Attributes:
- **next_page_token (Optional[str], optional)**: Token for fetching the next page of results. Defaults to None.
- **existing_pages (Optional[str], optional)**: Used internally for pagination. Defaults to None. List like string of page tokens separated by GmailApi.SEPARATOR_SYMBOL
- **previous_page_token (Optional[List[str | None]], optional)**: Token for fetching the previous page of results (may be empty list). Defaults to [].
- **messages (List[Message])**: List of retrieved message objects.

---

## Changelog

### 1.7.0
- `GmailApi(redirect_uri=...)`: choose which Authorized redirect URI of the credentials file the web login uses,
  for one OAuth client shared by several environments. It must be one of the file's `redirect_uris`.

### 1.6.0
- `send_message(in_reply_to=message)`: pass the answered `Message` itself and its thread and References are used.
- `Message.html_with_images()`: the html body with its inline (`cid:`) images embedded as `data:` URIs; `Message.inline_images`.
- `Message.recipient_addresses` / `Message.cc_addresses`: only the email addresses of To / Cc, as lists.
- `Message.short_date_string()`: hour for today, day and month for this year, full date for older messages.
- `MessagePart.has_attachments()` (public name of `_has_attachments`).
- `get_contacts` / `search_contacts` also return the contact names.
- The Gmail client is built with `cache_discovery=False`: no more "file_cache is only supported with oauth2client<4.0.0" log line.

### 1.5.0
- Threads: `get_threads`, `get_inbox_threads`, `get_thread`, class `Thread` (mark read/unread, labels, trash).
- Replies: `reply_to_message` (reply / reply all), `send_message(thread_id=, references=, sender_name=)`.
- Attachments from memory with `AttachmentFile`; files with an unknown extension no longer crash the send.
- `unread_count` and `get_label`.
- Auth: `scopes` argument, PKCE for the web login (`pkce`, `code_verifier`), `get_auth_token()` returns the refreshed token.
- Message: `cc`, `reply_to`, `references`, `in_reply_to`, `header(name)`; headers are matched case-insensitively;
  bodies are decoded with their own charset; attachments nested in other parts are found; `Attachment.size/is_inline/content_id`.
- Google libraries updated: google-api-python-client 2.202+, google-auth-httplib2 0.4.4+, google-auth-oauthlib 1.5+.
- Behaviour changes to check when upgrading:
  - listing messages/drafts now raises `HttpError` when Gmail refuses the request (before: an empty list was returned);
  - `get_draft` returns the draft's message (before: an object without content);
  - a single address passed as a string to `cc`/`bcc` and a single path passed to `attachments` now work as documented;
  - `Attachment.data` of small (inline) attachments is `bytes`, like after `download()`.
