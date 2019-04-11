# -*- coding: utf-8 -*-
import os
import random
import re2 as re
import urllib
import urllib.request
from urllib.parse import urlparse
from dateutil.parser import parse as date_parser
import tldextract
import validators
import time
from langdetect import detect
from textblob import TextBlob

LIST_OF_IMPORTANT_TAG = [
		'div', 'table', 'tr', 'td', 'ul', 'article', 'tbody', 'section', 'nav', 'footer', 'iframe', 'header', 'body', 'html', 'head']

ALLOWED_TYPES_TO_NAVIGATE = ['html', 'htm', 'md', 'rst', 'aspx', 'jsp', 'rhtml', 'cgi', 'xhtml', 'jhtml', 'asp', 'php', 'shtml', 'xml']

BAD_TOKENS = ['careers', 'contact', 'about', 'faq', 'terms', 'privacy', 'forum',
			  'advert', 'preferences', 'feedback', 'info', 'browse', 'howto', 'search',
			  'account', 'subscribe', 'donate', 'shop', 'admin', 'cookies', 'disclaimer', 'coupon', 'clickenc', 'clickhere', 'css', 'meteo']
# def is_structurally_important(tag):
# 	if tag in _LIST_OF_IMPORTANT_TAG:
# 		result = True
# 	else:
# 		result = False
# 	return result


def new_random_id(length=5):
	result = "tmp_id"
	for i in range(0, length):
		result += str(random.randint(0, 9))
	return result


def get_principal_domain(url): # estrae da un url il dominio "principale"; es: www.xxxxx.xx.it
	if not isinstance(url, str):
		url = str(url)
		url = urllib.parse.unquote(url)
	result = urlparse(url).hostname
	if result:
		result = re.sub('^(www\d?.)', '', result)
	return result


def get_principal_domain_www(url): # estrae da un url il dominio "principale"; es: www.xxxxx.xx.it
	result = urlparse(url).hostname
	return result


def get_domain(abs_url, **kwargs):
	if abs_url is None:
		return None
	return urlparse(abs_url, **kwargs).netloc


def get_scheme(abs_url, **kwargs):
	if abs_url is None:
		return None
	return urlparse(abs_url, **kwargs).scheme


def get_path(abs_url, **kwargs):
	"""
	"""
	if abs_url is None:
		return None
	return urlparse(abs_url, **kwargs).path


def is_valid_url(url):
	result = False
	if url and validators.url(url, public=True):
		result = True
	return result


def is_valid_url_to_navigate(url):
	tld_dat = tldextract.extract(url)
	sub_domain = tld_dat.subdomain
	result = is_valid_url(url)
	file_type = None
	match = re.match('https?://mailto', url)
	if match:
		result = False
	if result:
		url_parsed = urlparse(url)
		query = url_parsed.query
		if result and query:
			query = query.lower()
			match_query = re.match('share=|e?mail=', query)
			if match_query:
				result = False
		if result:
			file_type = get_filetype_from_url(url)
			if file_type is None or file_type in ALLOWED_TYPES_TO_NAVIGATE:
				result = True
			else:
				result = False
		if result:
			path = url_parsed.path
			path = path.lower()
			if path.endswith('/'):
				path = path[:-1]
			tokens = path.split('/')
			if file_type:
				tokens[-1] = tokens[-1].replace('.' + file_type, '')
			if sub_domain:
				sub_domain = sub_domain.lower()
			for b in BAD_TOKENS:
				if b in tokens or (sub_domain and b == sub_domain):
					result = False
					break
	return result


def clean_url(url, remove_arguments=True, domain=None, scheme=None):
	result = urllib.parse.unquote(url)
	# if '#' in result:
	# 	i = result.find('#')
	# 	result = result[:i]
	if domain or remove_arguments:
		if '?' in result:
			i = result.find('?')
			if domain:
				result1 = result[:i]
				result2 = result[i+1:]
				if domain in result1 and remove_arguments:
					result = result1
				elif domain in result2:
					res_split = result2.split('=')
					for r in res_split:
						if domain in r:
							result = r
							if '&' in result:
								i = result.find('&')
								result = result[:i]
							break
			else:
				result = result[:i]
	if scheme:
		if not re.match('https?://', result):
			result = scheme + '://' + result
	result = re.sub(' ', '', result)
	if result.endswith('/'):
		result = result[:-1]
	return result


def is_domain_link1(url, domain):
	return get_domain(url) == domain


def is_domain_link(url, domain):
	result = False
	if domain in url:
		if '?' in url:
			i_1 = url.find('?')
			i_2 = url.find(domain) + len(domain)
			if i_2 < i_1:
				result = True
		elif ';' in url:
			i_1 = url.find(';')
			i_2 = url.find(domain) + len(domain)
			if i_2 < i_1:
				result = True
		elif '{' in url:
			i_1 = url.find('{')
			i_2 = url.find(domain) + len(domain)
			if i_2 < i_1:
				result = True
		elif '=' in url:
			i_1 = url.find('=')
			i_2 = url.find(domain) + len(domain)
			if i_2 < i_1:
				result = True
		else:
			result = True
	return result


def get_filetype_from_url(url):
	path = urlparse(url).path
	if path.endswith('/'):
		path = path[:-1]
	path_chunks = [x for x in path.split('/') if len(x) > 0]
	if len(path_chunks) > 0:
		last_chunk = path_chunks[-1].split('.')  # last chunk == file usually
		if len(last_chunk) < 2:
			return None
		file_type = last_chunk[-1]
		if len(file_type) <= 5:
			return file_type.lower()
	return None


def read_text_file_as_array(filename):
	with open(filename, 'r') as f:
		result = [s for s in f.read().split('\n') if s]
	return result


def are_equals_urls(url1, url2):
	result = False
	url1 = urllib.parse.unquote(url1)
	url2 = urllib.parse.unquote(url2)
	url1 = re.sub("^(https?://(www.)?)", "", url1)
	url1 = re.sub(' ', '', url1)
	url2 = re.sub("^(https?://(www.)?)", "", url2)
	url2 = re.sub(' ', '', url2)
	if url1.endswith('/'):
		url1 = url1[0:-1]
	if url2.endswith('/'):
		url2 = url2[0:-1]
	if url1 == url2:
		result = True
	return result


def get_db_name_from_url(url):
	domain = get_domain(url)
	result = re.sub('\.', '_', domain)

	# url = url.encode('utf-8', 'replace')
	# result = hashlib.md5(url).hexdigest()
	return result + '.db'


def create_directory(relative_path):
	if not os.path.exists(relative_path):
		os.makedirs(relative_path)
		return True
	return False


def get_week_days(language):
	if language in ('it', 'IT', 'it-IT'):
		return ['lunedi', 'lunedì', 'lun', 'martedi', 'martedì', 'mar', 'mercoledi', 'mercoledì', 'mer', 'giovedi', 'giovedì', 'gio', 'venerdi', 'venerdì', 'ven', 'sabato', 'sab', 'domenica', 'dom']
	else:
		return None


def get_year_moths_dict(language):
	if language in ('it', 'IT', 'it-IT'):
		return {'gennaio': 1, 'gen': 1, 'febbraio': 2, 'feb': 2, 'marzo': 3, 'mar': 3, 'aprile': 4, 'apr': 4, 'maggio': 5,
				'mag': 5, 'giugno': 6, 'giu': 6, 'luglio': 7, 'lug': 7, 'agosto': 8, 'ago': 8, 'settembre': 9, 'set': 9,
				'ottobre': 10, 'ott': 10, 'novembre': 11, 'nov': 11, 'dicembre': 12, 'dic': 12}
	else:
		return None


def get_final_url(url):
	result = url
	try:
		response = urllib.request.urlopen(url)
		result = response.geturl()  # 'http://stackoverflow.com/'
	except Exception:
		pass
	return result


def current_time():
	return time.time()


def get_attr_dinamically(obj, attr):
	result = None
	try:
		result = getattr(obj, attr)
	except AttributeError:
		pass
	return result


def get_date_from_string_by_language(txt, language):
	result = None
	week_days = get_week_days(language)
	year_months_dict = get_year_moths_dict(language)
	if week_days and year_months_dict:
		rgx = '(%s)?\s{1,3}(\d\d)\s{1,3}(%s)\s{1,3}(\d\d(?:\d\d))?' % ('|'.join(week_days), '|'.join(year_months_dict.keys()))
		date_match = re.search(rgx, txt, re.IGNORECASE)
		if date_match:
			day = date_match.group(2)
			month = year_months_dict[date_match.group(3).lower()]
			year = date_match.group(4)
			date_str = '%s-%s-%s' % (year, month, day)
			datetime_obj = parse_date_str(date_str)
			if datetime_obj:
				result = datetime_obj
	return result


def parse_date_str(date_str):
	result = None
	if date_str:
		try:
			result = date_parser(date_str)
		except (ValueError, OverflowError, AttributeError, TypeError):
			# near all parse failures are due to URL dates without a day
			# specifier, e.g. /2014/04/
			result = None
	return result


def detect_language_from_text(text):
	result = None
	try:
		# b = TextBlob(text)
		# result = b.detect_language()
		result = detect(text)
	except Exception:
		pass
	return result


def get_current_time_form(pattern='%Y-%m-%d %H:%M:%S'):
	return time.strftime(pattern, time.gmtime())


def convert_datetime_to_format_str(datetime_obj, pattern='%Y-%m-%d %H:%M:%S'):
	result = None
	if datetime_obj and pattern:
		result = datetime_obj.strftime(pattern)
	return result


import datetime
def get_current_time():
	return datetime.datetime.now()


def split_url_and_scheme(url):
	cleaned_url = clean_url(url, False)
	scheme = get_scheme(cleaned_url)
	if scheme:
		scheme = scheme + '://'
		cleaned_url = cleaned_url.replace(scheme, '', 1)
	return scheme, cleaned_url


def get_free_memory():
	"""
	Get node total memory and memory usage
	"""
	with open('/proc/meminfo', 'r') as mem:
		ret = {}
		tmp = 0
		for i in mem:
			sline = i.split()
			if str(sline[0]) == 'MemTotal:':
				ret['total'] = int(sline[1])
			elif str(sline[0]) in ('MemFree:', 'Buffers:', 'Cached:'):
				tmp += int(sline[1])
		ret['free'] = tmp
		ret['used'] = int(ret['total']) - int(ret['free'])
	return int(ret['free'])


def wait_free_memory(min_m1, min_m2):
	free_memory = get_free_memory()
	if free_memory < min_m1:
		while free_memory < min_m2:
			time.sleep(5)
			free_memory = get_free_memory()


def extract_domain_name_from_db(file_):
	domain_name = file_[file_.rfind('/') + 1:]
	domain_name = domain_name.replace('_', '.')
	domain_name = re.sub('^(www\d?\.)', '', domain_name)
	domain_name = domain_name.replace('.db', '')
	# domain_name = domain_name.replace('.it', '')
	# domain_name = domain_name.replace('.com', '')
	# domain_name = domain_name.replace('.org', '')
	return domain_name