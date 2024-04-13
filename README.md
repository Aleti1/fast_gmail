# Fast-gmail a simple python wrapper for gmailapi

[![PyPI Downloads](https://img.shields.io/pypi/dm/fast-gmail.svg?label=PyPI%20downloads)](
https://pypi.org/project/fast-gmail/)

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

## Usage:

### Get messages
```
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

### Get INBOX messages
```
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

### Send message
``` 
    messages = GmailApi().send_message(
        sender: str,
        to: str,
        subject: str,
        html: Optional[str]=None,
        text: Optional[str]=None,
        cc: Optional[List[str] | str]=None,
        bcc: Optional[List[str] | str]=None,
        attachments: Optional[List[str] | str]=None,
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
            signature (bool, optional): Whether to include a signature (if configured). Defaults to True.
        Returns:
            Optional[Message]: An object representing the sent message, or None on error.
    """
```

## Classes:

### Message
###### Properties:
- id: Unique identifier for the message.
- snippet: Shortened summary of the message content.
- threadId: Thread ID that groups related messages together.
- historyId: Unique identifier for a specific message history change.
- sizeEstimate: Approximate size of the message in bytes.
- internalDate: Internal timestamp representing when the message was created.
- payload: Object of type MessagePart containing the parsed content of the message body and attachments.
- raw: Optional property containing the raw email data (if available).
- labelIds: List of label IDs associated with the message.
- labels: List of GmailLabel objects representing the message's labels (fetched on demand).

###### Additional Message Properties:
- message_headers: Returns a list of MessageHeader objects from the message's payload (if available).
- body: Returns the message body content (combines plain text and HTML if both exist).
- html: Returns the HTML content of the message body (if available).
- plain: Returns the plain text content of the message body (if available).
- alternative: Returns the text content of the most appropriate alternative part (if message uses multipart/alternative).
- recipient: Extracts the recipient's email address from the "To" header (if available).
- message_id: Extracts the message ID from the message headers (if available).
- subject: Extracts the subject line from the message headers (if available).
- sender: Extracts the sender's email address from the "From" header (if available).
- has_attachments: Checks if the message or its nested parts contain attachments.
- attachments: Returns a list of Attachment objects for all attachments within the message.
- is_unread, is_starred, is_important, etc.: Boolean properties indicating the message's label status (unread, starred, important, spam, draft, trash).
- created_date: Converts the internalDate to a datetime object representing the message creation time.
- date: Parses the "Received" or "Date" header to get the message delivery date (if available).
- date_string: Formats the delivery date according to a specified format string (defaults to "%a, %d %b %Y %H:%M:%S %z").

###### Message Actions:
- mark_as_read, mark_as_unread: Toggles the unread flag for the message.
- toogle_read_unread: Shortcut to toggle the unread flag based on the current state.
- mark_spam, mark_not_spam: Toggles the spam label for the message.
- toggle_spam: Shortcut to toggle the spam label based on the current state.
- move_to_trash, move_from_trash: Toggles the trash label for the message.
- toggle_trash: Shortcut to toggle the trash label based on the current state.
- mark_important, mark_not_important: Toggles the important label for the message.
- toggle_important: Shortcut to toggle the important label based on the current state.
- mark_starred, mark_not_starred: Toggles the starred label for the message.
- toggle_starred: Shortcut to toggle the starred label based on the current state.
- get_attachment(filename=None, id=None): Retrieves an attachment by filename or internal part ID.
- get_labels: Fetches and returns a list of GmailLabel objects for all labels associated with the message.
- add_label(label), add_labels(labels): Adds labels to the message.
- remove_label(label), remove_labels(labels): Removes labels from the message.
- modify_labels(label_to_add=None, labels_to_remove=None): Updates message labels by adding and/or removing labels.

Overall, this Message class provides a comprehensive way to access and manage individual email messages within a Gmail account. It allows you to retrieve message details, content, attachments, labels, and perform various actions like marking as read/unread, starring, labeling, and trash management.