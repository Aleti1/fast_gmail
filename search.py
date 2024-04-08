from dataclasses import dataclass
from typing import Optional
from typing import List


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
