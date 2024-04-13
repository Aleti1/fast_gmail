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