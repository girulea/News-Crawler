import threading
import time
from threading import Lock
import utils
from utils import get_attr_dinamically
from browsing_tools.customtimeout import CustomTimeout
from storage_tools.datacollector import DataCollector
from extraction_tools.extractor import ContentExtractor
from extraction_tools.pagecontentcontainer import PageContentContainer
from browsing_tools.custom_webbrowser import HttpResponse
from newspaperlite.articlecontainer import ArticleContainer
from extraction_tools.rss_finder import RssFinder
import datetime
import feedparser
from crawling_tools.work_info import WorkInfo
from crawling_tools.work_status import WorkStatus
from crawling_tools.web_browser_info import WebBrowserInfo
from extraction_tools.whoisinfo import WhoisInfo

class Crawler:

	def __init__(self, url, only_webnews=False, num_of_workers=3, headless=False, working_dir='tmpData/', driver_ex_path='chromedriver', _wb_instantiator_f=None, end_function=None, scrape_rss=True):
		self.url = url
		self.domain = utils.get_principal_domain(url)
		self.headless = headless
		self._jobs_info = dict()
		self.whois_info = None
		self.started = False
		self.only_webnews = only_webnews
		self.num_of_workers = num_of_workers
		self.data_collector = None
		self.scrape_rss = scrape_rss
		self.working_d = working_dir
		self.driver_ex_path = driver_ex_path
		self.domain_videos_path = None
		self._wb_instantiator_f = _wb_instantiator_f
		self._end_function = end_function
		self.webbrowsers_dict = dict()
		self.urls_dict_lock = Lock()
		self.last_exception = None
		self.num_of_processed_urls = 0
		self.num_of_redirection = 0
		self.num_of_failed_urls = 0
		self.start_time = utils.get_current_time_form()
		self._webbrowsers_dict_lock = Lock()

	def start(self):
		if not self.started:
			self.started = True
			t = threading.Thread(target=self._run)
			t.daemon = False
			t.start()

	def _run(self):
		db_name = utils.get_db_name_from_url(self.url)
		self.data_collector = DataCollector(directory=self.working_d, db_name=db_name)
		self.data_collector.add_domain_info(self.url, "per ora niente nome")
		self.data_collector.start()
		self.whois_info = WhoisInfo.create_whois_container(self.url)
		self.data_collector.add_whois_info(self.whois_info)
		if self.scrape_rss:
			self._check_rss()
		self.domain_videos_path = self.data_collector.get_domain_videos_path()
		self._init_web_browsers()
		while self._check_condictions():
			if self._num_of_free_workers() != 0 and self._there_other_work():
				if self.data_collector.len_queued_work() > 100:
					time.sleep(3)
				current_url = self._get_next_work()
				# print(current_url)
				if current_url:
					browser_id = self._get_free_browser_id()
					web_browser = self._acquire_webbrowser_by_id(browser_id, current_url)
					t = threading.Thread(target=web_browser.download_page, args=(current_url, self._process_scraped_data, True))
					t.start()
			else:
				time.sleep(0.3)
		self._release_resources()
		self.started = False
		if self._end_function:
			self._end_function(self.url)
		# print("finito: " + self.url)

	def _check_condictions(self):
		result = self._there_other_work() or \
					self._num_of_free_workers() < self.num_of_workers or \
					self.data_collector.len_queued_work() > 0
		return result

	def _process_scraped_data(self, browsing_result):
		successful = browsing_result.successful
		browser_id = browsing_result.browser_id
		current_url = browsing_result.current_url
		canonical_url = browsing_result.canonical_url
		redirection_url = browsing_result.redirection_url
		response = browsing_result.response
		mime_type = browsing_result.mime_type
		html_source = browsing_result.html_source
		har = browsing_result.har
		error_text = browsing_result.error_text
		# ads_list = self.ad_blocker.find_ads(har)
		if canonical_url and response:
			if response.value == 200 and not utils.are_equals_urls(canonical_url, current_url):
				self._mark_as_no_principal(current_url, canonical_url, 200, mime_type)
				current_url = canonical_url
		# Se il response code non è impostato su nessun valore, vuol dire che si è verificato un errore interno irrecuperabile, quindi si procede a creare una nuova istanza del webdriver
		if response is None or (not successful and response != HttpResponse.NOT_FOUND):
			self._reset_web_browser_safe(browser_id)
			self._release_failed_work(current_url, error_text)
			self._release_webbrowser_by_id(browser_id)
		elif response == HttpResponse.OK_RESPONSE:
			self._manage_extracted_data(browser_id, current_url, html_source, mime_type, har)
		elif response in (HttpResponse.MOVED_PERMANENTLY_RESPONSE, HttpResponse.REDIRECTION_RESPONSE):
			if not utils.are_equals_urls(current_url, redirection_url):
				self._mark_as_no_principal(current_url, redirection_url, response.value, mime_type)
				self._manage_extracted_data(browser_id, redirection_url, html_source, mime_type, har)
			else:
				self._manage_extracted_data(browser_id, current_url, html_source, mime_type, har)
		elif response in (HttpResponse.SERVER_ERROR_RESPONSE, HttpResponse.BAD_REQUEST_RESPONSE, HttpResponse.GENERIC_CLIENT_ERROR,
						  HttpResponse.NOT_FOUND, HttpResponse.FORBIDDEN_RESPONSE, HttpResponse.UNAUTHORIZED_RESPONSE, HttpResponse.MULTIPLE_CHOICE_RESPONSE):
			self._release_accomplished_work({current_url})
			self._release_webbrowser_by_id(browser_id)
			self.data_collector.add_extracted_data(current_url, True, self._get_attempts_count(current_url), mime_type, response.value, None, error_text=error_text)
			# print("errore di tipo 5xx url: " + current_url)
		else:
			# self._release_webbrowser_by_id(browser_id)
			print("qualcosa è andato storto")

	def _manage_extracted_data(self, browser_id, current_url, html_source, mime_type, har):
		w_info_dict = self._get_work_info_by_dict(current_url)
		self._release_countdown_by_id(browser_id)
		if html_source is None or len(html_source) < 200 or mime_type is None or mime_type != "text/html":
			self._release_webbrowser_by_id(browser_id)
			self.data_collector.add_extracted_data(current_url, True, self._get_attempts_count(current_url), mime_type, 200, None)
		else:
			extractor = ContentExtractor()
			extractor.prepare_html_tree(html=str(html_source), url=current_url, domain=self.domain)
			extracted = extractor.extract_content(d_v_path=self.domain_videos_path, **w_info_dict)
			self._release_webbrowser_by_id(browser_id)
			if extracted.article_c:
				extracted.har = har
			self.data_collector.add_extracted_data(current_url, scraped=True, attempts_count=self._get_attempts_count(current_url), mime_type=mime_type, http_response_code=200, page_content_container=extracted)
		self._release_accomplished_work({current_url})

	def _mark_as_no_principal(self, url, url_to_refer, response_code, mime_type):
		self.num_of_redirection = self.num_of_redirection + 1
		self._add_works([url_to_refer], work_status=WorkStatus.ProcessingInQueue)
		self.data_collector.add_extracted_data(url, scraped=True, attempts_count=self._get_attempts_count(url), mime_type=mime_type, http_response_code=response_code, page_content_container=None, url_to_refer=url_to_refer)
		self._release_accomplished_work({url})

	def _get_work_info_by_dict(self, url):
		result = dict()
		with self._webbrowsers_dict_lock:
			if url in self._jobs_info.keys():
				work_info = self._jobs_info[url]
			else:
				work_info = WorkInfo(url=url)
			#result['protocol'] = work_info.protocol
			result['language'] = work_info.language
			result['is_webnews'] = work_info.is_webnews
			result['title_art'] = work_info.title_art
			result['publish_date'] = work_info.publish_date
			result['img_art'] = work_info.img_art
			result['videos_art'] = work_info.videos_art
			result['authors'] = work_info.authors
			result['category'] = work_info.category
		return result

	def _init_web_browsers(self):
		with self._webbrowsers_dict_lock:
			try:
				for i in range(0, self.num_of_workers):
					_id = utils.new_random_id(8)
					while _id in self.webbrowsers_dict.keys():
						_id = utils.new_random_id(8)
					web_browser = self._init_web_browser(_id)
					web_browser_info = WebBrowserInfo(web_browser)
					web_browser_info.watch_dog = CustomTimeout(_id, 300, self._timeout_handler)
					# print("_id: " + str(_id))
					self.webbrowsers_dict[_id] = web_browser_info
					# time.sleep(0.1)
			except Exception as e:
				print(e)

	def get_count_scraped(self):
		result = 0
		if self.data_collector:
			result = self.data_collector.get_count_scraped()
		return result

	def get_count_to_scrape(self):
		result = 0
		if self.data_collector:
			result = self.data_collector.get_count_to_scrape()
		return result

	def get_last_exception_datacollector(self):
		result = None
		if self.data_collector:
			result = self.data_collector.last_exception
		return result

	def get_work_added_datacollector(self):
		result = 0
		if self.data_collector:
			result = self.data_collector.work_added_count
		return result

	def get_work_queue_len(self):
		result = 0
		if self.data_collector:
			result = self.data_collector.len_queued_work()
		return result

	def get_count_last_insert(self):
		result = 0
		if self.data_collector:
			result = self.data_collector.count_last_insert
		return result

	def _release_resources(self):
		with self._webbrowsers_dict_lock:
			for key_w in self.webbrowsers_dict.keys():
				try:
					self.webbrowsers_dict[key_w].watch_dog.stop_countdown()
					web_browser = self.webbrowsers_dict[key_w].web_browser
					web_browser.stop()
				except Exception as ex:
					self.last_exception = "crawler _release_resources: " + str(ex)
			self.webbrowsers_dict = None
		try:
			if self.data_collector:
				self.data_collector.stop()
		except Exception as e:
			self.last_exception = str(e)

	def _init_web_browser(self, _id):
		success = False
		web_browser = None
		while not web_browser:
			try:
				web_browser = self._wb_instantiator_f(logging=True, id_wb=_id)
				time.sleep(0.2)
			except Exception as ex:
				self.last_exception = "init_webbrowser: " + str(ex)
		return web_browser

	def _reset_web_browser_safe(self, _id):
		with self._webbrowsers_dict_lock:
			try:
				web_browser = self.webbrowsers_dict[_id].web_browser
				if web_browser:
					web_browser.stop()
			except Exception as e:
				print(e)
			self.webbrowsers_dict[_id].watch_dog.stop_countdown()
			self.webbrowsers_dict[_id].loaded_pages = 0
			self.webbrowsers_dict[_id].web_browser = self._init_web_browser(_id)

	def _get_free_browser_id(self):
		result = None
		for _id in self.webbrowsers_dict.keys():
			if not self.webbrowsers_dict[_id].busy:
				result = _id
				break
		return result

	def _acquire_webbrowser_by_id(self, _id, url):
		with self._webbrowsers_dict_lock:
			self.webbrowsers_dict[_id].busy = True
			self.webbrowsers_dict[_id].watch_dog.start_countdown(url)
			return self.webbrowsers_dict[_id].web_browser

	def _release_webbrowser_by_id(self, _id):
		with self._webbrowsers_dict_lock:
			self.webbrowsers_dict[_id].watch_dog.stop_countdown()
			self.webbrowsers_dict[_id].loaded_pages += 1
			if self.webbrowsers_dict[_id].loaded_pages > 30:
				self._reset_web_browser(_id)
				time.sleep(0.2)
			self.webbrowsers_dict[_id].busy = False

	def _release_countdown_by_id(self, _id):
		with self._webbrowsers_dict_lock:
			self.webbrowsers_dict[_id].watch_dog.stop_countdown()

	def _reset_web_browser(self, _id):
		try:
			web_browser = self.webbrowsers_dict[_id].web_browser
			if web_browser:
				web_browser.stop()
		except Exception as ex:
			self.last_exception = "crawler _reset_web_browser: " + str(ex)
		self.webbrowsers_dict[_id].web_browser = self._init_web_browser(_id)
		self.webbrowsers_dict[_id].watch_dog.stop_countdown()
		self.webbrowsers_dict[_id].loaded_pages = 0

	def _num_of_free_workers(self):
		result = 0
		for _id in self.webbrowsers_dict.keys():
			if not self.webbrowsers_dict[_id].busy:
				result += 1
		return result

	def _add_works(self, urls, work_status=WorkStatus.ProcessingInQueue):
		result = False
		with self.urls_dict_lock:
			for url in urls:
				scheme, cleaned_url = utils.split_url_and_scheme(url)
				if cleaned_url not in self._jobs_info.keys():
					self._jobs_info[cleaned_url] = WorkInfo(cleaned_url, protocol=scheme)
					self._jobs_info[cleaned_url].work_status = work_status
					result = True
		return result

	def _add_works_by_dicts(self, dcts_lst, work_status=WorkStatus.ProcessingInQueue):
		with self.urls_dict_lock:
			for dct in dcts_lst:
				w_info = WorkInfo(**dct)
				if w_info.url and w_info.url not in self._jobs_info.keys():
					self._jobs_info[w_info.url] = w_info
					self._jobs_info[w_info.url].work_status = work_status

	def _add_work_unsafe(self, url, protocol, work_status=WorkStatus.ProcessingInQueue, failed_attempts=0, error_text=None):
		result = False
		if url not in self._jobs_info.keys():
			self._jobs_info[url] = WorkInfo(url)
			self._jobs_info[url].protocol = protocol
			self._jobs_info[url].work_status = work_status
			self._jobs_info[url].failed_attempts = failed_attempts
			self._jobs_info[url].error_text = error_text
			result = True
		return result

	def _get_next_work(self):
		result = None
		with self.urls_dict_lock:
			for url in self._jobs_info.keys():
				work_info = self._jobs_info[url]
				status = work_info.work_status
				failed_attempts = work_info.failed_attempts
				if status == WorkStatus.ProcessingInQueue and failed_attempts < 2:
					self._jobs_info[url].work_status = WorkStatus.UnderProcessing
					protocol = self._jobs_info[url].protocol
					result = str(protocol + url)
					break
		return result

	def _get_attempts_count(self, url):
		result = 0
		with self.urls_dict_lock:
			if url in self._jobs_info.keys():
				result = self._jobs_info[url].failed_attempts
		return result

	def _release_failed_work(self, url, error_text):
		self.num_of_failed_urls = self.num_of_failed_urls + 1
		with self.urls_dict_lock:
			scheme, cleaned_url = utils.split_url_and_scheme(url)
			if cleaned_url not in self._jobs_info.keys():
				self._add_work_unsafe(cleaned_url, scheme, work_status=WorkStatus.UnderProcessing)
			self._jobs_info[cleaned_url].failed_attempts += 1
			self._jobs_info[cleaned_url].error_text = error_text
			self._jobs_info[cleaned_url].work_status = WorkStatus.ProcessingInQueue

	def _release_accomplished_work(self, urls):
		self.num_of_processed_urls = self.num_of_processed_urls + 1
		with self.urls_dict_lock:
			for url in urls:
				scheme, cleaned_url = utils.split_url_and_scheme(url)
				if cleaned_url not in self._jobs_info.keys():
					self._add_work_unsafe(cleaned_url, scheme, work_status=WorkStatus.Processed)
				else:
					self._jobs_info[cleaned_url].work_status = WorkStatus.Processed

	def _there_other_work(self):
		result = False
		with self.urls_dict_lock:
			for url in self._jobs_info.keys():
				work_info = self._jobs_info[url]
				status = work_info.work_status
				failed_attempts = work_info.failed_attempts
				if status == WorkStatus.ProcessingInQueue and failed_attempts < 2:
					result = True
					break
		if not result:
			other = self.data_collector.get_candidates(200)
			if other:
				self._add_works_by_dicts(other, work_status=WorkStatus.ProcessingInQueue)
				result = True
			self._remove_finished_work()
			self._remove_failed_work()
		return result

	def _remove_finished_work(self):
		elementToRemove = list()
		with self.urls_dict_lock:
			for url in self._jobs_info.keys():
				work_status = self._jobs_info[url].work_status
				if work_status == WorkStatus.Processed:
					elementToRemove.append(url)
			for url in elementToRemove:
				self._jobs_info.pop(url, None)

	def _remove_failed_work(self):
		elementToRemove = list()
		with self.urls_dict_lock:
			for url in self._jobs_info.keys():
				work_status = self._jobs_info[url].work_status
				failed_attempts = self._jobs_info[url].failed_attempts
				e_text = self._jobs_info[url].error_text
				if work_status == WorkStatus.ProcessingInQueue and failed_attempts >= 2:
					self.data_collector.add_extracted_data(url, True, failed_attempts, None, -1, None, error_text=e_text)
					# self.data_collector.add_extracted_data(url, False, failed_attempts, None)
					elementToRemove.append(url)
			for url in elementToRemove:
				self._jobs_info.pop(url, None)

	def _timeout_handler(self, browser_id, url):
		self._reset_web_browser_safe(browser_id)
		time.sleep(2)
		self._release_failed_work(url, 'timeout del browser')
		# self._release_webbrowser_by_id(browser_id)
		self._release_webbrowser_by_id(browser_id)
		self.last_exception = 'timeout del browser'

	def _check_rss(self):
		feeds_rss = self.data_collector.get_feeds_rss()
		if len(feeds_rss) == 0:
			scraped_rss = self._search_rss_from_domain()
			self.data_collector.add_feeds_rss(scraped_rss)
			feeds_rss = self.data_collector.get_feeds_rss()
		self._update_rss(feeds_rss)

	def _update_rss(self, feeds_rss):
		for feed in feeds_rss:
			last_update_feed = utils.parse_date_str(feed.last_update)
			parsed_feed = feedparser.parse(feed.url)
			feed_release_date, feed_sections, link_section, language = self._get_info_from_feed(parsed_feed)
			if feed.language is None or feed.sections is None:
				self.data_collector.update_details_feed(feed.url, language, feed_sections)
			if last_update_feed is None or feed_release_date is None or feed_release_date > last_update_feed:
				for entry in parsed_feed.entries:
					self._parse_rss_entry(entry, language, feed_sections)
			self.data_collector.update_timestamp_feed(feed.url)

	def _get_info_from_feed(self, parsed_feed):
		feed_release_date = self._get_parsed_dates_from_object(parsed_feed, 'updated_parsed')
		feed_sections = get_attr_dinamically(parsed_feed.feed, 'title')
		link_section = get_attr_dinamically(parsed_feed.feed, 'link')
		language = get_attr_dinamically(parsed_feed.feed, 'language')
		if language and len(language) >= 2:
			language = language[:2].lower()
		return feed_release_date, feed_sections, link_section, language

	def _parse_rss_entry(self, entry, language, feed_sections):
		title = get_attr_dinamically(entry, 'title')
		link = get_attr_dinamically(entry, 'link')
		link = utils.clean_url(link, remove_arguments=False)
		article_date = self._get_parsed_dates_from_object(entry, 'published_parsed')
		article_container = ArticleContainer(url=link, title=title, publish_date=article_date, top_img=None, sections=[feed_sections])
		extracted = PageContentContainer(None, url=link, article_c=article_container, language=language)
		self.data_collector.add_extracted_data(link, 0, 0, 'text/html', 0, page_content_container=extracted)

	def _get_parsed_dates_from_object(self, obj, attribute_name_date):
		result = None
		parsed_date = get_attr_dinamically(obj, attribute_name_date)
		if parsed_date:
			result = datetime.datetime(*parsed_date[:6])
		return result

	def _search_rss_from_domain(self):
		web_browser = self._init_web_browser('')
		rss_finder = RssFinder(web_browser, self.url)
		feeds_rss = rss_finder.search_rss_from_domain()
		web_browser.stop()
		return feeds_rss
