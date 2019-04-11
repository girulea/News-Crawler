import sqlite3
import threading
import time
import queue
from newspaperlite import Article
from extraction_tools.rss_info import RssInfo
from .work_data_container import WorkDataContainer
from storage_tools._datacollector_statements \
	import CREATION_QUERY_DOMAIN, \
	CREATION_QUERY_DATES_COLLECT, CREATION_QUERY_PAGES, CREATION_HAR_URLS_QUERY, CREATION_PAGE_HAR_URL_ASSOCIATED_QUERY, \
	CREATE_INDEX_ON_DB_QUERY, CREATE_FEED_RSS_QUERY
import utils
from .abstract_datacollector import AbstractDataCollector
from extraction_tools.ads_extractor import AdsExtractor
import apsw
import datetime

class DataCollector(AbstractDataCollector):

	def __init__(self, directory=None, db_name='tmp.db'):
		AbstractDataCollector.__init__(self, directory, db_name)
		#self.directory = directory
		#self.db_name = db_name
		self.started = False
		self._db_connection = None
		self.domain = None
		self.domain_name = None
		self.whois_dict = None
		self._queued_works = queue.Queue()
		self.work_added_count = 0
		self.count_last_insert = 0
		self.db_path = None
		self._thread_ads_finder = None

	def start(self):
		if not self.started:
			self.started = True
			self._prepare_db()
			#self.ad_blocker = AdsExtractor()
			t = threading.Thread(target=self._run)
			t.daemon = False
			t.start()

	def stop(self):
		self.started = False

	def add_whois_info(self, whois_info):
		CREATION_QUERY_WHOIS_RECORD = '''CREATE TABLE IF NOT EXISTS whois_record
								(creation_date TEXT,
								updated_date TEXT,
								expiration_date TEXT,
								country TEXT,
								state TEXT,
								status TEXT);'''
		db_connection = apsw.Connection(self.db_path)
		db_connection.setbusytimeout(500)
		c = db_connection.cursor()
		c.execute(CREATION_QUERY_WHOIS_RECORD)
		c.execute('begin;')
		c.execute('delete from whois_record')
		c.execute('commit')
		INSERT_QUERY = "INSERT OR IGNORE INTO whois_record "\
						"(creation_date, updated_date, expiration_date, country, state, status) "\
						"VALUES(?, ?, ?, ?, ?, ?)"
		try:
			c.execute('begin;')
			c.execute(INSERT_QUERY, (utils.convert_datetime_to_format_str(whois_info.creation_date), utils.convert_datetime_to_format_str(whois_info.updated_date), utils.convert_datetime_to_format_str(whois_info.expiration_date), whois_info.country, whois_info.state, whois_info.status))
			c.execute('commit')
			c.close()
			db_connection.close()
		except Exception as e:
			print('____________')
			print(self.domain)
			print(e)
			print('____________')

	def add_domain_info(self, domain, domain_name):
		self.domain = domain
		self.domain_name = domain_name

	def create_connection(self):
		connection = apsw.Connection(self.db_path)
		connection.setbusytimeout(500)
		#connection = sqlite3.connect(self.db_path, detect_types=sqlite3.PARSE_DECLTYPES)
		connection.cursor().execute("PRAGMA journal_mode=WAL")
		return connection

	def commit_change(self, connection, cursor):
		if connection:
			cursor.execute('commit')
			#connection.commit()

	def rollback(self, connection):
		if connection:
			pass
			#connection.rollback()

	def close_connection(self, connection):
		if connection:
			connection.close()

	def get_cursor_from_connection(self, connection):
		return connection.cursor()

	def get_count_scraped(self):
		res = self.raw_read('select count(id) FROM pages where scraped=1')
		if res:
			return res[0][0]
		return 0

	def get_count_to_scrape(self):
		res = self.raw_read('select count(id) FROM pages where scraped=0')
		if res:
			return res[0][0]
		return 0

	def read_data(self, cursor, query_string, values_condictions=None):
		result = list()
		if values_condictions:
			cursor.execute(query_string, values_condictions)
			rows = cursor.fetchall()
			if rows:
				for row in rows:
					result.append(row)
		else:
			cursor.execute(query_string)
			rows = cursor.fetchall()
			if rows:
				for row in rows:
					result.append(row)
		return result

	def write_data(self, cursor, statement, data_to_associate):
		cursor.execute('begin;')
		if data_to_associate and len(data_to_associate) > 1:
			cursor.executemany(statement, data_to_associate)
		elif data_to_associate:
			cursor.execute(statement, data_to_associate[0])

	def add_extracted_data(self, url, scraped, attempts_count, mime_type, http_response_code, page_content_container=None, url_to_refer=None, error_text=None):
		if scraped:
			self.work_added_count = self.work_added_count + 1
		self._queued_works.put(WorkDataContainer(url, scraped, attempts_count, mime_type, http_response_code, page_content_container, url_to_refer, error_text))

	def add_feeds_rss(self, feeds_rss):
		tps = list()
		for feed in feeds_rss:
			tps.append((feed, feeds_rss[feed]))
		self.insert_data('feed_rss', ['url', 'class'], tps)

	def _get_page_identifier_(self, url):
		result = -1
		tmp = self.select_from_table('pages', ['id'], ['url'], (url, ), limit=1)
		if tmp:
			result = tmp[0][0]
		return result

	def get_feeds_rss(self):
		result = list()
		rows = self.select_from_table('feed_rss', ['url', 'class', 'language', 'last_update'])
		for row in rows:
			result.append(RssInfo(row[0], row[1], row[2], row[3]))
		return result

	def update_details_feed(self, url, language, sections):
		self.update_data('feed_rss', ['class', 'language'], [(sections, language, url)], ['url'])

	def update_timestamp_feed(self, url):
		self.update_data('feed_rss', ['last_update'], [(utils.get_current_time_form(), url)], ['url'])

	def get_candidates(self, count):
		result = self._get_candidates(count, webnews_priority=True)
		if len(result) < count:
			result.extend(self._get_candidates(count - len(result)))
		if len(result) == 0:
			result = None
		return result

	def get_domain_videos_path(self):
		result = None
		try:
			res = self.select_from_table('domain_info', ['domain_videos_path'])
			if res:
				result = res[0]
			condiction = True
		except Exception:
			pass
		return result

	def len_queued_work(self):
		return self._queued_works.qsize()

	def _get_candidates(self, count, webnews_priority=False):
		is_webnews = int(webnews_priority)
		result = list()
		condiction = False
		params = ['url', 'protocol', 'scraped', 'attempts_count', 'language', 'is_webnews', 'title_art', 'publish_date', 'img_art', 'videos_art', 'authors', 'category']
		condictions = ['scraped', 'attempts_count', 'is_webnews']
		values_condictions = (0, 0, int(webnews_priority))
		rows = self.select_from_table('pages', params, condictions, values_condictions, limit=count)
		for row in rows:
			tmp = {'url': row[0], 'protocol': row[1], 'language': row[3], 'is_webnews': row[4], 'title_art': row[5], 'publish_date': row[6],
				   'img_art': row[7], 'videos_art': row[8], 'authors': row[9], 'category': row[10]}
			result.append(tmp)
		return result

	def _prepare_db(self):
		if self.directory:
			self.db_path = self.directory + '/'
			# utils.create_directory(self.directory)
		self.db_path += self.db_name
		self._db_connection = sqlite3.connect(self.db_path, detect_types=sqlite3.PARSE_DECLTYPES)
		c = self._db_connection.cursor()
		#c.execute('DROP TABLE IF EXISTS domain_info;')
		c.execute(CREATION_QUERY_DOMAIN)
		c.execute(CREATION_QUERY_DATES_COLLECT)
		c.execute(CREATION_QUERY_PAGES)
		c.execute(CREATION_HAR_URLS_QUERY)
		c.execute(CREATION_PAGE_HAR_URL_ASSOCIATED_QUERY)
		c.execute(CREATE_FEED_RSS_QUERY)
		for qry in CREATE_INDEX_ON_DB_QUERY:
			c.execute(qry)
		self._db_connection.commit()
		self._db_connection.close()

	def _run(self):
		num_of_record = 50
		min = 10
		saved_record = 0
		if self.domain:
			#curs = self._db_connection.cursor()
			#curs.execute("INSERT OR IGNORE INTO domain_info VALUES(?,?,?)", (self.domain, self.domain_name, None))
			#curs.execute('INSERT OR IGNORE INTO pages (url, scraped, attempts_count) VALUES(?, ?, ?)', (self.domain, False, 0))
			#self._db_connection.commit()
			#curs.close()
			self._insert_links([self.domain])
		self._active_detects_ads()
		while self.started or not self._queued_works.empty():
			while self._queued_works.empty():
				time.sleep(1)
			# if self._queued_works.qsize() < min:
			# 	time.sleep(2)
			#start = utils.current_time()
			_list_of_works = self._get_works(num_of_record)
			processed_data, page_har_associated_list = self._prepare_list_of_works(_list_of_works)
			self._update_many_data(processed_data)
			for elem in page_har_associated_list:
				self._associate_page_har_url(elem[0], elem[1])
			self.count_last_insert = len(_list_of_works)
		while self._thread_ads_finder and self._thread_ads_finder.is_alive():
			time.sleep(2)

	def _active_detects_ads(self):
		self._thread_ads_finder = threading.Thread(target=self._find_ads)
		self._thread_ads_finder.start()

	def _find_ads(self):
		ads = AdsExtractor()
		condiction = False
		while self.started or condiction:
			try:
				condiction = False
				candidates = self.select_from_table('har_urls', ['url'], ['checked'], (0,), limit=100)
				#tmp_candidates = curs.execute('SELECT url FROM har_urls WHERE checked=0 LIMIT 20;')
				#candidates = tmp_candidates.fetchall()
				if candidates:
					condiction = True
					candidates = [t[0] for t in candidates]
					result = ads.mark_ads(candidates, '')
					tpls = [(1, int(result[r]), r) for r in result]
					self.update_data('har_urls', ['checked', 'is_advertising'], tpls, ['url'])
			except Exception as e:
				self.last_exception = ' _find_ads: ' + str(e)
			time.sleep(3)

	def _reset_connection(self):
		with self.db_locker:
			self._db_connection.close()
			self._db_connection = sqlite3.connect(self.db_path, detect_types=sqlite3.PARSE_DECLTYPES)

	def _update_many_data(self, tups):
		success = True
		try:
			params = ['scraped', 'attempts_count', 'mime_type', 'http_response_code', 'language', 'url_to_refer', 'generic_text', 'is_webnews', 'title_art', 'text_art', 'publish_date', 'img_art', 'videos_art', 'authors', 'category', 'har', 'error_text']
			self.update_data('pages', params, tups, ['url', 'scraped'])
		except Exception as ex:
			self.last_exception = 'update_many_data: ' + str(ex)
			#self._db_connection.rollback()
			success = False
		return success

	def _insert_links(self, urls):

		urls = list(set(urls))
		tps = list()
		for url in urls:
			is_webnews = Article.is_valid_url(url)
			scheme, cleaned_url = utils.split_url_and_scheme(url)
			tps.append((cleaned_url, scheme, False, 0, is_webnews))
		try:
			self.insert_data('pages', ['url', 'protocol', 'scraped', 'attempts_count', 'is_webnews'], tps)
		except Exception as ex:
			self.last_exception = 'insert_links: ' + str(ex)

	def _process_har(self, har_urls):
		har_ids = None
		try:
			har_ids = self._insert_missing_har_urls(har_urls)
		except Exception as ex:
			self.last_exception = '_process_har: ' + str(ex)
		return har_ids

	def _insert_missing_har_urls(self, urls):
		result = dict()
		if len(urls) > 0:
			custom_condiction = ' WHERE url=?'
			for i in range(1, len(urls)):
				urls[i] = utils.clean_url(urls[i], False)
				custom_condiction += ' or url=? '
			tmp = self.custom_select_from_table('har_urls', ['url', 'id'], custom_condiction, tuple(urls))
			for row in tmp:
				result[row[0]] = row[1]
				urls.remove(row[0])
			if len(urls) > 0:
				urls_to_insert = [(url, 0) for url in urls]
				self.insert_data('har_urls', ['url', 'is_advertising'], urls_to_insert)
				custom_condiction = ' WHERE url=?'
				for i in range(1, len(urls)):
					custom_condiction += ' or url=? '
				tmp = self.custom_select_from_table('har_urls', ['url', 'id'], custom_condiction, tuple(urls))
				for row in tmp:
					result[row[0]] = row[1]
		return result

	# def _insert_har_url(self, url, is_adversing):
	# 	identifier = -1
	# 	with self.db_locker:
	# 		curs = self._db_connection.cursor()
	# 		try:
	# 			result = curs.execute(INSERT_HAR_URL_QUERY, (url, is_adversing))
	# 			if result:
	# 				identifier = result.lastrowid
	# 				self._db_connection.commit()
	# 		except sqlite3.OperationalError as e:
	# 			print('_insert_har_url, url: ' + url + ', errore: ' + str(e))
	# 		finally:
	# 			curs.close()
	# 	return identifier

	def _associate_page_har_url(self, id_page, har_urls):
		tps = list()
		for k in har_urls:
			# value = har_urls[id_har_url]
			tps.append((id_page, har_urls[k]))
		result = self.insert_data('page_har_url_associated', ['id_page', 'id_har_url'], tps)
		return result

	def _get_works(self, count):
		result = list()
		while self._queued_works.qsize() > 0 and len(result) < count:
			try:
				result.append(self._queued_works.get(True, 0.01))
			except queue.Empty as e:
				print(e)
		return result

	def _prepare_list_of_works(self, lst):
		result = list()
		result_2 = list()
		scraped_links = list()
		for work_data_container in lst:
			tup = None
			scheme, url = utils.split_url_and_scheme(work_data_container.url)
			identifier = self._get_page_identifier_(url)
			if identifier == -1:
				self._insert_links([work_data_container.url])
				identifier = self._get_page_identifier_(url)
			pagecontent = work_data_container.page_content_container
			if pagecontent:
				if pagecontent.in_links:
					scraped_links.extend(pagecontent.in_links)
				if pagecontent.har:
					processed_har = self._process_har(pagecontent.har)
					# self._associate_page_har_url(identifier, processed_har)
					result_2.append((identifier, processed_har))
				if pagecontent.article_c:
					tup = self._prepare_tuple_with_article(work_data_container)
				else:
					tup = self._prepare_tuple_without_article(work_data_container)
			else:
				tup = self._prepare_tuple_failed_work(work_data_container)
			result.append(tup)
		self._insert_links(scraped_links)
		return result, result_2

	def _prepare_tuple_failed_work(self, work_data_container):
		url = utils.clean_url(work_data_container.url, False)
		scheme, url = utils.split_url_and_scheme(url)
		scraped_flag = work_data_container.scraped
		attempts_count = work_data_container.attempts_count
		mime_type = work_data_container.mime_type
		response_code = work_data_container.http_response_code
		url_to_refer = work_data_container.url_to_refer
		error_text = work_data_container.error_text
		return scraped_flag, attempts_count, mime_type, response_code, None, url_to_refer, \
			None, False, None, None, None, \
			None, None, None, None, None, error_text, url, 0

	def _prepare_tuple_with_article(self, work_data_container):
		har = None
		url = utils.clean_url(work_data_container.url, False)
		scheme, url = utils.split_url_and_scheme(url)
		scraped_flag = work_data_container.scraped
		attempts_count = work_data_container.attempts_count
		mime_type = work_data_container.mime_type
		response_code = work_data_container.http_response_code
		url_to_refer = work_data_container.url_to_refer
		pagecontent = work_data_container.page_content_container
		art_container = pagecontent.article_c
		videos = ','.join(art_container.videos)
		authors = ','.join(art_container.authors)
		sections = ','.join(art_container.sections)
		publish_date = art_container.publish_date
		if publish_date and isinstance(publish_date, datetime.datetime):
			publish_date = utils.convert_datetime_to_format_str(publish_date)
		return scraped_flag, attempts_count, mime_type, response_code, pagecontent.language, url_to_refer, \
			pagecontent.text, True, art_container.title,\
			art_container.text, publish_date, \
			art_container.top_img, videos, authors, sections, har, None, url, 0

	def	_prepare_tuple_without_article(self, work_data_container):
		har = None
		url = utils.clean_url(work_data_container.url, False)
		scheme, url = utils.split_url_and_scheme(url)
		scraped_flag = work_data_container.scraped
		attempts_count = work_data_container.attempts_count
		mime_type = work_data_container.mime_type
		response_code = work_data_container.http_response_code
		url_to_refer = work_data_container.url_to_refer
		pagecontent = work_data_container.page_content_container
		return scraped_flag, attempts_count, mime_type, \
			response_code, pagecontent.language, url_to_refer, pagecontent.text,\
			False, None, None, None,	None, None, None, None, har, None, url, 0



