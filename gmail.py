from typing import Optional, Union, List, Self
from dataclasses import dataclass, field
from datetime import datetime as dt
from enum import Enum, StrEnum
from datetime import timezone
import mimetypes
import base64
import os

from email.message import EmailMessage
from email.header import Header
from email import utils

from swgapp.oauth_helper import Creds

from googleapiclient.discovery import build, Resource
from google.oauth2.credentials import Credentials
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

@dataclass
class GmailLabelColor(object):
	textColor: str
	backgroundColor: str

@dataclass
class GmailLabel(object):
	id: str
	name: str
	messagesTotal: Optional[int] = None
	messagesUnread: Optional[int] = None
	threadsTotal: Optional[int] = None
	threadsUnread: Optional[int] = None
	messageListVisibility: Optional['LabelMessageVisibility'] = None
	labelListVisibility: Optional['LabelListVisibility'] = None
	type: Optional['LabelType'] = None
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
class MessageHeader(object):
	name: str
	value: str

@dataclass
class MessagePartBody(object):
	size: int
	attachmentId: Optional[str] = None
	data: Optional[str] = None

@dataclass
class BatchResponse(object):
	exception: Optional[HttpError] = None
	message: Union[Optional['Message'], Optional['Draft']] = None

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
class SearchParams(object):
	"""https://support.google.com/mail/answer/7190"""
	message_id: Optional[str] = None
	from_sender: Optional[str] = None
	recipient: Optional[str] = None
	label: Optional[str] = None
	subject: Optional[str] = None
	unread: Optional[bool] = False
	read: Optional[bool] = False
	snoozed: Optional[bool] = False
	starred: Optional[bool] = False
	search_only_with_attachments: Optional[bool] = False
	filename: Optional[str] = None
	ignore_words: Optional[list] = None
	date_after: Optional[str] = None
	date_before: Optional[str] = None
	older_than_date: Optional[str] = None
	newer_than_date: Optional[str] = None
	older_than: Optional[str] = None
	newer_than: Optional[str] = None
	important: Optional[bool] = False
	include_spam_trash: Optional[bool] = False
	google_drive: Optional[bool] = False
	google_docs: Optional[bool] = False
	google_sheet: Optional[bool] = False
	attachment_name: Optional[str] = None
	has_youtube_video: Optional[bool] = False
	google_presentation: Optional[bool] = False
	all_folders: Optional[bool] = False
	exact_match: Optional[bool] = False
	search_query: Optional[str] = None

	@property
	def query(self):
		search_queries: List[str] = []
		if self.message_id:
			search_queries.append(f"rfc822msgid:{self.message_id}")
		if self.from_sender:
			search_queries.append(f"from:{self.from_sender}")
		if self.recipient:
			search_queries.append(f"to:{self.recipient} cc:{self.recipient} bcc:{self.recipient}")
		if self.label:
			search_queries.append(f"label:{self.label}")
		if self.subject:
			search_queries.append(f"subject:{self.subject}")
		if self.unread:
			search_queries.append(f"is:unread")
		if self.read:
			search_queries.append(f"is:read")
		if self.snoozed:
			search_queries.append(f"is:snoozed")
		if self.starred:
			search_queries.append(f"is:starred")
		if self.search_only_with_attachments:
			search_queries.append("has:attachment")
		if self.filename:
			search_queries.append(f"filename:{self.filename}")
		if self.ignore_words:
			for word in self.ignore_words:
				search_queries.append(f"-{word}")
		if self.date_after:
			"""can be Y/m/d | d/m/Y | int(seconds from epoch)"""
			search_queries.append(f"after:{self.date_after}")
		if self.date_before:
			"""can be Y/m/d | d/m/Y | int(seconds from epoch)"""
			search_queries.append(f"before:{self.date_before}")
		if self.older_than_date:
			search_queries.append(f"older:{self.older_than_date}")
		if self.newer_than_date:
			search_queries.append(f"newer:{self.newer_than_date}")
		if self.older_than:
			search_queries.append(f"older_than:{self.older_than}")
		if self.newer_than:
			search_queries.append(f"newer_than:{self.newer_than}")
		if self.important:
			search_queries.append("is:important")
		if self.include_spam_trash:
			"""same as all_folders field"""
			search_queries.append("in:anywhere")
		if self.google_drive:
			search_queries.append("has:drive")
		if self.google_docs:
			search_queries.append("has:document")
		if self.google_sheet:
			search_queries.append("has:spreadsheet")
		if self.attachment_name:
			search_queries.append(f"filename:{self.attachment_name}")
		if self.has_youtube_video:
			search_queries.append("has:youtube")
		if self.google_presentation:
			search_queries.append("has:presentation")
		if self.all_folders:
			search_queries.append("in:anywhere")
		exact_match_symbol = "+" if self.exact_match else ""
		return f"""{" ".join(search_queries)}{exact_match_symbol}{self.search_query if self.search_query else ""}"""

class LabelMessageVisibility(StrEnum):
	SHOW = "show"
	HIDE = "hide"

class LabelListVisibility(StrEnum):
	LABEL_SHOW = "labelShow"
	LABEL_SHOW_IF_UNREAD = "labelShowIfUnread"
	LABEL_HIDE = "labelHide"

class LabelType(StrEnum):
	SYSTEM = "system"
	USER = "user"

class Labels(StrEnum):
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

class GoogleService(object):
	service: Resource
	user_id: str
	message_id: Optional[str]

	def __init__(self, service: Resource, user_id: str, message_id: Optional[str]=None):
		self.service = service
		self.user_id = user_id
		self.message_id = message_id

	def set_message_id(self, id: str):
		self.messsage_id = id

class Attachment(object):
	filename: str
	mimeType: str
	google_service: GoogleService
	id: Optional[str] = None
	data: Optional[str] = None

	def __init__(
		self,
		filename: str,
		mimeType: str,
		google_service: GoogleService,
		id: Optional[str]=None,
		data: Optional[str]=None
	):
		self.filename = filename
		self.mimeType = mimeType
		self.google_service = google_service
		self.id = id
		self.data = data

	def download(self)-> None:
		if not self.id:
			return None
		if self.data:
			return None
		if not self.google_service.message_id:
			raise TypeError("Attachment.google_service.message_id missing")
		res: Optional[MessagePartBody] = self.google_service.service.users().messages().attachments().get(
            userId=self.google_service.user_id,
			messageId=self.google_service.message_id,
			id=self.id
        ).execute()
		if not res or "data" not in res:
			return None
		self.data = base64.urlsafe_b64decode(res["data"])
	
	def save(self, filepath: Optional[str]=None, overwrite: bool=False)-> None:
		if not filepath:
			filepath = self.filename
		if not self.data:
			self.download()
		if os.path.exists(filepath) and not overwrite:
			raise FileExistsError(
				f"""\
					{filepath} allready exists. \
					Call save(file_path, overwrite=True) \
					to rewrite the existing file\
				"""
			)
		with open(filepath, "wb") as f:
			f.write(self.data)

	def __str__(self):
		return self.filename

class MessagePart(object):
	mimeType: Optional[str]
	headers: List[MessageHeader] = field(default_factory=lambda : [])
	parts: List[Self] = field(default_factory=lambda : [])
	partId: Optional[str] = None
	filename: Optional[str] = None
	body: Optional[MessagePartBody] = None

	def __init__(self, google_service: GoogleService, **kwargs):
		self.google_service = google_service
		self.mimeType = kwargs.pop("mimeType", None)
		self.filename = kwargs.pop("filename", None)
		self.partId = kwargs.pop("partId", None)
		self.headers = [MessageHeader(**hdr) for hdr in kwargs.pop("headers", None)] if "headers" in kwargs else []
		self.body = MessagePartBody(**kwargs.pop("body", None)) if "body" in kwargs else None
		self.parts = [MessagePart(google_service=self.google_service, **part) for part in kwargs.pop("parts", None)] if "parts" in kwargs else []

	def _has_attachments(self)-> bool:
		if self.filename:
			return True
		if not self.parts:
			return False
		for part in self.parts:
			if part.filename:
				return True
		return False
	
	def get_attachment_by_filename(self, filename: str)-> Union[Attachment, None]:
		if not filename or len(filename) == 0:
			return None
		if not self._has_attachments():
			return None
		for attachment in self.attachments:
			if attachment.filename == filename:
				return attachment
		return None

	@property
	def attachments(self)-> Optional[List[Attachment]]:
		if not self._has_attachments():
			return []
		attachments = []
		for part in self.parts:
			if part.filename:
				if part.body.attachmentId:
					attachments.append(Attachment(
						filename=part.filename,
						mimeType=part.mimeType if part.mimeType else "",
						id = part.body.attachmentId,
						google_service=self.google_service
					))
				else:
					attachments.append(Attachment(
						filename=part.filename,
						mimeType=part.mimeType if part.mimeType else "",
						data = part.body.data,
						google_service=self.google_service
					))
		return attachments

	def get_header(self, key: str)-> Optional[MessageHeader]:
		if not self.headers or len(self.headers) == 0:
			return None
		if not key:
			return self.headers
		for header in self.headers:
			if key == header.name:
				return header
		return None
	
class Message(object):
	id: str
	snippet: str
	threadId: str
	historyId: str
	sizeEstimate: int
	internalDate: str
	payload: MessagePart
	raw: Optional[str] = None
	labelIds: List[Labels] = field(default_factory=lambda : [])
	labels: Optional[List[GmailLabel]] = None

	def __init__(self, google_service: GoogleService, *args, **kwargs):
		self.id = kwargs.pop("id", None)
		self.threadId = kwargs.pop("threadId", None)
		self.snippet = kwargs.pop("snippet", None)
		self.historyId = kwargs.pop("historyId", None)
		self.internalDate = kwargs.pop("internalDate", None)
		self.sizeEstimate = kwargs.pop("sizeEstimate", None)
		self.raw = kwargs.pop("raw", None)
		self.labelIds = kwargs.pop("labelIds", None)
		self.google_service = google_service
		if "payload" in kwargs:
			self.payload = MessagePart(google_service=self.google_service, **kwargs["payload"])

	def __str__(self):
		return self.subject if self.subject else (self.snippet if self.snippet else "")

	@property
	def message_headers(self)-> Optional[List[MessageHeader]]:
		if not self.payload:
			return None
		if not self.payload.headers:
			return None
		return self.payload.headers

	@property
	def recipient(self)-> Union[str, None]:
		if not self.message_headers:
			return None
		for header in self.message_headers:
			if header.name == "To":
				return header.value
		return None

	@property
	def message_id(self)-> Union[str, None]:
		if not self.message_headers:
			return None
		for header in self.message_headers:
			if header.name == "Message-ID":
				return header.value
			if header.name == "Message-Id":
				return header.value
		return None

	@property
	def subject(self)-> Union[str, None]:
		if not self.message_headers:
			return None
		for header in self.message_headers:
			if header.name == "Subject":
				return header.value
		return None

	@property
	def sender(self)-> Union[str, None]:
		if not self.message_headers:
			return None
		for header in self.message_headers:
			if header.name == "From":
				return header.value
		return None
	
	@property
	def has_attachments(self)-> bool:
		if not self.payload: return False
		return self.payload._has_attachments()

	@property
	def attachments(self)-> Optional[List[Attachment]]:
		return self.payload.attachments

	@property
	def is_unread(self)-> bool:
		if not self.labelIds:
			return False
		if Labels.UNREAD.value in [x for x in self.labelIds]:
			return True
		return False
	
	@property
	def is_starred(self)-> bool:
		if not self.labelIds:
			return False
		if Labels.STARRED.value in [x for x in self.labelIds]:
			return True
		return False
	
	@property
	def is_important(self)-> bool:
		if not self.labelIds:
			return False
		if Labels.IMPORTANT.value in [x for x in self.labelIds]:
			return True
		return False

	@property
	def is_spam(self)-> bool:
		if not self.labelIds:
			return False
		if Labels.SPAM.value in [x for x in self.labelIds]:
			return True
		return False

	@property
	def is_draft(self)-> bool:
		if not self.labelIds:
			return False
		if Labels.DRAFT.value in [x for x in self.labelIds]:
			return True
		return False

	@property
	def is_trash(self)-> bool:
		if not self.labelIds:
			return False
		if Labels.TRASH.value in [x for x in self.labelIds]:
			return True
		return False

	@property
	def created_date(self)-> dt:
		"""internalDate is the time when messages was created"""
		seconds_from_epoch: int
		try:
			seconds_from_epoch = int(self.internalDate)/1000
		except ValueError:
			raise ValueError(f"{self.internalDate=} can't be cast to int")
		return dt.fromtimestamp(seconds_from_epoch)

	@property
	def date(self)-> Optional[dt]:
		"""returns the date when message was delivered"""
		received = self.payload.get_header("Received")
		split_to_extract: bool = True
		if not received:
			split_to_extract = False
			received = self.payload.get_header("Date")
		if not received:
			return None
		
		date_part: str = received.value
		if split_to_extract:
			_, date_part = received.value.split("; ")
			if not date_part:
				return None
			if "(" in date_part:
				date_part, _ = date_part.split("(")
				if not date_part:
					return None
			date_part = date_part.strip()

		return dt.strptime(date_part, f"%a, %d %b %Y %H:%M:%S %z")
		
	def date_string(self, format: Optional[str] = DATE_FORMAT)-> Optional[str]:
		"""returns fomated delivered date, cheatsheet: https://strftime.org/"""
		if not self.date:
			print(self.__dict__,"\n", self.payload.__dict__)
			return None
		date = self.date.astimezone() # set to locale timezone
		if date.year == dt.now(timezone.utc).astimezone().year:
			format = format.replace(", %Y", "")
		return date.strftime(format)

	@property
	def mark_as_read(self)-> Self:
		self.remove_label(Labels.UNREAD.value)
		return self
	
	@property
	def mark_as_unread(self)-> Self:
		self.add_label(Labels.UNREAD.value)
		return self

	@property
	def toogle_read_unread(self)-> Self:
		if self.is_unread:
			self.remove_label(Labels.UNREAD.value)
		else:
			self.add_label(Labels.UNREAD.value)
		return self

	@property
	def mark_spam(self)-> Self:
		self._edit_labels(
			action="add_remove",
			add=[Labels.SPAM.value],
			remove=[
				Labels.TRASH.value,
				Labels.INBOX.value,
				Labels.STARRED.value,
				Labels.IMPORTANT.value,
			]
		)
		return self
	
	@property
	def mark_not_spam(self)-> Self:
		self._edit_labels(
			label_to_add=[Labels.INBOX.value],
			labels_to_remove=[Labels.SPAM.value]
		)
		return self

	@property
	def toggle_spam(self)-> Self:
		if self.is_spam:
			self.mark_not_spam
		else:
			self.mark_spam
		return self

	@property
	def move_to_trash(self)-> Self:
		self._edit_labels(
			action="add_remove",
			add=[Labels.TRASH.value],
			remove=[
				Labels.INBOX.value,
				Labels.STARRED.value,
				Labels.IMPORTANT.value,
			]
		)
		return self

	@property
	def move_from_trash(self)-> Self:
		self._edit_labels(
			label_to_add=[Labels.INBOX.value],
			labels_to_remove=[Labels.TRASH.value]
		)
		return self

	@property
	def toggle_trash(self)-> Self:
		if self.is_trash:
			self.move_from_trash
		else:
			self.move_to_trash
		return self

	@property
	def mark_important(self)-> Self:
		self.add_label(Labels.IMPORTANT.value)
		return self
	
	@property
	def mark_not_important(self)-> Self:
		self.remove_label(Labels.IMPORTANT.value)
		return self

	@property
	def toggle_important(self)-> Self:
		if self.is_important:
			return self.mark_not_important
		return self.mark_important

	@property
	def mark_starred(self)-> Self:
		self.add_label(Labels.STARRED.value)
		return self
	
	@property
	def mark_not_starred(self)-> Self:
		self.remove_label(Labels.STARRED.value)
		return self

	@property
	def toggle_starred(self)-> Self:
		if self.is_starred:
			return self.mark_not_starred
		return self.mark_starred

	def get_attachment(self, filename: str)-> Union[Attachment, None]:
		if not filename or len(filename) == 0:
			return None
		if not self.has_attachments:
			return None
		return self.payload.get_attachment_by_filename(filename)

	@property
	def get_labels(self)-> Optional[List[GmailLabel]]:
		"""gets all labels for this message"""
		if not self.labels:
			self.labels = []
		batch = self.google_service.service.new_batch_http_request()
		def get_label_response(request_id, response, exception):
			if exception is not None:
				raise exception
			self.labels.append(GmailLabel(**response))
			return
		for label_id in self.labelIds:
			batch.add(
				self.google_service.service.users().labels().get(
					userId = self.google_service.user_id,
					id = label_id
				),
				callback=get_label_response
			)
		batch.execute()
		return self.labels

	def add_label(self, label: Union[Labels, str])-> bool:
		return self._edit_labels(action="add", add=[label])
	def add_labels(self, labels: Union[List[Labels], List[str]])-> bool:
		return self._edit_labels(action="add", add=labels)
	def remove_label(self, label: Union[Labels, str])-> bool:
		return self._edit_labels(action="remove", remove=[label])
	def remove_labels(self, labels: Union[List[Labels], List[str]])-> bool:
		return self._edit_labels(action="remove", remove=labels)
	def modify_labels(
		self,
		label_to_add: Optional[Union[List[Labels], List[str]]],
		labels_to_remove: Optional[Union[List[Labels], List[str]]]
	)-> bool:
		return self._edit_labels(
			action="add_remove",
			add=label_to_add,
			remove=labels_to_remove
		)

	def _edit_labels(self, action: str, add: Optional[List[Labels]]=[], remove: Optional[List[Labels]]=[])-> bool:
		payload = {}
		match action:
			case "remove":
				payload["removeLabelIds"] = [x for x in remove]
			case "add":
				payload["addLabelIds"] = [x for x in add]
			case "add_remove":
				payload["removeLabelIds"] = [x for x in remove]
				payload["addLabelIds"] = [x for x in add]
			case _:
				return False
		try:
			self.google_service.service.users().messages().modify(
				userId=self.google_service.user_id,
				id=self.id,
				body=payload
			).execute()
			match action:
				case "add":
					for label in add:
						if label not in self.labelIds:
							self.labelIds.append(label)
				case "remove":
					for label in remove:
						if label in self.labelIds:
							self.labelIds.remove(label)
				case "add_remove":
					for label in add:
						if label not in self.labelIds:
							self.labelIds.append(label)
					for label in remove:
						if label in self.labelIds:
							self.labelIds.remove(label)
				case _:
					return False
			return True
		except HttpError as e:
			raise e
		finally:
			self.google_service.service.close()

class Draft(object):
	id: str
	message: Message
	google_service: Resource

	def __init__(self, id: str, google_service: Resource, message: dict):
		self.id = id
		self.google_service = google_service
		self.message = Message(google_service=google_service, **message)

@dataclass
class GmailProfile(object):
	emailAddress: str
	messagesTotal: int
	threadsTotal: int
	historyId: int

class Thread(Message):
	...

class InvalidToken(Exception):
	...

@dataclass
class GetMessagesResponse(object):
	next_page_token: Optional[str] = None
	existing_pages: Optional[str] = None
	previous_page_token: Optional[List[str | None]] = field(default_factory=lambda: [])
	messages: List[Message] = field(default_factory=lambda: [])

	def __iter__(self):
		for message in self.messages:
			yield message

	def __contains__(self, value):
		return value in self.messages

	def __len__(self):
		return len(self.messages)

	def __getitem__(self, idx):
		if isinstance(idx, Message):
			return self.__class__(self.messages[idx])
		else:
			return self.messages[idx]

	def __setitem__(self, idx, value):
		self.messages[idx] = value

	def __delitem__(self, idx):
		del self.messages[idx]
		
	def count(self):
		return self.totalResults
	
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
		
class GmailApi(object):
	"""https://googleapis.github.io/google-api-python-client/docs/dyn/gmail_v1.users.html"""
	credentials: Optional[Credentials] = None
	google_service: GoogleService
	max_results: int = MAX_RESULTS
	SEPARATOR_SYMBOL: str
	profile_data: Optional[GmailProfile] = None

	def __init__(
		self,
		token: str,
		separator_symbol: Optional[str] = ", ", # used for pagination on get_messages/drafts
		user_id: Optional[str] = "me"
	)-> None:
		self.SEPARATOR_SYMBOL = separator_symbol
		if not token:
			raise InvalidToken(f"Gmail user Token missing")
		self.credentials = Creds(
			json_creds = token
		).get_credentials()
		try:
			# Call the Gmail API and set the instance 
			self.google_service = GoogleService(
				service = build("gmail", "v1", credentials = self.credentials),
				user_id = user_id
			)
		except HttpError as e:
			raise e

	def get_message(self, id: str)-> Union[Message, None]:
		if not self.google_service:
			return None
		return Message(
			google_service=GoogleService(
				service=self.google_service.service,
				user_id=self.google_service.user_id,
				message_id=id
			),
			**self.google_service.service.users().messages().get(
				userId=self.google_service.user_id,
				id=id
			).execute()
		)
	
	def get_draft(self, id: str)-> Union[Message, None]:
		if not self.google_service:
			return None
		return Message(
			google_service=GoogleService(
				service=self.google_service.service,
				user_id=self.google_service.user_id,
				message_id=id
			),
			**self.google_service.service.users().drafts().get(
				userId=self.google_service.user_id,
				id=id
			).execute()
		)
	
	def send_message(
		self,
		sender: str,
		to: str,
		subject: str,
		html: Optional[str]=None,
		text: Optional[str]=None,
		cc: Optional[List[str] | str]=None,
		bcc: Optional[List[str] | str]=None,
		attachments: Optional[List[str] | str]=None,
		signature: bool = False
	)-> Optional[Message]:
		msg = EmailMessage()
		msg["To"] = to
		msg["From"] = str(Header(f"{sender} <{sender}>"))
		msg["Subject"] = subject
		msg["Date"] = utils.formatdate(localtime=1)
		msg["Cc"] = ", ".join(cc) if cc else ""
		msg["Bcc"] = ", ".join(bcc) if bcc else ""
		if signature and html:
			account_signature = self._alias_info(sender)
			html = f"{html}<br/><br/>{account_signature['signature'] if 'signature' in account_signature else ''}"
		if text:
			msg.set_content(text.strip())
		if html:
			msg.add_alternative(html.strip(), subtype = "html")

		if attachments:
			for attachment in attachments:
				type_subtype, _ = mimetypes.guess_type(attachment)
				maintype, subtype = type_subtype.split("/")
				with open(attachment, "rb") as fp:
					attachment_data = fp.read()
					msg.add_attachment(
						attachment_data,
						maintype = maintype,
						subtype = subtype,
						filename = os.path.basename(attachment)
					)
		try:
			encoded_message = base64.urlsafe_b64encode(msg.as_bytes()).decode()
			send_msg = (
				self.google_service.service.users().
				messages().
				send(
					userId = self.google_service.user_id,
					body = {"raw": encoded_message}
				).execute()
			)
		except HttpError as e:
			raise e
		return send_msg

	def get_inbox_messages(
		self,
		max_results: int = MAX_RESULTS,
		next_page_token: str = None,
		existing_pages: Optional[List[str] | str] = None,
		previous_page_token: Optional[str] = None,
		query: Union[SearchParams, str] = None
	)-> GetMessagesResponse:
		return self._get_messages(
			max_results = max_results,
			labels = [Labels.INBOX.value],
			next_page_token = next_page_token,
			existing_pages=existing_pages,
			previous_page_token = previous_page_token,
			query=query.query if isinstance(query, SearchParams) else query
		)

	def get_trash_messages(
		self,
		max_results: int = MAX_RESULTS,
		next_page_token: str = None,
		existing_pages: Optional[List[str] | str] = None,
		previous_page_token: Optional[str] = None,
		query: Union[SearchParams, str] = None
	)-> GetMessagesResponse:
		return self._get_messages(
			max_results = max_results,
			labels = [Labels.TRASH.value],
			next_page_token = next_page_token,
			existing_pages=existing_pages,
			previous_page_token = previous_page_token,
			query=query.query if isinstance(query, SearchParams) else query
		)
	
	def get_spam_messages(
		self,
		max_results: int = MAX_RESULTS,
		next_page_token: str = None,
		existing_pages: Optional[List[str] | str] = None,
		previous_page_token: Optional[str] = None,
		query: Union[SearchParams, str] = None
	)-> GetMessagesResponse:
		return self._get_messages(
			max_results = max_results,
			labels = [Labels.SPAM.value],
			next_page_token = next_page_token,
			existing_pages=existing_pages,
			previous_page_token = previous_page_token,
			query=query.query if isinstance(query, SearchParams) else query
		)
	
	def get_messages(
		self,
		includeSpamTrash: bool = False,
		max_results: int = MAX_RESULTS,
		labels: Union[List[Labels], List[str], None]=None,
		next_page_token: str = None,
		existing_pages: Optional[List[str] | str] = None,
		previous_page_token: Optional[str] = None,
		query: Union[SearchParams, str] = None,
	)-> GetMessagesResponse:
		return self._get_messages(
			includeSpamTrash = includeSpamTrash,
			max_results = max_results,
			labels = labels,
			next_page_token = next_page_token,
			existing_pages=existing_pages,
			previous_page_token = previous_page_token,
			query=query.query if isinstance(query, SearchParams) else query
		)

	def get_draft_messages(
		self,
		includeSpamTrash: bool = False,
		max_results: int = MAX_RESULTS,
		labels: Union[List[Labels], List[str], None]=None,
		next_page_token: str = None,
		existing_pages: Optional[List[str] | str] = None,
		previous_page_token: Optional[str] = None,
		query: Union[SearchParams, str] = None,
	)-> Union[List[Draft], list]:
		return self._get_drafts(
			includeSpamTrash = includeSpamTrash,
			max_results = max_results,
			labels = labels,
			next_page_token = next_page_token,
			existing_pages=existing_pages,
			previous_page_token = previous_page_token,
			query=query.query if isinstance(query, SearchParams) else query
		)

	@property
	def labels(self)-> Optional[List[GmailLabel]]:
		try:
			results = self.google_service.service.users().labels().list(
				userId=self.google_service.user_id
			).execute()
		except HttpError as e:
			raise e
		finally:
			self.google_service.service.close()
		return [GmailLabel(**label) for label in results.get("labels", [])]
	
	@property
	def profile(self)-> Optional[GmailProfile]:
		if self.profile_data:
			return self.profile_data
		try:
			request = self.google_service.service.users().getProfile(
				userId=self.google_service.user_id
			).execute()
			self.profile_data = GmailProfile(**request)
		except HttpError as e:
			raise e
		finally:
			self.google_service.service.close()
		return self.profile_data

	def _alias_info(self, email_address: str)-> dict:
		try:
			return self.google_service.service.users().settings().sendAs().get(
				sendAsEmail = email_address,
				userId = self.google_service.user_id
			).execute()
		except HttpError as e:
			raise e
		finally:
			self.google_service.service.close()

	def _get_messages(
		self,
		max_results: int,
		includeSpamTrash: bool = False,
		labels: Optional[List[Labels]] = None,
		next_page_token: str = None,
		existing_pages: Optional[List[str] | str] = None,
		previous_page_token: Optional[str] = None,
		query: str = None
	)-> GetMessagesResponse:
		
		# set existing page tokens holder
		existing_pages: Optional[List[str]] = existing_pages or []
		if isinstance(existing_pages, str):
			existing_pages = existing_pages.split(self.SEPARATOR_SYMBOL)
		# check if we need get previous messages
		if previous_page_token:
			# check if previous token exists
			if previous_page_token not in existing_pages:
				raise InvalidToken(f"{previous_page_token=} not found in {existing_pages=}")
			# get previous token index from existing pages 
			previous_index: int =  existing_pages.index(previous_page_token)
			# remove old token
			existing_pages = existing_pages[:previous_index]
			# set mew request token with the correct value
			next_page_token = existing_pages[-1] if len(existing_pages) > 0 else None

		# get message ids
		messages_response: MessagesList = self._get_messages_ids(
			includeSpamTrash=includeSpamTrash,
			max_results = max_results,
			next_page_token=next_page_token,
			labels=labels,
			query=query
		)

		# set results holder
		results: List[BatchResponse] = []

		try:
			# create batch request
			batch = self.google_service.service.new_batch_http_request()
			# callback for batch response
			def on_get_messages_callback(request_id, response, exception)-> None:
				if exception:
					results.append(BatchResponse(exception=exception))
					return
				results.append(BatchResponse(
					message = Message(
						google_service = self.google_service,
						**response
					)
				))
			# add request to batch
			for index in range(0, len(messages_response.messages)):
				batch.add(
					self.google_service.service.users().messages().get(
						userId = self.google_service.user_id,
						id = messages_response.messages[index].id
					),
					callback = on_get_messages_callback
				)
			# execute http batch request
			batch.execute()
		except HttpError as e:
			raise e
		finally:
			# close http connection
			self.google_service.service.close()
		
		if next_page_token and next_page_token not in existing_pages:
			existing_pages.append(next_page_token)
		for idx, item in enumerate(results):
			if idx == 3:
				print(item.message.labelIds, item.message.subject)
		# TODO: group messages by threads???
		return GetMessagesResponse(
			previous_page_token = existing_pages[-1] if existing_pages else next_page_token,
			existing_pages = self.SEPARATOR_SYMBOL.join(existing_pages) if existing_pages else None,
			next_page_token = messages_response.nextPageToken,
			messages = [x.message for x in results if x.message]
		)

	def _get_drafts(
		self,
		max_results: int,
		includeSpamTrash: bool = False,
		next_page_token: str = None,
		existing_pages: Optional[List[str] | str] = None,
		previous_page_token: Optional[str] = None,
		query: str = None
	)-> GetMessagesResponse:
		
		# set existing page tokens holder
		existing_pages: Optional[List[str]] = existing_pages or []
		if isinstance(existing_pages, str):
			existing_pages = existing_pages.split(self.SEPARATOR_SYMBOL)
		# check if we need get previous messages
		if previous_page_token:
			# check if previous token exists
			if previous_page_token not in existing_pages:
				raise InvalidToken(f"{previous_page_token=} not found in {existing_pages=}")
			# get previous token index from existing pages 
			previous_index: int =  existing_pages.index(previous_page_token)
			# remove old token
			existing_pages = existing_pages[:previous_index]
			# set mew request token with the correct value
			next_page_token = existing_pages[-1] if len(existing_pages) > 0 else None

		messages_response: DraftsList = self._get_drafts_ids(
			max_results=max_results,
			includeSpamTrash=includeSpamTrash,
			next_page_token=next_page_token,
			query=query
		)

		results: List[Draft] = []
		try:
			def on_get_draft_callback(request_id, response, exception)-> None:
				if exception:
					results.append(BatchResponse(exception=exception))
					return
				results.append(BatchResponse(
					message=Draft(
						id=response.get("id"),
						google_service=self.google_service,
						message=response.get("message")
					)
				))

			batch = self.google_service.service.new_batch_http_request()

			for index in range(0, len(messages_response.drafts)):
				draft_id = DraftIdentifiers(
					id=messages_response.drafts[index]["id"],
					message=MessageIdentifiers(**messages_response.drafts[index]["message"])
				)
				batch.add(
					self.google_service.service.users().drafts().get(
						userId=self.google_service.user_id,
						id=draft_id.id
					),
					callback=on_get_draft_callback
				)
			batch.execute()
		except HttpError as e:
			raise e
		finally:
			# close http connection
			self.google_service.service.close()
		
		if next_page_token and next_page_token not in existing_pages:
			existing_pages.append(next_page_token)

		return GetMessagesResponse(
			previous_page_tokens = next_page_token,
			next_page_token = messages_response.nextPageToken,
			messages = [x.message.message for x in results if x.message]
		) 

	def _get_messages_ids(
		self,
		max_results: Optional[int],
		includeSpamTrash: bool = False,
		labels: Optional[List[Labels]] = None,
		next_page_token: str = None,
		query: str = None
	)-> MessagesList:
		"""
			request should be json
			Example:
			{
				"messages": [   # List of MessageIdentifiers
					{
					object (MessageIdentifiers) 
					}
				],
				"nextPageToken": string, # Token to retrieve the next page of results in the list.
				"resultSizeEstimate": integer # Estimated total number of results.
			}
		"""
		request: Optional[MessagesList] = None
		try:
			request = self.google_service.service.users().messages().list(
				userId = self.google_service.user_id,
				maxResults = self.max_results if not max_results else max_results,
				labelIds = labels if labels else [],
				includeSpamTrash = includeSpamTrash,
				pageToken = next_page_token,
				q=query if query else ""
			).execute()
		except HttpError as e:
			raise e
		finally:
			# close connection
			self.google_service.service.close()
			if request:
				return MessagesList(**request)
			return MessagesList(resultSizeEstimate=0, messages=[], nextPageToken=None)

	def _get_drafts_ids(
		self,
		max_results: Optional[int],
		includeSpamTrash: bool = False,
		next_page_token: str = None,
		query: str = None
	)-> DraftsList:
		
		request: Optional[MessagesList] = None
		try:
			request = self.google_service.service.users().drafts().list(
				userId=self.google_service.user_id,
				maxResults=self.max_results if not max_results else max_results,
				includeSpamTrash=includeSpamTrash,
				pageToken = next_page_token,
				q=query
			).execute()
		except HttpError as e:
			raise e
		finally:
			# close connection
			self.google_service.service.close()
			if request:
				return DraftsList(**request)
			return DraftsList(resultSizeEstimate=0, drafts=[], nextPageToken=None)