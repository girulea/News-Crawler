import re2 as re
from urllib.parse import urlparse

import tldextract

ALLOWED_TYPES = ['html', 'htm', 'md', 'rst', 'aspx', 'jsp', 'rhtml', 'cgi',
				 'xhtml', 'jhtml', 'asp', 'shtml']

GOOD_PATHS = ['story', 'article', 'feature', 'featured', 'slides',
			  'slideshow', 'gallery', 'news', 'video', 'media',
			  'v', 'radio', 'press']

BAD_CHUNKS = ['careers', 'contact', 'about', 'faq', 'terms', 'privacy',
			  'advert', 'preferences', 'feedback', 'info', 'browse', 'howto',
			  'account', 'subscribe', 'donate', 'shop', 'admin', 'cookies', 'disclaimer']

BAD_DOMAINS = ['amazon', 'doubleclick', 'twitter', 'shop']

_STRICT_DATE_REGEX_PREFIX = r'(?<=\W)'

DATE_REGEX = r'([\./\-_]{0,1}(19|20)\d{2})[\./\-_]{0,1}(([0-3]{0,1}[0-9][\./\-_])|(\w{3,5}[\./\-_]))([0-3]{0,1}[0-9][\./\-]{0,1})?'

STRICT_DATE_REGEX = _STRICT_DATE_REGEX_PREFIX + DATE_REGEX


def is_news_url(url):
	path = urlparse(url).path
	if not path.startswith('/'):
		return False

	if path.endswith('/'):
		path = path[:-1]

	# '/story/cnn/blahblah/index.html' --> ['story', 'cnn', 'blahblah', 'index.html']
	path_tokens = [x for x in path.split('/') if len(x) > 0]

	# siphon out the file type. eg: .html, .htm, .md
	if len(path_tokens) > 0:
		file_type = url_to_filetype(url)

		# if the file type is a media type, reject instantly
		if file_type and file_type not in ALLOWED_TYPES:
			return False

		last_token = path_tokens[-1].split('.')
		# the file type is not of use to use anymore, remove from url
		if len(last_token) > 1:
			path_tokens[-1] = last_token[-2]

	# Index gives us no information
	if 'index' in path_tokens:
		path_tokens.remove('index')

	# extract the tld (top level domain)
	tld_dat = tldextract.extract(url)
	subd = tld_dat.subdomain
	tld = tld_dat.domain.lower()

	url_slug = path_tokens[-1] if path_tokens else ''

	if tld in BAD_DOMAINS:
		return False

	if len(path_tokens) == 0:
		dash_count, underscore_count = 0, 0
	else:
		dash_count = url_slug.count('-')
		underscore_count = url_slug.count('_')

	# If the url has a news slug title
	if url_slug and (dash_count > 4 or underscore_count > 4):

		if dash_count >= underscore_count:
			if tld not in [x.lower() for x in url_slug.split('-')]:
				return True

		if underscore_count > dash_count:
			if tld not in [x.lower() for x in url_slug.split('_')]:
				return True

	# There must be at least 2 subpaths
	if len(path_tokens) <= 1:
		return False

	# Check for subdomain & path red flags
	# Eg: http://cnn.com/careers.html or careers.cnn.com --> BAD
	for b in BAD_CHUNKS:
		if b in path_tokens or b == subd:
			return False

	match_date = re.search(DATE_REGEX, url)

	# if we caught the verified date above, it's an article
	if match_date is not None:
		return True

	for GOOD in GOOD_PATHS:
		if GOOD.lower() in [p.lower() for p in path_tokens]:
			return True

	return False

def url_to_filetype(abs_url):
	"""
	Input a URL and output the filetype of the file
	specified by the url. Returns None for no filetype.
	'http://blahblah/images/car.jpg' -> 'jpg'
	'http://yahoo.com'               -> None
	"""
	path = urlparse(abs_url).path
	# Eliminate the trailing '/', we are extracting the file
	if path.endswith('/'):
		path = path[:-1]
	path_chunks = [x for x in path.split('/') if len(x) > 0]
	last_chunk = path_chunks[-1].split('.')  # last chunk == file usually
	if len(last_chunk) < 2:
		return None
	file_type = last_chunk[-1]
	# Assume that file extension is maximum 5 characters long
	if len(file_type) <= 5 or file_type.lower() in ALLOWED_TYPES:
		return file_type.lower()
	return None