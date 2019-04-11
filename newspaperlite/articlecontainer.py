
class ArticleContainer:

	def __init__(self, title, top_img, url, language='it', text='', publish_date='', videos='', authors='', sections=''):
		self.title = title
		self.language = language
		self.sections = sections
		self.authors = authors
		self.top_img = top_img
		self.url = url
		self.text = text
		self.publish_date = publish_date
		self.videos = videos
