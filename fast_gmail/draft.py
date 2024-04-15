from fast_gmail.message import Message

from googleapiclient.discovery import Resource


class Draft(object):
	id: str
	message: Message
	google_service: Resource

	def __init__(self, id: str, google_service: Resource, message: dict):
		self.id = id
		self.google_service = google_service
		self.message = Message(google_service=google_service, **message)


