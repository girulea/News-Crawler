class WorkDataContainer(object):

	def __init__(self, url, scraped, attempts_count, mime_type, http_response_code, page_content_container, url_to_refer=None, error_text=None):
		self.url = url
		self.scraped = scraped
		self.attempts_count = attempts_count
		self.mime_type = mime_type
		self.http_response_code = http_response_code
		self.error_text = error_text
		self.page_content_container = page_content_container
		self.url_to_refer = url_to_refer
