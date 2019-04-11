from threading import Thread
from crawling_tools.crawler import Crawler
from browsing_tools.custom_webbrowser import CustomWebBrowser
import time
import queue
from threading import Lock
import curses
import utils
from prettytable import PrettyTable


class CrawlerManager():
	def __init__(self, urls_list, only_webnews=False, headless=True, num_of_crawler=4, n_crawler_thread=4, working_dir='', driver_ex_path='chromedriver'):
		self.urls_queue = self._fill_queue(urls_list)
		self.num_of_crawler = num_of_crawler
		self.n_crawler_thread = n_crawler_thread
		self.driver_ex_path = driver_ex_path
		self.working_dir = working_dir
		self.headless = headless
		self.only_webnews = only_webnews
		self._crawlers = list()
		self._wb_instantiator_locker = Lock()
		self._crawlers_locker = Lock()
		self._last_update_details = dict()
		self._table_headers = ['url', 'started UTC', 'running', 'free workers', 'scraped', 'redirection', 'failed', 'exception crawler', 'added datacollector', 'count last insert', 'datacollector queue len', 'exception datacollector', 'last update UTC']

	def start(self):
		num = 0
		while not self.urls_queue.empty() and num < self.num_of_crawler:
			self._start_new_crawler()
			# time.sleep(2)
			num += 1
			# print('started %d' % num)
		stdscr = curses.initscr()
		curses.noecho()
		curses.cbreak()
		while True:
			try:
				table = self._create_pretty_table()
				# print('enter clear')
				stdscr.clear()
				# print('exit clear')
				stdscr.addstr(str(table))
				stdscr.refresh()
				time.sleep(10)
			except Exception as ex:
				print(ex)
				time.sleep(3)
				curses.endwin()
				stdscr = curses.initscr()

	def instantiate_browser(self, logging=True, id_wb=''):
		result = None
		with self._wb_instantiator_locker:
			try:
				result = CustomWebBrowser(logging=logging, headless=self.headless, id_browser=id_wb, ex_path=self.driver_ex_path)
				result.start()
				time.sleep(4)
			except Exception as e:
				print(e)
		return result

	def release_slot(self, url):
		self._start_new_crawler()


	def _fill_queue(self, urls_list):
		q = queue.Queue()
		for url in urls_list:
			q.put(url)
		return q

	def _configure_crawler(self, url):
		_cr = Crawler(url, only_webnews=self.only_webnews, num_of_workers=self.n_crawler_thread, headless=self.headless,
					  working_dir=self.working_dir, driver_ex_path=self.driver_ex_path,
					  _wb_instantiator_f=self.instantiate_browser, end_function=self.release_slot)
		return _cr

	def _start_new_crawler(self):
		if not self.urls_queue.empty():
			url = self.urls_queue.get()
			_cr = self._configure_crawler(url)
			_cr.start()
			with self._crawlers_locker:
				self._crawlers.append(_cr)

	def _create_pretty_table(self):
		table = PrettyTable(self._table_headers)
		with self._crawlers_locker:
			current_time = utils.get_current_time_form()
			for crawler in self._crawlers:
				if crawler.started:
					row = self._create_row_from_crawler(crawler, current_time)
					self._last_update_details[crawler.url] = row
				elif crawler.url in self._last_update_details.keys():
					self._last_update_details[crawler.url][2] = False
					row = self._last_update_details[crawler.url]
				else:
					row = [''] * 13
				table.add_row(row)
		return table

	def _create_row_from_crawler(self, crawler, current_time):
		last_exception = crawler.last_exception
		if last_exception and len(last_exception) > 25:
			last_exception = last_exception[:25]
		last_exception_data_collector = crawler.get_last_exception_datacollector()
		if last_exception_data_collector and len(last_exception_data_collector) > 25:
			last_exception_data_collector = last_exception_data_collector[:25]
		url = crawler.url
		start_time = crawler.start_time
		is_alive = crawler.started
		current_scraped = crawler.num_of_processed_urls
		current_redirection = crawler.num_of_redirection
		current_failed = crawler.num_of_failed_urls
		#total_scraped = crawler.get_count_scraped()
		#to_scrape = crawler.get_count_to_scrape()
		free_workers = crawler._num_of_free_workers()
		addeds_to_data_collector = crawler.get_work_added_datacollector()
		count_last_insert = crawler.get_count_last_insert()
		queue_len = crawler.get_work_queue_len()
		return [url, start_time, is_alive, free_workers, current_scraped, current_redirection, current_failed, last_exception, addeds_to_data_collector, count_last_insert, queue_len, last_exception_data_collector, current_time]