import json
import time
from enum import Enum
from io import StringIO

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import UnexpectedAlertPresentException
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.common.keys import Keys
from extraction_tools.ads_extractor import AdsExtractor
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import utils
from browsing_tools.browsing_result import BrowsingResult


class CustomWebBrowser:
	user_agent = "user-agent=Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2228.0 Safari/537.36"
	list_arguments = ["--ssl-protocol=any", '--ignore-certificate-errors', '--ignore-ssl-errors=true', '--mute-audio', '--disable-popup-blocking', '--start-maximized']
	COMMON_FAILED_TEXTS = ['net::ERR_NAME_NOT_RESOLVED', 'net::ERR_CONNECTION_REFUSED', 'net::ERR_TOO_MANY_REDIRECTS', 'net::ERR_CERT_COMMON_NAME_INVALID', 'net::ERR_CONNECTION_RESET', 'net::ERR_ADDRESS_UNREACHABLE']

	headless_arguments = ['--headless']
	# '--disable-gpu',
	# browsermob_proxy_path = "/home/amerigo/tesi/browsermob-proxy/bin/browsermob-proxy"

	def __init__(self, headless=False, logging=False, id_browser=None, ex_path=None, active_adblock_filtering=False):
		self.logs = None
		self.driver = None
		self.headless = headless
		self.removed_blocks = dict()
		self.logging = logging
		self.options = None
		self.capabilities = None
		self.id_browser = id_browser
		self.current_url = None
		self.stopped = False
		self._init_options()
		self.ex_path = ex_path
		self.first_usage = True

	def _init_options(self):
		options = webdriver.ChromeOptions()
		options.add_argument(self.user_agent)
		# options.add_experimental_option("prefs", {"profile.default_content_settings.cookies": 2})
		for s in self.list_arguments:
			options.add_argument(s)
		if self.headless:
			for a in self.headless_arguments:
				options.add_argument(a)
		self.capabilities = DesiredCapabilities.CHROME
		if self.logging:
			self.capabilities['loggingPrefs'] = {'performance': 'ALL'}
		self.capabilities['handlesAlerts'] = False
		self.capabilities['unexpectedAlertBehaviour'] = 'dismiss'
		self.options = options

	def start(self):
		# ex_path = os.path.dirname(os.path.realpath(__file__)) + "/risorse/chromedriver"
		if self.ex_path is None:
			self.ex_path = "/media/amerigo/b76d854a-105f-412d-8e94-38e8af4ce00c/risorse/chromedriver"
		if self.capabilities:
			self.driver = webdriver.Chrome(chrome_options=self.options, desired_capabilities=self.capabilities, executable_path=self.ex_path)
		else:
			self.driver = webdriver.Chrome(chrome_options=self.options, executable_path=self.ex_path)

	def stop(self):
		try:
			self.stopped = True
			self._remove_denied_redirection()
			self.driver.close()
			self.driver.quit()
		except:
			pass

	def download_page(self, starting_url, asynchronous_return_f=None, wait_body=False):
		if self.stopped:
			self.stop()
			print('si sta cercando avviare il download con un webbrowser che dovrebbe ormai risultare chiuso')
		else:
			self.current_url = starting_url
			response = None
			mime_type = None
			canonical_url = None
			html_source = None
			error_text = None
			successful = False
			try:
				self._download(starting_url, wait_body)
				response, mime_type, error_text = self._parse_responses(starting_url)
				canonical_url = self._get_canonical_url()
				if mime_type is not None:
					mime_type = mime_type.lower()
					if mime_type == "text/html":
						self.crossing_page()
						html_source = self.get_html_source()
					successful = True
			except TimeoutException as ex:
				pass
			except Exception as ex:
				pass
				#print('url:' + starting_url + ' ' + str(ex))
			har = self.get_har()
			if self.stopped:
				# print('bloccato contenuto da un webbrowser ormai eliminato')
				self.stop()
			else:
				browsing_res = BrowsingResult(self.id_browser, starting_url, canonical_url, response, mime_type, html_source, self.get_current_url(), har, error_text, successful)
				if asynchronous_return_f is None:
					return browsing_res
				else:
					asynchronous_return_f(browsing_res)

	def _download(self, url, wait_body):
		if not self.first_usage:
			self.open_new_tab()
		self.first_usage = False
		self._reset_logs()
		self._delete_cookie()
		timeout = 10
		try:
			self.driver.set_page_load_timeout(10)
			self.driver.get(url)
			if wait_body:
				WebDriverWait(self.driver, timeout).until(EC.presence_of_element_located((By.TAG_NAME, 'body')))
			else:
				time.sleep(2)
		except TimeoutException as ex1:
			pass
		except UnexpectedAlertPresentException as ex2:
			pass

	def _delete_cookie(self):
		try:
			self.driver.delete_all_cookies()
		except TimeoutException:
			pass

	def open_new_tab(self):
		# current_window_handle = self.driver.current_window_handle
		self._remove_denied_redirection()
		self.driver.execute_script("window.open('');")
		self.driver.close()
		self.driver.switch_to_window(self.driver.window_handles[0])

	def crossing_page(self):
		try:
			# self._stop_loading()
			self._scroll_down(0.2, 1)
			# self._stop_loading()
		except UnexpectedAlertPresentException:
			pass

	def get_current_url(self):
		canonical_url = self._get_canonical_url()
		if canonical_url:
			result = canonical_url
		else:
			result = self.current_url
		return result

	def render_page_from_html_string(self, html_string):
		self.driver.set_page_load_timeout(2)
		try:
			self.driver.get("data:text/html;charset=utf-8," + html_string)
		except TimeoutException:
			pass

	def get_har(self, remove_domain_request=True, domains_to_remove={'facebook.com', 'facebook.it', 'youtube.it', 'youtube.com', 'twitter.it', 'twitter.com'}, file_type_to_remove={'jpg', 'png', 'jpeg'}):
		result = list()
		if self.logging and self.logs:
			domain = None
			if remove_domain_request:
				domain = utils.get_domain(self.current_url)
			for log in self.logs:
				message = json.load(StringIO(log['message']))['message']
				if 'method' in message:
					method = message['method']
					if method and method == 'Network.responseReceived':
						url = message['params']['response']['url']
						if utils.is_valid_url(url):
							to_insert = (domain and not utils.is_domain_link(url, domain)) or domain is None
							to_insert = to_insert and utils.get_filetype_from_url(url) not in file_type_to_remove
							if to_insert:
								for d in domains_to_remove:
									if utils.is_domain_link(url, d):
										to_insert = False
										break
								if to_insert:
									result.append(url)

		result = list(set(result))
		#print('har len: ' + str(len(result)))
		return result

	def get_html_source(self):
		# html = self.driver.page_source
		html = self.driver.execute_script("return document.documentElement.outerHTML")
		return html

	def _get_canonical_url(self):
		result = None
		try:
			tmp_res = self.driver.find_element_by_xpath('//link[@rel="canonical" and @href]')
			if tmp_res:
				href = tmp_res.get_attribute("href")
				if href:
					# domain = utils.get_principal_domain(self.current_url)
					result = href
		except NoSuchElementException:
			pass
		except TimeoutException:
			pass
		except Exception:
			pass
		if result is None:
			try:
				tmp_res = self.driver.find_element_by_xpath('//meta[@property="og:url"]|//meta[@name="twitter:url"]')
				result = tmp_res.get_attribute('content')
			except NoSuchElementException:
				pass
			except TimeoutException:
				pass
			except Exception:
				pass
		if result:
			result = utils.clean_url(result, False)
			tmp = utils.clean_url(self.current_url, False)
			scheme, u = utils.split_url_and_scheme(tmp)
			if result.startswith(r'//'):
				result = '{}:{}'.format(scheme, result)
			elif result.startswith(r'/'):
				domain = '{}://{}'.format(scheme, utils.get_principal_domain_www(tmp))
				result = '{}{}'.format(domain, result)
			if not utils.is_valid_url_to_navigate(result):
				result = None
		return result

	def _denies_redirection(self):
		result = False
		try:
			self._get_focus_on_body()
			self.driver.execute_script('window.onbeforeunload = function(e) { return "nothing";};')
			result = True
		except TimeoutException:
			pass
		except UnexpectedAlertPresentException:
			pass
		return result

	def _remove_denied_redirection(self):
		result = False
		try:
			self._get_focus_on_body()
			self.driver.execute_script('window.onbeforeunload = null;')
			result = True
		except TimeoutException:
			pass
		except UnexpectedAlertPresentException:
			pass
		return result

	def _get_focus_on_body(self):
		elements = self.driver.find_elements_by_tag_name('body')
		if len(elements) > 0:
			elements[0].send_keys(Keys.ENTER)

	def _stop_loading(self):
		elements = self.driver.find_elements_by_tag_name('body')
		if len(elements) > 0:
			elements[0].send_keys(Keys.ESCAPE)
		# self.driver.execute_script('window.stop();')

	def _get_page_height(self):
		return self.driver.execute_script("return document.body.scrollHeight")

	def _scroll_down(self, time_to_wait, attempts, max_height=6000):
		try:
			last_height = self._get_page_height()
			if last_height < max_height:
				self._denies_redirection()
				count = 0
				while count < attempts and last_height < max_height:
					try:
						self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
						time.sleep(time_to_wait)
						new_height = self._get_page_height()
					except UnexpectedAlertPresentException:
						new_height = self._get_page_height()
					if new_height == last_height:
						count = attempts
					else:
						last_height = new_height
						count += 1
				time.sleep(1)
		except UnexpectedAlertPresentException:
			pass
		except TimeoutException:
			pass
		finally:
			self._remove_denied_redirection()

	def _load_logs(self):
		self.logs = self.driver.get_log('performance')

	def _reset_logs(self):
		try:
			self.logs = None
			self.driver.get_log('performance')
		except TimeoutException:
			pass

	def _parse_responses(self, starting_url):
		result = None
		success = False
		while not success:
			try:
				result = self._get_response(starting_url)
				success = True
			except UnexpectedAlertPresentException:
				success = False
		return result

	def _get_response(self, starting_url):
		result = None
		redirection_result = None
		mime_type = None
		error_text = None
		if self.logging:
			self._load_logs()
			redirection_result, final_url = self._check_redirection(starting_url)
			self.current_url = final_url or self.current_url
			request_id = self._get_request_id_from_log()
			for log in self.logs:
				message = json.load(StringIO(log['message']))['message']
				if 'method' in message:
					method = message['method']
					if method and method == 'Network.responseReceived':
						params = message['params']
						response = params['response']
						message_url = response['url']
						if final_url:
							url_to_compare = final_url
						else:
							url_to_compare = starting_url
						if '#' in url_to_compare:
							url_to_compare = url_to_compare[:url_to_compare.find('#')]
						if utils.are_equals_urls(message_url, url_to_compare):
							response_code = response['status']
							mime_type = response['mimeType']
							result = HttpResponse.parse_response(response_code)
							break
					elif method and method == 'Network.loadingFailed':
						params = message['params']
						if 'requestId' in params and params['requestId'] == request_id:
							failed_text = params['errorText']
							if failed_text in self.COMMON_FAILED_TEXTS:
								result = HttpResponse.NOT_FOUND
								error_text = failed_text
								break
							elif failed_text in ('net::ERR_ABORTED'):
								result = None
								break
							else:
								print('failed loading: %s \n url:%s' % (failed_text, self.current_url))
								break
			if redirection_result and (result == HttpResponse.OK_RESPONSE or result is None):
				result = redirection_result
		return result, mime_type, error_text

	def _get_request_id_from_log(self):
		result = None
		for log in self.logs:
			message = json.load(StringIO(log['message']))['message']
			if 'method' in message:
				method = message['method']
				if method and method == 'Network.requestWillBeSent':
					params = message['params']
					if 'documentURL' in params:
						doc_url = params['documentURL']
						if utils.are_equals_urls(doc_url, self.current_url):
							result = params['loaderId']
							break
		return result

	def _check_redirection(self, starting_url):
		result = None
		final_url = None
		for log in self.logs:
			message = json.load(StringIO(log['message']))['message']
			if 'method' in message:
				method = message['method']
				if method and method == 'Network.requestWillBeSent':
					params = message['params']
					if 'redirectResponse' in params:
						response = params['redirectResponse']
						response_url = response['url']
						if utils.are_equals_urls(response_url, starting_url):
							response_code = response['status']
							headers = response['headers']
							if 'location' in headers:
								final_url = headers['location']
							else:
								final_url = headers['Location']
							result = HttpResponse.parse_response(response_code)
							break
		if result is None:
			if utils.is_valid_url_to_navigate(self.driver.current_url):
				if not utils.are_equals_urls(starting_url, self.driver.current_url):
					result = HttpResponse.REDIRECTION_RESPONSE
					final_url = self.driver.current_url
		elif utils.are_equals_urls(starting_url, final_url):
			final_url = self.driver.current_url
		return result, final_url

	# questo metodo verifica che non ci siano div sovrapposti al corpo vero e proprio della pagina. Tali div vengono rimossi dal corpo della pagina
	def _check_div_popup(self):
		start = utils.current_time()
		body = self.driver.find_elements_by_tag_name('body')[0]
		body_height = body.size['height']
		body_width = body.size['width']
		try:
			# body_z_index = body.value_of_css_property('z-index')
			div_list = self.driver.find_element_by_xpath("//div[@position='fixed']")
			count = 0
			for div in div_list:
				div_height = div.size['height']
				div_width = div.size['width']
				if div.is_displayed() and div_width != 0 and div_height != 0:
					if (body_height / div_height) < 1.1 and (body_width / div_width) < 1.1:
						# all_children = div.find_elements_by_xpath(".//*")
						self.driver.execute_script("var element = arguments[0];element.parentNode.removeChild(element);", div)
						# self.removed_blocks[str(count)] = (div, all_children)
						count += 1
		except NoSuchElementException:
			pass
			#print('nessun elemento trovato')
		elapsed = utils.current_time() - start
		print("elapsed time: " + str(elapsed))


class HttpResponse(Enum):
	OK_RESPONSE = 200

	MULTIPLE_CHOICE_RESPONSE = 300
	REDIRECTION_RESPONSE = 333
	MOVED_PERMANENTLY_RESPONSE = 301

	BAD_REQUEST_RESPONSE = 400
	UNAUTHORIZED_RESPONSE = 401
	FORBIDDEN_RESPONSE = 403
	NOT_FOUND = 404
	GENERIC_CLIENT_ERROR = 402

	SERVER_ERROR_RESPONSE = 500



	@staticmethod
	def parse_response(response_code):
		result = None
		try:
			result = HttpResponse(response_code)
		except:
			pass
		if result:
			return result
		if response_code in (201, 202, 203, 204, 205, 206, 207):
			result = HttpResponse.OK_RESPONSE
		elif response_code in (302, 303, 304, 305, 306, 307, 308):
			result = HttpResponse.REDIRECTION_RESPONSE
		elif response_code in (405, 406, 407, 408, 409, 410, 411, 412, 413, 414, 415, 416, 417, 418, 420, 422, 426, 449, 451):
			result = HttpResponse.GENERIC_CLIENT_ERROR
		elif response_code in (501, 502, 503, 504, 505, 509):
			result = HttpResponse.SERVER_ERROR_RESPONSE
		return result
