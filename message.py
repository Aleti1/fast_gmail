from typing import Optional
from typing import List
from typing import Self
from typing import Union

from dataclasses import field
from dataclasses import dataclass

from datetime import datetime as dt
from datetime import timezone

from helpers import GoogleService
from helpers import Labels
from helpers import GmailLabel
from helpers import DATE_FORMAT

from googleapiclient.errors import HttpError

import base64
import os


@dataclass
class MessagePartBody(object):
	size: int
	attachmentId: Optional[str] = None
	data: Optional[str] = None

@dataclass
class MessageHeader(object):
	name: str
	value: str

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
