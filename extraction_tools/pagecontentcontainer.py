
class PageContentContainer:

	def __init__(self, text, url, language=None, har=None, article_c=None, in_links=None, outbound_links=None, scripts=None, iframes=None, page_videos=None, images=None, html=None, styles=None):
		self.text = text
		self.url = url
		self.language = language
		self.article_c = article_c
		self.in_links = in_links
		self.har = har
		self.outbound_links = outbound_links
		self.scripts = scripts
		self._iframes = iframes
		self.page_videos = page_videos
		self.images = images
		self.html = html
		self.styles = styles

