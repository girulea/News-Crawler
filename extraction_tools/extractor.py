import copy

import lxml.html
import xpath2_functions
import utils
from extraction_tools.explorer import TreeExplorer
from extraction_tools.navigationcontenthunter import NavigationContentHunter
from newspaperlite import Article
from extraction_tools.pagecontentcontainer import PageContentContainer

_structurally_insignificant = 'structurallyins'
_structurally_important = 'structurallyimp'
_flag_anchor_count = '_qh_'
_flag_tag_count = '_qt_'
_flag_text_length_anchor = '_lh_'
_flag_text_length_tag = '_lt_'
_flag_backup_tag = '_back_tag_'
_namespace_regex = "http://exslt.org/regular-expressions"
_node_to_remove_re = ["cookie", "retweet", "menucontainer", "disclaimer",
					"utility-bar", "inline-share-tools", "nav-bar", "tags", "socialnetworking", "pagetools", "share-link",
					"comments", "sharebar", 'ads_content', 'ads-content',
					"post-attributes", "communitypromo", "box-meteo", "fb-page",
					"runaroundLeft", "subscribe", "vcard", "footer", "author-dropdown", "socialtools",
					"menu", "utility", "top-bar", "adsbygoogle", "relatedpost", "related-post", 'advn_zone']

_tag_text_formatting = ['b', 'strong', 'i', 'em', 'mark', 'small', 'del', 'ins', 'sub', 'sup']
class ContentExtractor:
	def __init__(self):
		self._backup_html_tree = None
		self._tree_explorer = TreeExplorer
		self.article = None
		self.domain = None
		self.scheme = None
		self._html_source = None
		self._domain_urls = None
		self._outbound_links = None
		self._url = None
		self.language = None
		self.body_node = None
		self._is_news = False
		self._blocks_to_remove = list()
		self._notes_on_descent = dict()
		self.blocks_to_not_remove_xpath = ".//article|.//*[@id='article']|.//*[@itemprop='articleBody']|//*[@id and contains(@id, 'main-con')]|//*[@class and contains(@class, 'main-con')]"
		self.blocks_to_not_remove_tag = ['video', 'script', 'style', 'article']
		self.protect_parent = ['article', 'head', 'video', 'script', 'style', 'html', 'body']
		self._parser = lxml.html.HTMLParser(remove_comments=True)

	# effettua le prime operazioni necessarie a inizializzare gli oggetti della classe
	def prepare_html_tree(self, url, domain, html=None, store_script=False, store_style=False, store_urls=True):
		if url.endswith('/'):
			url = url[:-1]
		filetype = utils.get_filetype_from_url(url)
		if filetype:
			#index = len(filetype)
			url = url[:-(len(filetype)+1)]
		self._url = url
		self.domain = domain
		self.scheme = utils.get_scheme(url)
		self._html_source = html
		self.clean_html_source()

		self._backup_html_tree = lxml.html.fromstring(self._html_source, parser=self._parser)
		# registering all available functions in default namespace
		# xpath2_functions.register_functions(self._backup_html_tree)
		self.body_node = self._tree_explorer.get_elements_by_tags(self._backup_html_tree, ['body'])[0] # viene prelevato il body dal DOM
		self.language = self.extract_content_language()
		self._is_news = self._check_webnews_from_meta_tag()
		# iniziare da qui tutte le chiamate per modificare il DOM e non prima
		self._fix_relative_urls()
		if store_urls:
			self._retrieve_urls()

	def extract_content(self, d_v_path=None, language=None, is_webnews=False, title_art=None, publish_date=None, img_art=None, videos_art=None, authors=None, category=None):
		#self.language = language
		if self.language and len(self.language) >= 2:
			self.language = self.language[:2].lower()
		article_container = None
		if is_webnews or self._is_news or Article.is_valid_url(self._url):
			self._last_clean()
			self.article = Article(url=self._url, language=self.language, title_art=title_art, publish_date=publish_date, img_art=img_art, videos_art=videos_art, category=category, authors=authors, html_tree=self._backup_html_tree, domain_videos_path=d_v_path)
			article_container = self.article.parse()
			self.language = article_container.language
		in_links = self.get_domain_links()
		# outbound_links = self.get_outbound_links()
		# images = self.get_imgs()
		# html_string = lxml.html.tostring(self._backup_html_tree, method="html").decode()
		html_string = ''
		text_content = None # per il momento non pare necessario collezionare anche il testo che non è parte dell'articolo
		result = PageContentContainer(url=self._url, language=self.language, article_c=article_container, html=html_string, in_links=in_links, text=text_content)
		return result

	def _last_clean(self):
		#start_time = utils.current_time()
		self._remove_text_style_tag()
		self._remove_forms()
		self._remove_input()
		self._remove_select()
		self._remove_hr()
		self._checking_ids_tree()
		scripts = self.pop_scripts()
		styles = self.pop_styles()
		iframes = self.pop_iframe()
		html_tree_copy = copy.deepcopy(self._backup_html_tree)
		hunter = NavigationContentHunter(html_tree_copy)
		hunter.find_candidate()
		blocks_to_remove = hunter.get_candidate()
		self._apply_nhunter_result_on_page(blocks_to_remove)
		self._remove_with_attr_value()
		#elapsed_time = utils.current_time() - start_time
		#print('blocks removed: ' + str(len(blocks_to_remove)) + ' elapesd: ' + str(elapsed_time))
		#self._remove_hidden_tags()


	def extract_rss_source(self):
		sources_rss = list()
		common_feed = ['rss', 'feed', 'feeds']
		expression = "//a[contains(@href, '%s')] | //a[contains(@href, '%s')] | //a[contains(@href, '%s')]" % ('feed', 'feeds', 'rss')
		_selected_elements = self._tree_explorer.xpath(self._backup_html_tree, expression)
		for a_element in _selected_elements:
			url = self._tree_explorer.get_attribute(a_element, attr='href')
			path_tokens = utils.get_path(url).split('/')
			latest_token = path_tokens[len(path_tokens)-1]
			if 'rss' in latest_token or 'feed' in latest_token:
				sources_rss.append(url)
			else:
				for token in path_tokens:
					if token in common_feed:
						sources_rss.append(url)
						break
		sources_rss = list(set(sources_rss))
		if len(sources_rss) == 0:
			for common in common_feed:
				sources_rss.append('%s/%s' % (self._url, common))
		return sources_rss

	def extract_feed_rss(self):
		tmp = self._tree_explorer.xpath(self._backup_html_tree, '//link[@type="application/rss+xml" and @rel="alternate"] | //link[@type="application/atom+xml" and @rel="alternate"]' )
		feeds = dict()
		for t in tmp:
			feeds[self._tree_explorer.get_attribute(t, attr='href')] = self._tree_explorer.get_attribute(t, attr='title')
		if len(feeds) == 0:
			tmp = self._tree_explorer.xpath(self._backup_html_tree, "//a[contains(@href, '.xml')]")
			for t in tmp:
				href = self._tree_explorer.get_attribute(t, attr='href')
				file_type = utils.get_filetype_from_url(href)
				if file_type and file_type == 'xml':
					feeds[href] = ''
		if len(feeds) == 0:
			tmp = self._tree_explorer.xpath(self._backup_html_tree, "//a[contains(@href, 'rss')] | //a[contains(@href, 'feed')]")
			for t in tmp:
				href = self._tree_explorer.get_attribute(t, attr='href')
				if not utils.is_valid_url(href):
					final_url = '%s/%s' % (self._url, href)
					if utils.is_valid_url(final_url):
						feeds[final_url] = ''
				elif not utils.are_equals_urls(href, self._url):
					feeds[href] = ''
		return feeds

	def pop_scripts(self):
		result = list()
		elements = self._tree_explorer.xpath(self._backup_html_tree, '//script|//noscript')
		for element in elements:
			result.append(lxml.html.tostring(element, method='html').decode())
			self._tree_explorer.remove(element, remove_tail=True)
		return result

	def pop_styles(self):
		result = list()
		elements = self._tree_explorer.xpath(self._backup_html_tree, '//style')
		for element in elements:
			result.append(lxml.html.tostring(element, method='html').decode())
			self._tree_explorer.remove(element, remove_tail=True)
		return result

	def get_imgs(self):
		result = list()
		elements = self._tree_explorer.xpath(self.body_node, '//img[@src]')
		for element in elements:
			src = element.attrib['src']
			title = element.attrib.get('title', None)
			result.append((src, title))
		return result

	def pop_iframe(self):
		result = list()
		elements = self._tree_explorer.xpath(self.body_node, '//iframe')
		for element in elements:
			result.append(lxml.html.tostring(element, method='html').decode())
			self._tree_explorer.remove(element)
		return result

	def pop_article(self):
		result = list()
		root = self._backup_html_tree
		for element in root.iter('article'):
			result.append(lxml.html.tostring(element, method='html', encoding='utf-8').decode())
		return result

	def get_outbound_links(self):
		return self._outbound_links

	def get_domain_links(self):
		return self._domain_urls

	def _apply_nhunter_result_on_page(self, blocks_to_remove):
		try:
			expression = "|".join(["//%s" % t for t in utils.LIST_OF_IMPORTANT_TAG])
			elements_with_id = self._tree_explorer.xpath(self.body_node, expression)
			for element in elements_with_id:
				_id = self._tree_explorer.get_attribute(element, attr='id')
				if _id in blocks_to_remove:
					if self.can_be_deleted(element):
						self._tree_explorer.remove(element, to_print=False)
					blocks_to_remove.remove(_id)
		except Exception as ex:
			print(ex)
		# self._remove_empty_field(self._backup_html_tree[1])

	def _checking_ids_tree(self):
		expression = "|".join(["//%s" % t for t in utils.LIST_OF_IMPORTANT_TAG])
		important_elements = self._tree_explorer.xpath(self.body_node, expression)
		for element in important_elements:
			if element is not self.body_node:
				_id = self._tree_explorer.get_attribute(element, attr='id')
				if _id:
					if _id in self._notes_on_descent:
						new_id = utils.new_random_id()
						while new_id in self._notes_on_descent:
							new_id = utils.new_random_id()
						self._notes_on_descent[new_id] = _id
						self._tree_explorer.set_attribute(element, attr='id', value=new_id)
					else:
						self._notes_on_descent[_id] = None
				else:
					_id = utils.new_random_id()
					while _id in self._notes_on_descent.keys():
						_id = utils.new_random_id()
					self._notes_on_descent[_id] = None
					self._tree_explorer.set_attribute(element, attr='id', value=_id)

	def clean_html_source(self):
		self._html_source = " ".join(self._html_source.split())

	def _remove_text_style_tag(self):
		elements = self._tree_explorer.get_elements_by_tags(self.body_node, _tag_text_formatting)
		for element in elements:
			self._tree_explorer.drop_tag(element)

	# prende in input una lista di url trovati nella pagina e verifica che siano dei validi url
	def _fix_relative_urls(self):
		_href_elements = self._tree_explorer.xpath_re(self.body_node, "//*[re:test(@href, '^/.*', 'i')]")
		#_href_elements = self._tree_explorer.xpath(self.body_node, '//a[start-with(@href,"/"]')
		domain = self.scheme + '://' + utils.get_principal_domain_www(self._url)
		for element in _href_elements:
			href = self._tree_explorer.get_attribute(element, 'href')
			if href.startswith(r'//'):
				href = self.scheme + ':' + href
				self._tree_explorer.set_attribute(element, 'href', href)
			elif href.startswith(r'/'):
				href = domain + href
				self._tree_explorer.set_attribute(element, 'href', href)

	def _retrieve_urls(self):
		self._domain_urls = self.retrieve_domain_links()
		self._outbound_links = self._retrieve_outbound_links()

	def retrieve_domain_links(self):
		result = dict()
		# principal_domain = utils.get_principal_domain(self._url)
		# regex = "//*[regexp:test(@href, '^(https?://)?(www\.)?.*%s', 'i')]" % principal_domain
		# elements_with_urls = self.root.xpath(regex)
		expression = "//a[contains(@href, '%s')]" % self.domain
		elements_with_urls = self._tree_explorer.xpath(self.body_node, expression)
		for element in elements_with_urls:
			href = element.attrib['href']
			href = utils.clean_url(href, remove_arguments=False, domain=self.domain, scheme=self.scheme)
			if utils.is_valid_url_to_navigate(href):
					if utils.is_domain_link(href, self.domain):
						if href not in result:
							result[href] = ''
		return list(result.keys())

	def _retrieve_outbound_links(self):
		result = dict()
		principal_domain = utils.get_principal_domain(self._url)
		regex = "//*[@href and not(@href [contains(., '%s')])]" % principal_domain
		elements_with_urls = self._tree_explorer.xpath(self.body_node, regex)
		for element in elements_with_urls:
			href = element.attrib['href']
			if utils.is_valid_url(href):
				href = utils.clean_url(href)
				if href not in result:
					result[href] = ''
		return list(result.keys())

	def can_be_deleted(self, node):
		result = not self._tree_explorer.xpath(node, self.blocks_to_not_remove_xpath)
		parent = self._tree_explorer.get_parent(node)
		if parent is not None and result:
			parent_tag = self._tree_explorer.get_tag(parent)
			result = parent_tag not in self.protect_parent
		return result

	def _remove_forms(self):
		for form in self._tree_explorer.get_forms(self.body_node):
			self._tree_explorer.remove(form)

	def _remove_input(self):
		elements = self._tree_explorer.xpath(self.body_node, '//input')
		for element in elements:
			self._tree_explorer.remove(element)

	def _remove_select(self):
		elements = self._tree_explorer.xpath(self.body_node, '//select')
		for element in elements:
			self._tree_explorer.remove(element)

	def _remove_hr(self):
		elements = self._tree_explorer.xpath(self.body_node, '//hr')
		for element in elements:
			self._tree_explorer.remove(element)

	def _remove_with_attr_value(self):
		caption_re = "^caption$"
		google_re = " google "
		entries_re = "^[^entry-]more.*$"
		facebook_re = "[^-]facebook"
		facebook_braodcasting_re = "facebook-broadcasting"
		twitter_re = "[^-]twitter"
		self._remove_nodes_regex(caption_re)
		self._remove_nodes_regex(google_re)
		self._remove_nodes_regex(entries_re)
		self._remove_nodes_regex(facebook_re)
		self._remove_nodes_regex(facebook_braodcasting_re)
		self._remove_nodes_regex(twitter_re)
		remove_nodes_re = ("^side$|combx|retweet|mediaarticlerelated|menucontainer|"
							"navbar|storytopbar-bucket|utility-bar|inline-share-tools"
							"|comment|PopularQuestions|contact|foot|footer|Footer|footnote"
							"|cnn_strycaptiontxt|cnn_html_slideshow|cnn_strylftcntnt"
							"|links|meta$|shoutbox|sponsor"
							"|tags|socialnetworking|socialNetworking|cnnStryHghLght"
							"|cnn_stryspcvbx|^inset$|pagetools|post-attributes"
							"|welcome_form|contentTools2|the_answers"
							"|communitypromo|runaroundLeft|subscribe|vcard|articleheadings"
							"|date|^print$|popup|author-dropdown|tools|socialtools|byline"
							"|konafilter|KonaFilter|breadcrumbs|^fn$|wp-caption-text"
							"|legende|ajoutVideo|timestamp|js_replies")
		nauthy_ids_re = ("//*[re:test(@id, '%s', 'i')]" % remove_nodes_re)
		nauthy_classes_re = ("//*[re:test(@class, '%s', 'i')]" % remove_nodes_re)
		nauthy_names_re = ("//*[re:test(@name, '%s', 'i')]" % remove_nodes_re)
		items = self._tree_explorer.xpath_re(self.body_node, nauthy_ids_re)
		for item in items:
			if self.can_be_deleted(item):
				self._tree_explorer.remove(item)
		items = self._tree_explorer.xpath_re(self.body_node, nauthy_classes_re)
		for item in items:
			if self.can_be_deleted(item):
				self._tree_explorer.remove(item)
		items = self._tree_explorer.xpath_re(self.body_node, nauthy_names_re)
		for item in items:
			if self.can_be_deleted(item):
				self._tree_explorer.remove(item)

	def _remove_nodes_regex(self, pattern):
		for selector in ['id', 'class']:
			reg = "//*[re:test(@%s, '%s', 'i')]" % (selector, pattern)
			naughty_list = self._tree_explorer.xpath_re(self.body_node, reg)
			for node in naughty_list:
				self._tree_explorer.remove(node)

	def _remove_hidden_tags(self):
		expression = "//*[(contains(@style,'display:none'))] | //*[(contains(@style,'display: none'))]"
		elements = self._tree_explorer.xpath(self._backup_html_tree, expression)
		for element in elements:
			if self.can_be_deleted(element):
				self._tree_explorer.remove(element, remove_tail=True)

	def extract_content_language(self):
		html_tag = self._tree_explorer.xpath(self._backup_html_tree, '//html')
		result = self._tree_explorer.get_attribute(html_tag[0], 'lang')
		if result is None:
			meta_tag = self._tree_explorer.xpath(self._backup_html_tree, '//meta[@http-equiv="content-language"] | //meta[@name="language"]')
			if meta_tag:
				result = self._tree_explorer.get_attribute(meta_tag[0], 'content')
		return result

	def _check_webnews_from_meta_tag(self):
		result = False
		candidates = self._tree_explorer.xpath(self._backup_html_tree, '//*[@itemtype="http://schema.org/NewsArticle"]'
																		'|//*[@itemtype="http://schema.org/Article"]'
																		'| //meta[@property="og:type" and @content="article"]')
		if candidates:
			result = True
		return result
