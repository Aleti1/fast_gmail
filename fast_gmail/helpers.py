from typing import Optional
from typing import List
from typing import Union
from enum import Enum
from dataclasses import dataclass
from dataclasses import field

from googleapiclient.discovery import Resource
from googleapiclient.errors import HttpError


"""This are all colors accepted by google for custom labes"""
COLORS = (
	"#000000",
	"#434343",
	"#666666",
	"#999999",
	"#cccccc",
	"#efefef",
	"#f3f3f3",
	"#ffffff",
	"#fb4c2f",
	"#ffad47",
	"#fad165",
	"#16a766",
	"#43d692",
	"#4a86e8",
	"#a479e2",
	"#f691b3",
	"#f6c5be",
	"#ffe6c7",
	"#fef1d1",
	"#b9e4d0",
	"#c6f3de",
	"#c9daf8",
	"#e4d7f5",
	"#fcdee8",
	"#efa093",
	"#ffd6a2",
	"#fce8b3",
	"#89d3b2",
	"#a0eac9",
	"#a4c2f4",
	"#d0bcf1",
	"#fbc8d9",
	"#e66550",
	"#ffbc6b",
	"#fcda83",
	"#44b984",
	"#68dfa9",
	"#6d9eeb",
	"#b694e8",
	"#f7a7c0",
	"#cc3a21",
	"#eaa041",
	"#f2c960",
	"#149e60",
	"#3dc789",
	"#3c78d8",
	"#8e63ce",
	"#e07798",
	"#ac2b16",
	"#cf8933",
	"#d5ae49",
	"#0b804b",
	"#2a9c68",
	"#285bac",
	"#653e9b",
	"#b65775",
	"#822111",
	"#a46a21",
	"#aa8831",
	"#076239",
	"#1a764d",
	"#1c4587",
	"#41236d",
	"#83334c",
	"#464646",
	"#e7e7e7",
	"#0d3472",
	"#b6cff5",
	"#0d3b44",
	"#98d7e4",
	"#3d188e",
	"#e3d7ff",
	"#711a36",
	"#fbd3e0",
	"#8a1c0a",
	"#f2b2a8",
	"#7a2e0b",
	"#ffc8af",
	"#7a4706",
	"#ffdeb5",
	"#594c05",
	"#fbe983",
	"#684e07",
	"#fdedc1",
	"#0b4f30",
	"#b3efd3",
	"#04502e",
	"#a2dcc1",
	"#c2c2c2",
	"#4986e7",
	"#2da2bb",
	"#b99aff",
	"#994a64",
	"#f691b2",
	"#ff7537",
	"#ffad46",
	"#662e37",
	"#ebdbde",
	"#cca6ac",
	"#094228",
	"#42d692",
	"#16a765"
)
"""default date format returned by Message.date_string property"""
DATE_FORMAT = "%B %d, %Y %H:%M"
"""default number of messages"""
MAX_RESULTS = 10


class LabelAction(Enum):
	REMOVE = "remove"
	ADD = "add"
	TOGGLE = "toggle"


class ApplicationType(str, Enum):
	WEB = "web"
	INSTALLED = "installed"


class LabelMessageVisibility(str, Enum):
	SHOW = "show"
	HIDE = "hide"


class LabelListVisibility(str, Enum):
	LABEL_SHOW = "labelShow"
	LABEL_SHOW_IF_UNREAD = "labelShowIfUnread"
	LABEL_HIDE = "labelHide"


class LabelType(str, Enum):
	SYSTEM = "system"
	USER = "user"


class Labels(str, Enum):
	SPAM = "SPAM"
	SENT = "SENT"
	INBOX = "INBOX"
	DRAFT = "DRAFT"
	TRASH = "TRASH"
	UNREAD = "UNREAD"
	STARRED = "STARRED"
	IMPORTANT = "IMPORTANT"
	CATEGORY_FORUMS = "CATEGORY_FORUMS"
	CATEGORY_SOCIAL = "CATEGORY_SOCIAL"
	CATEGORY_UPDATES = "CATEGORY_UPDATES"
	CATEGORY_PERSONAL = "CATEGORY_PERSONAL"
	CATEGORY_PROMOTIONS = "CATEGORY_PROMOTIONS"

	
class AttachmentAction(Enum):
	IGNORE = "ignore"
	REFERENCE = "reference"
	DOWNLOAD = "download"
	

@dataclass
class BatchResponse(object):
	exception: Optional[HttpError] = None
	message: Union[Optional['Message'], Optional['Draft']] = None

@dataclass
class MessageIdentifiers(object):
	id: str
	threadId: str

@dataclass
class DraftIdentifiers(object):
	id: str
	message: MessageIdentifiers

@dataclass
class DraftsList(object):
	resultSizeEstimate: int
	nextPageToken: Optional[str]=None
	drafts: Optional[List[DraftIdentifiers]] = field(default_factory=lambda: [])

@dataclass
class MessagesList(object):
	resultSizeEstimate: int
	messages: Optional[List[MessageIdentifiers]] = field(default_factory=lambda : [])
	nextPageToken: Optional[str]=None

	def __init__(
		self, 
		resultSizeEstimate: int,
		messages: Optional[List[MessageIdentifiers]] = [],
		nextPageToken: Optional[str] = None
	):
		self.resultSizeEstimate = resultSizeEstimate
		self.nextPageToken = nextPageToken
		self.messages = [MessageIdentifiers(**x) for x in messages] if messages else []

@dataclass
class GmailLabelColor(object):
	textColor: str
	backgroundColor: str

@dataclass
class GmailProfile(object):
	emailAddress: str
	messagesTotal: int
	threadsTotal: int
	historyId: int

@dataclass
class GmailLabel(object):
	id: str
	name: str
	messagesTotal: Optional[int] = None
	messagesUnread: Optional[int] = None
	threadsTotal: Optional[int] = None
	threadsUnread: Optional[int] = None
	messageListVisibility: Optional[LabelMessageVisibility] = None
	labelListVisibility: Optional[LabelListVisibility] = None
	type: Optional[LabelType] = None
	color: Optional[GmailLabelColor] = None

	def __init__(self, **kwargs):
		self.id = kwargs.pop("id", None)
		self.name = kwargs.pop("name", None)
		self.messagesTotal = kwargs.pop("messagesTotal", None)
		self.messagesUnread = kwargs.pop("messagesUnread", None)
		self.threadsTotal = kwargs.pop("threadsTotal", None)
		self.threadsUnread = kwargs.pop("threadsUnread", None)

		message_visibility = kwargs.pop("messageListVisibility", None)
		if message_visibility:
			self.messageListVisibility = LabelMessageVisibility(message_visibility)
		list_visibility = kwargs.pop("labelListVisibility", None)
		if list_visibility:
			self.labelListVisibility = LabelListVisibility(list_visibility)
		label_type = kwargs.pop("type", None)
		if label_type:
			self.type = LabelType(label_type)
		colors = kwargs.pop("color", None)
		if colors:
			self.color = GmailLabelColor(**colors)

@dataclass
class GetMessagesResponse(object):
	"""Represents the response object containing retrieved messages and pagination information.
		Attributes:
			next_page_token (Optional[str], optional): Token for fetching the next page of results. Defaults to None.
			existing_pages (Optional[str], optional): Used internally for pagination. Defaults to None.
			previous_page_token (Optional[List[str | None]], optional): Token for fetching the previous page of results (may be empty list). Defaults to [].
			messages (List[Message]): List of retrieved message objects.

		This dataclass also provides list-like methods for iterating, checking membership, length, and accessing/modifying elements within the `messages` list.  
    """
	next_page_token: Optional[str] = None
	existing_pages: Optional[str] = None
	previous_page_token: Optional[List[str | None]] = field(default_factory = lambda: [])
	messages: List['Message'] = field(default_factory = lambda: [])

	def __iter__(self):
		for message in self.messages:
			yield message

	def __contains__(self, value):
		return value in self.messages

	def __len__(self):
		return len(self.messages)

	def __getitem__(self, idx):
		if isinstance(idx, 'Message'):
			return self.__class__(self.messages[idx])
		else:
			return self.messages[idx]

	def __setitem__(self, idx, value):
		self.messages[idx] = value

	def __delitem__(self, idx):
		del self.messages[idx]

	def count(self):
		return len(self.messages)
	
	def index(self, idx, *args):
		return self.messages.index(idx, *args)
	
	def append(self, value):
		self.messages.append(value)

	def insert(self, idx, value):
		self.messages.insert(idx, value)

	def pop(self, idx=-1):
		return self.messages.pop(idx)

	def remove(self, value):
		self.messages.remove(value)

	def clear(self):
		self.messages.clear()
		

class GoogleService(object):
	service: Resource
	user_id: str
	message_id: Optional[str]

	def __init__(
        self,
		service: Resource,
		user_id: str,
		message_id: Optional[str]=None
    ):
		self.service = service
		self.user_id = user_id
		self.message_id = message_id

	def set_message_id(self, id: str):
		self.messsage_id = id


class InvalidToken(Exception):
	...

