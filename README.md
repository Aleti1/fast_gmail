# Fast-gmail a simple python wrapper for gmailapi

---
## Functionalities:
- Send text/html messages
- Send messages with signature & attachments
- Get messages with pagination
- Filter messages
- Get drafts
- Edit message labels
- Get message attachments


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

### Examples
- FastAPI
- Django
- Flask (comming soon)

### Send message
```python
    from fast_gmail import GmailApi

    messages = GmailApi().send_message(
        sender: str,
        to: str,
        subject: str,
        html: Optional[str]=None,
        text: Optional[str]=None,
        cc: Optional[List[str] | str]=None,
        bcc: Optional[List[str] | str]=None,
        attachments: Optional[List[str] | str]=None,
        in_reply_to: Optional[str] = None,
        signature: bool = True
    )
    """Sends an email message.
        Args:
            sender (str): Email address of the message sender.
            to (str): Email address of the recipient.
            subject (str): Subject line of the email.
            html (Optional[str], optional): HTML content of the email body. Defaults to None.
            text (Optional[str], optional): Plain text content of the email body. Defaults to None.
            cc (Optional[List[str] | str], optional): List of email addresses to carbon copy. Defaults to None.
            bcc (Optional[List[str] | str], optional): List of email addresses to blind carbon copy. Defaults to None.
            attachments (Optional[List[str] | str], optional): List of file paths to attach to the email. Defaults to None.
            in_reply_to (Optional[str], optional): Message.message_id value that is replyed to. Defaults to None.
            signature (bool, optional): Whether to include a signature (if configured). Defaults to True.
        Returns:
            Optional[Message]: An object representing the sent message, or None on error.
    """
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
- **code: Optional[str] = None**: gmail oAuth response code for creating token.json file after successful login

###### Constructor (__init__):
- Initializes the GmailApi object.
- Reads credentials from token and credentials files.
- Handles refreshing expired tokens.
- Creates a GoogleService instance for making API calls.

###### Methods:
###### Message Retrieval:
- **get_message(id: str)-> Optional[Message]**: Retrieves a message by its ID.
- **get_draft(id: str)-> Optional[Message]**: Retrieves a draft by its ID.
###### Message Sending:
- **send_message(sender, to, subject, ...)-> Optional[Message]**: Sends an email message with various options (text, HTML, attachments, signature).
###### Inbox Management:
- **get_inbox_messages()-> GetMessagesResponse**: Retrieves messages from the inbox.
Similar methods exist for getting trash, spam, and all messages with various filtering options.
###### Drafts Management:
- **get_draft_messages()**: Retrieves draft messages.
###### Attachment Management:
- **get_attachment(message_id: str, attachment_id: str) -> Optional[MessagePartBody]**: Retrieves an attachment from a message.
###### Profile and Label Management:
- **labels**: Returns a list of user labels.
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
- **data (Optional[str])**: This optional attribute stores the Base64 encoded content of the attachment data downloaded from the API.

###### Methods:
- **download() -> None**: This method downloads the attachment data from the Gmail API if it hasn't been downloaded already. It raises exceptions for errors like missing message ID or HTTP errors during download.
- **save(filepath: Optional[str] = None, overwrite: bool = False) -> None**: This method saves the attachment data to a file. It allows specifying the filepath and whether to overwrite existing files. It raises an error if the file already exists and overwrite is set to False.

Overall, the Attachment class provides functionality to manage attachments associated with Gmail messages. It handles downloading attachments from the API, storing downloaded data, and saving them to local files.

---

### class GetMessagesResponse:
###### Attributes:
- **next_page_token (Optional[str], optional)**: Token for fetching the next page of results. Defaults to None.
- **existing_pages (Optional[str], optional)**: Used internally for pagination. Defaults to None. List like string of page tokens separated by GmailApi.SEPARATOR_SYMBOL
- **previous_page_token (Optional[List[str | None]], optional)**: Token for fetching the previous page of results (may be empty list). Defaults to [].
- **messages (List[Message])**: List of retrieved message objects.