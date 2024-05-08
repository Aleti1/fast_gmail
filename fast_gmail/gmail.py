from typing import Optional
from typing import Union
from typing import List
import mimetypes
import base64
import os
import json

from email.message import EmailMessage
from email.header import Header
from email import utils

from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from googleapiclient.errors import HttpError
from google_auth_oauthlib.flow import InstalledAppFlow
from google_auth_oauthlib.flow import Flow

from fast_gmail.message import MessagePartBody
from fast_gmail.message import Message
from fast_gmail.search import SearchParams
from fast_gmail.draft import Draft
from fast_gmail.helpers import *


# If modifying these scopes, delete the file token.json.
SCOPES = [
	"https://www.googleapis.com/auth/gmail.modify",
	"https://www.googleapis.com/auth/gmail.settings.basic",
	"https://www.googleapis.com/auth/contacts.readonly",
	"https://www.googleapis.com/auth/contacts.other.readonly"
]


class GmailApi(object):
	"""https://googleapis.github.io/google-api-python-client/docs/dyn/gmail_v1.users.html"""
	credentials: Optional[Credentials] = None
	google_service: GoogleService
	max_results: int = MAX_RESULTS
	SEPARATOR_SYMBOL: str
	profile_data: Optional[GmailProfile] = None
	redirect_uri: Optional[str] = None

	def __init__(
		self,
		token_file_path: str = "token.json",
		credentials_file_path: str = "credentials.json",
		port: int = 3000, # set the local server port for Authorized redirect URI
		separator_symbol: str = ", ",
		user_id: str = "me",
		application_type: ApplicationType = ApplicationType.WEB,
		code: Optional[str] = None
	)-> None:
		"""https://github.com/googleapis/google-api-python-client/blob/main/docs/oauth-installed.md"""

		# set separator for spliting/joining the array of existing previous_page_tokens for pagination
		self.SEPARATOR_SYMBOL = separator_symbol
		# The file token.json stores the user's access and refresh tokens, and is
		# created automatically when the authorization flow completes for the first time.
		if os.path.exists(token_file_path):
			self.credentials = Credentials.from_authorized_user_file(token_file_path, SCOPES)
		self.auth_url: str = ""
		# If there are no (valid) credentials available, let the user log in.
		if not self.credentials or not self.credentials.valid:
			if self.credentials and self.credentials.expired and self.credentials.refresh_token:
				# refresh access token
				self.credentials = Credentials(
					token=None,  # No initial token provided, refresh token will be used
					refresh_token=self.credentials.refresh_token,
					token_uri=self.credentials.token_uri,
					client_id=self.credentials.client_id,
					client_secret=self.credentials.client_secret
				)
			else:
				if not os.path.exists(credentials_file_path):
					raise FileNotFoundError(f"{credentials_file_path=} NOT FOUND!")
				match application_type:
					case ApplicationType.INSTALLED:
						flow = InstalledAppFlow.from_client_secrets_file(
							credentials_file_path, SCOPES
						)
						self.credentials = flow.run_local_server(port=port)
					case ApplicationType.WEB:
						cred_payload: Optional[dict] = None
						with open(credentials_file_path, "r") as f:
							cred_payload = json.loads(f.read())
						if not cred_payload:
							raise Exception(f"Could't read {credentials_file_path=}")
						if not "web" in cred_payload:
							raise Exception(
								f"{cred_payload=} content missing."
								"\n\033[91mDid you create credentials for Web app?\033[0m"
							)
						if not "redirect_uris" in cred_payload["web"] or not cred_payload["web"]["redirect_uris"]:
							raise Exception(
								f"Missing `redirect_uris` key from {cred_payload['web']}."
								"\n\033[91mDid you define Authorized redirect URIs?\033[0m"
							)
						
						redirect_uris = cred_payload["web"]["redirect_uris"]
						for uri in redirect_uris:
							if str(port) in uri:
								self.redirect_uri = uri
						if not self.redirect_uri:
							self.redirect_uri = redirect_uris[0]
						self.flow = Flow.from_client_secrets_file(
							credentials_file_path,
							SCOPES,
                            redirect_uri=self.redirect_uri
                        )
						if code:
							self.flow.fetch_token(code=code)
							self.credentials = self.flow.credentials
						else:
							self.auth_url = f"{self.flow.authorization_url()[0]}&prompt=consent"
							return
			# Save the credentials for the next run
			with open(token_file_path, "w") as token:
				token.write(self.credentials.to_json())
		try:
			# Call the Gmail API and set the instance 
			self.google_service = GoogleService(
				service = build("gmail", "v1", credentials = self.credentials),
				user_id = user_id
			)
		except HttpError as e:
			raise e

	def get_message(self, id: str)-> Optional[Message]:
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
	
	def get_draft(self, id: str)-> Optional[Message]:
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
		in_reply_to: Optional[str] = None,
		signature: bool = True
	)-> Optional[Message]:
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
		msg = EmailMessage()
		msg["To"] = to
		msg["From"] = str(Header(f"{sender} <{sender}>"))
		msg["Subject"] = subject if not in_reply_to else f"Re: {subject}"
		msg["Date"] = utils.formatdate(localtime=1)
		msg["Cc"] = ", ".join(cc) if cc else ""
		msg["Bcc"] = ", ".join(bcc) if bcc else ""
		if in_reply_to:
			msg["In-Reply-To"] = in_reply_to
			msg["References"] = in_reply_to
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
		labels: Union[List[Labels], List[str], None] = None,
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
		next_page_token: str = None,
		existing_pages: Optional[List[str] | str] = None,
		previous_page_token: Optional[str] = None,
		query: Union[SearchParams, str] = None,
	)-> Union[List[Draft], list]:
		return self._get_drafts(
			includeSpamTrash = includeSpamTrash,
			max_results = max_results,
			next_page_token = next_page_token,
			existing_pages=existing_pages,
			previous_page_token = previous_page_token,
			query=query.query if isinstance(query, SearchParams) else query
		)

	def get_attachment(
		self,
		message_id: str,
		attachment_id: str
	)-> Optional[MessagePartBody]:
		try:
			return MessagePartBody(**self.google_service.service.users().messages().attachments().get(
				userId=self.google_service.user_id,
				messageId=message_id,
				id=attachment_id
			).execute())
		except HttpError as e:
			raise e
		finally:
			self.google_service.service.close()

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
		"""Retrieves and caches the authorized user's Gmail profile information.
			This property is a cached accessor for the user's Gmail profile data. 
			The first call will fetch the data from the Gmail API and store it internally. 
			Subsequent calls will return the cached data unless it's explicitly cleared.
			Returns:
				Optional[GmailProfile]: An object containing the user's Gmail profile information, 
				or None if there's an error fetching the data.
			Raises:
				HttpError: An exception if there is an error fetching profile information from the Gmail API.
		"""
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
		"""Retrieves information about a specific send-as alias for the authorized user.
			Args:
				email_address (str): The email address of the send-as alias to retrieve information for.
			Raises:
				HttpError: An exception if there is an error fetching alias information from the Gmail API.
			Returns:
				dict: A dictionary containing information about the alias, 
					or an empty dictionary if the alias is not found.

			This method is private and intended for internal use. 
		"""
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
		"""Retrieves drafts from a user's mailbox."""
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
			previous_page_token = next_page_token,
			next_page_token = messages_response.nextPageToken,
			existing_pages = self.SEPARATOR_SYMBOL.join(existing_pages) if existing_pages else None,
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

	def get_contacts(self)-> Optional[list]:
		try:
			request = build("people", "v1", credentials = self.credentials).otherContacts().list(
				pageSize=1000,
				readMask="emailAddresses"
			).execute()
			return request["otherContacts"] if "otherContacts" in request else None
		except HttpError as e:
			raise e
		
	def search_contacts(self, query: str)-> Optional[list]:
		try:
			request = build("people", "v1", credentials = self.credentials).otherContacts().search(
				pageSize=30,
				readMask="emailAddresses",
				query = query
			).execute()
			return request["results"] if "results" in request else None
		except HttpError as e:
			raise e
