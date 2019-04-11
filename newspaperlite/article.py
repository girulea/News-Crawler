import copy

from .articlecontainer import ArticleContainer
from .extractors import ContentExtractor
from .images import Scraper
from .newsurl import is_news_url
from .outputformatters import OutputFormatter
from .videos import VideoExtractor
import utils
MIN_WORD_COUNT = 300  # num of word tokens in text
MIN_SENT_COUNT = 7  # num of sentence tokens
MAX_TITLE = 200  # num of chars
MAX_TEXT = 100000  # num of chars
MAX_KEYWORDS = 35  # num of strings in list
MAX_AUTHORS = 10  # num strings in list
MAX_SUMMARY = 5000  # num of chars
MAX_SUMMARY_SENT = 5  # num of sentences



class Article(object):

	def __init__(self, html_tree, url, language=None, title_art=None, publish_date=None, img_art=None, videos_art='', authors='', category='', remove_detected_block=True, domain_videos_path=None):

		self.extractor = ContentExtractor(remove_detected_block)
		self.url = url
		self.domain_videos_path = domain_videos_path
		self.title = title_art

		# URL of the "best image" to represent this article
		self.top_img = self.top_image = img_art

		# stores image provided by metadata
		self.meta_img = ''

		# All image urls in this article
		self.imgs = self.images = []

		if category:
			self.sections = category.split(',')
		else:
			self.sections = []

		# All videos in this article: youtube, vimeo, etc
		if videos_art:
			self.movies = videos_art.split(',')
		else:
			self.movies = []

		# Body text from this article
		self.text = ''

		# `keywords` are extracted via nlp() from the body text
		self.keywords = []

		# `meta_keywords` are extracted via parse() from <meta> tags
		self.meta_keywords = []

		# `tags` are also extracted via parse() from <meta> tags
		self.tags = set()

		# List of authors who have published the article, via parse()
		if authors:
			self.authors = authors.split(',')
		else:
			self.authors = []

		self.publish_date = publish_date

		# Summary generated from the article's body txt
		self.summary = ''

		# This article's unchanged and raw HTML
		self.html = ''

		# The HTML of this article's main node (most important part)
		self.article_html = ''

		# Meta description field in the HTML source
		self.meta_description = ""

		# Meta language field in HTML source
		self.meta_lang = None
		self.set_meta_language(language)

		# Meta favicon field in HTML source
		self.meta_favicon = ""

		# Meta tags contain a lot of structured data, e.g. OpenGraph
		self.meta_data = {}

		# The canonical link of this article if found in the meta data
		self.canonical_link = ""

		# Holds the top element of the DOM that we determine is a candidate
		# for the main body of the article
		self.top_node = None

		# A deepcopied clone of the above object before heavy parsing
		# operations, useful for users to query data in the
		# "most important part of the page"
		self.clean_top_node = None

		# lxml DOM object generated from HTML
		self.html_tree = html_tree

		# A deepcopied clone of the above object before undergoing heavy
		# cleaning operations, serves as an API if users need to query the DOM
		self.clean_html_tree = None

		self.output_formatter = OutputFormatter()
		# A property dict for users to store custom data.
		self.additional_data = {}

	def parse(self, detect_language_from_text=True):
		#self.doc = self.config.get_parser().fromstring(self.html)
		self.clean_html_tree = copy.deepcopy(self.html_tree)

		title = self.extractor.get_title(self.clean_html_tree)
		if not self.title and title:
			self.set_title(title)

		authors = self.extractor.get_authors(self.clean_html_tree)
		self.set_authors(authors)
		detected_lang = None
		if title and self.meta_lang is None:
			detected_lang = utils.detect_language_from_text(title)

		if detected_lang and self.extractor.update_language(detected_lang):
			self.set_meta_language(detected_lang)

		if self.meta_lang and self.extractor.update_language(self.meta_lang):
			self.output_formatter.update_language(self.meta_lang)

		meta_favicon = self.extractor.get_favicon(self.clean_html_tree)
		self.set_meta_favicon(meta_favicon)

		meta_description = self.extractor.get_meta_description(self.clean_html_tree)
		self.set_meta_description(meta_description)

		canonical_link = self.extractor.get_canonical_link(	self.url, self.clean_html_tree)
		self.set_canonical_link(canonical_link)

		tags = self.extractor.extract_tags(self.clean_html_tree)
		self.set_tags(tags)

		meta_keywords = self.extractor.get_meta_keywords(
			self.clean_html_tree)
		self.set_meta_keywords(meta_keywords)

		meta_data = self.extractor.get_meta_data(self.clean_html_tree)
		self.set_meta_data(meta_data)
		if not self.publish_date:
			self.publish_date = self.extractor.get_publishing_date(self.url, self.clean_html_tree)

		self.top_node = self.extractor.calculate_best_node(self.html_tree)
		if self.top_node is not None:
			video_extractor = VideoExtractor(self.top_node, self.url, self.domain_videos_path)
			self.set_movies(video_extractor.get_videos())

			self.top_node = self.extractor.post_cleanup(self.top_node)
			self.clean_top_node = copy.deepcopy(self.top_node)

			text, article_html = self.output_formatter.get_formatted(self.clean_top_node)
			self.set_article_html(article_html)
			self.set_text(text)
		self.fetch_top_image()
		self.sections.extend(self.extractor.get_sections(self.clean_html_tree))
		result = ArticleContainer(title=self.title, language=self.meta_lang, top_img=self.top_img, url=self.url, text=self.text, publish_date=self.publish_date, authors=self.authors, videos=self.movies, sections=self.sections)
		return result

	def fetch_top_image(self):
		if self.clean_html_tree is not None:
			meta_img_url = self.extractor.get_meta_img_url(self.url, self.clean_html_tree)
			self.set_meta_img(meta_img_url)

		if self.clean_top_node is not None and not self.has_top_image():
			first_img = self.extractor.get_first_img_url(self.url, self.clean_top_node)
			self.set_top_img(first_img)

		if not self.has_top_image():
			self.set_reddit_top_img()

	def has_top_image(self):
		return self.top_img is not None and self.top_image != ''

	@staticmethod
	def is_valid_url(url):
		"""Performs a check on the url of this link to determine if article
		is a real news article or not
		"""
		return is_news_url(url)

	def is_valid_body(self):
		"""If the article's body text is long enough to meet
		standard article requirements, keep the article
		"""
		meta_type = self.extractor.get_meta_type(self.clean_html_tree)
		wordcount = self.text.split(' ')
		sentcount = self.text.split('.')

		if meta_type == 'article' and len(wordcount) >	(MIN_WORD_COUNT):
			return True

		if not self.is_media_news() and not self.text:
			return False

		if self.title is None or len(self.title.split(' ')) < 2:
			return False

		if len(wordcount) < MIN_WORD_COUNT:
			return False

		if len(sentcount) < MIN_SENT_COUNT:
			return False

		if self.html is None or self.html == '':
			return False

		return True

	def is_media_news(self):
		"""If the article is related heavily to media:
		gallery, video, big pictures, etc
		"""
		safe_urls = ['/video', '/slide', '/gallery', '/powerpoint',
					 '/fashion', '/glamour', '/cloth']
		for s in safe_urls:
			if s in self.url:
				return True
		return False


	def set_reddit_top_img(self):
		"""Wrapper for setting images. Queries known image attributes
		first, then uses Reddit's image algorithm as a fallback.
		"""
		try:
			s = Scraper(self)
			self.set_top_img(s.largest_image_url())
		except TypeError as e:
			print(e)

	def set_title(self, input_title):
		if input_title:
			self.title = input_title[:]

	def set_text(self, text):
		text = text[:]
		if text:
			self.text = text


	def set_article_html(self, article_html):
		"""Sets the HTML of just the article's `top_node`
		"""
		if article_html:
			self.article_html = article_html

	def set_meta_img(self, src_url):
		self.meta_img = src_url
		self.set_top_img_no_check(src_url)

	def set_top_img(self, src_url):
		if src_url is not None:
			s = Scraper(self)
			if s.satisfies_requirements(src_url):
				self.set_top_img_no_check(src_url)

	def set_top_img_no_check(self, src_url):
		"""Provide 2 APIs for images. One at "top_img", "imgs"
		and one at "top_image", "images"
		"""
		self.top_img = src_url
		self.top_image = src_url

	def set_imgs(self, imgs):
		"""The motive for this method is the same as above, provide APIs
		for both `article.imgs` and `article.images`
		"""
		self.images = imgs
		self.imgs = imgs


	def set_keywords(self, keywords):
		"""Keys are stored in list format
		"""
		if not isinstance(keywords, list):
			raise Exception("Keyword input must be list!")
		if keywords:
			self.keywords = keywords[:]

	def set_authors(self, authors):
		"""Authors are in ["firstName lastName", "firstName lastName"] format
		"""
		if not isinstance(authors, list):
			raise Exception("authors input must be list!")
		if authors:
			self.authors = authors[:]

	def set_summary(self, summary):
		"""Summary here refers to a paragraph of text from the
		title text and body text
		"""
		self.summary = summary[:]

	def set_meta_language(self, meta_lang):
		"""Save langauges in their ISO 2-character form
		"""
		if meta_lang and len(meta_lang) >= 2:
			self.meta_lang = meta_lang[:2].lower()

	def set_meta_keywords(self, meta_keywords):
		"""Store the keys in list form
		"""
		self.meta_keywords = [k.strip() for k in meta_keywords.split(',')]

	def set_meta_favicon(self, meta_favicon):
		self.meta_favicon = meta_favicon

	def set_meta_description(self, meta_description):
		self.meta_description = meta_description

	def set_meta_data(self, meta_data):
		self.meta_data = meta_data

	def set_canonical_link(self, canonical_link):
		self.canonical_link = canonical_link

	def set_tags(self, tags):
		self.tags = tags

	def set_movies(self, movie_objects):
		"""Trim video objects into just urls
		"""
		movie_urls = [o.src for o in movie_objects if o and o.src]
		self.movies = movie_urls

