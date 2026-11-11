from googleapiclient.errors import HttpError

from fast_gmail.helpers import GoogleService
from fast_gmail.helpers import Labels
from fast_gmail.message import Attachment
from fast_gmail.message import Message


class Thread(object):
    """A Gmail conversation: the messages that share one threadId, oldest first.
    Attributes:
        id (str): Unique identifier of the thread.
        historyId (str | None): Id of the last history record that modified the thread.
        snippet (str | None): Short part of the thread text (only set by the list call).
        messages (list[Message]): Messages of the thread, oldest first.
    Properties:
        first_message / last_message (Message | None): Ends of the conversation.
        subject (str | None): Subject of the first message.
        message_count (int): Number of messages in the thread.
        is_unread (bool): True when at least one message is unread.
        has_attachments (bool): True when at least one message has attachments.
        attachments (list[Attachment]): Attachments of all messages.
        participants (list[str]): Distinct From headers, in order of appearance.
    Methods:
        mark_as_read() / mark_as_unread(): Change the UNREAD label of every message in the thread.
        modify_labels(labels_to_add, labels_to_remove): Change labels of every message in the thread.
        move_to_trash() / move_from_trash(): Trash / restore the whole thread.
    """  # noqa

    id: str
    historyId: str | None
    snippet: str | None
    messages: list[Message]

    def __init__(self, google_service: GoogleService, **kwargs):
        self.google_service = google_service
        self.id = kwargs.pop("id", None)
        self.historyId = kwargs.pop("historyId", None)
        self.snippet = kwargs.pop("snippet", None)
        self.messages = [
            Message(google_service=google_service, **message)
            for message in kwargs.pop("messages", None) or []
        ]

    def __str__(self):
        return self.subject or self.snippet or ""

    def __iter__(self):
        for message in self.messages:
            yield message

    def __len__(self):
        return len(self.messages)

    @property
    def first_message(self) -> Message | None:
        return self.messages[0] if self.messages else None

    @property
    def last_message(self) -> Message | None:
        return self.messages[-1] if self.messages else None

    @property
    def subject(self) -> str | None:
        return self.first_message.subject if self.messages else None

    @property
    def message_count(self) -> int:
        return len(self.messages)

    @property
    def is_unread(self) -> bool:
        return any(message.is_unread for message in self.messages)

    @property
    def has_attachments(self) -> bool:
        return any(message.has_attachments for message in self.messages)

    @property
    def attachments(self) -> list[Attachment]:
        return [
            attachment
            for message in self.messages
            for attachment in (message.attachments or [])
        ]

    @property
    def participants(self) -> list[str]:
        senders: list[str] = []
        for message in self.messages:
            sender = message.sender_header
            if sender and sender not in senders:
                senders.append(sender)
        return senders

    def mark_as_read(self) -> "Thread":
        self.modify_labels(labels_to_remove=[Labels.UNREAD.value])
        return self

    def mark_as_unread(self) -> "Thread":
        self.modify_labels(labels_to_add=[Labels.UNREAD.value])
        return self

    def move_to_trash(self) -> "Thread":
        self._call("trash")
        return self

    def move_from_trash(self) -> "Thread":
        self._call("untrash")
        return self

    def modify_labels(
        self,
        labels_to_add: list[Labels] | list[str] | None = None,
        labels_to_remove: list[Labels] | list[str] | None = None,
    ) -> bool:
        """Adds/removes labels on every message of the thread (one API call)."""
        add = [_label_id(label) for label in labels_to_add or []]
        remove = [_label_id(label) for label in labels_to_remove or []]
        self._call("modify", body={"addLabelIds": add, "removeLabelIds": remove})
        for message in self.messages:
            if message.labelIds is None:
                message.labelIds = []
            for label in add:
                if label not in message.labelIds:
                    message.labelIds.append(label)
            for label in remove:
                if label in message.labelIds:
                    message.labelIds.remove(label)
        return True

    def _call(self, method: str, **kwargs) -> dict:
        try:
            threads = self.google_service.service.users().threads()
            return getattr(threads, method)(
                userId=self.google_service.user_id, id=self.id, **kwargs
            ).execute()
        except HttpError as e:
            raise e
        finally:
            self.google_service.service.close()


def _label_id(label: Labels | str) -> str:
    return label.value if isinstance(label, Labels) else label
