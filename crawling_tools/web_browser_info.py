class WebBrowserInfo(object):

	def __init__(self, web_browser):
		self.web_browser = web_browser
		self.loaded_pages = 0
		self.watch_dog = None
		self.busy = False