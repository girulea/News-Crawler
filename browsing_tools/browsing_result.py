class BrowsingResult:

	def __init__(self, browser_id, current_url, canonical_url, response, mime_type, html_source, redirection_url=None, har=None, error_text=None, successful=False):
		self.browser_id = browser_id
		self.current_url = current_url
		self.canonical_url = canonical_url
		self.response = response
		self.mime_type = mime_type
		self.html_source = html_source
		self.redirection_url = redirection_url
		self.har = har
		self.error_text = error_text
		self.successful = successful
