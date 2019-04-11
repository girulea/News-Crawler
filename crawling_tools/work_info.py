from crawling_tools.work_status import WorkStatus


class WorkInfo(object):

	def __init__(self, url, protocol='', language=None, is_webnews=None, title_art=None, publish_date=None, img_art=None, videos_art=None, authors=None, category=None):
		self.url = url
		self.protocol = protocol
		self.language = language
		self.is_webnews = is_webnews
		self.title_art = title_art
		self.publish_date = publish_date
		self.img_art = img_art
		self.videos_art = videos_art
		self.authors = authors
		self.category = category
		self.work_status = WorkStatus.ProcessingInQueue
		self.failed_attempts = 0
		self.error_text = None