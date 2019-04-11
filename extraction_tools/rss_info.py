
class RssInfo:

	def __init__(self, url, sections='', language=None, last_update=None):
		self.url = url
		self.last_update = last_update
		self.sections = sections
		self.language = language
