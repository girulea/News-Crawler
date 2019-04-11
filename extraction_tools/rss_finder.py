from extraction_tools.extractor import ContentExtractor
import utils
from browsing_tools.custom_webbrowser import HttpResponse


class RssFinder:

	def __init__(self, web_browser, start_url):
		self.start_url = start_url
		self.web_browser = web_browser

	def search_rss_from_domain(self):
		browsing_res = self.web_browser.download_page(self.start_url)
		domain = utils.get_principal_domain(self.start_url)
		html_source = browsing_res.html_source
		mime_type = browsing_res.mime_type
		feeds_rss = dict()
		if browsing_res.successful and mime_type == 'text/html':
			extractor = ContentExtractor()
			extractor.prepare_html_tree(html=str(html_source), url=self.start_url, domain=domain)
			feeds_rss = extractor.extract_feed_rss()
			rss_url = extractor.extract_rss_source()
			for url in rss_url:
				browsing_res1 = self.web_browser.download_page(url)
				html_source1 = browsing_res1.html_source
				domain = utils.get_principal_domain(url)
				mime_type = browsing_res1.mime_type
				if browsing_res1.successful and browsing_res1.response in (HttpResponse.OK_RESPONSE, HttpResponse.MOVED_PERMANENTLY_RESPONSE):
					if mime_type == "text/html":
						if url in feeds_rss:
							feeds_rss.pop(url)
						extractor1 = ContentExtractor()
						extractor1.prepare_html_tree(html=str(html_source1), url=url, domain=domain)
						feeds_rss.update(extractor1.extract_feed_rss())
					elif mime_type in ('text/plain', 'text/xml'):
						feeds_rss[url] = ''
		elif browsing_res.successful and mime_type in ('text/plain', 'text/xml'):
			feeds_rss[self.start_url] = ''
		return feeds_rss
