# -*- coding: utf-8 -*-
"""
Output formatting to text via lxml xpath nodes abstracted in this file.
"""
__title__ = 'newspaper'
__author__ = 'Lucas Ou-Yang'
__license__ = 'MIT'
__copyright__ = 'Copyright 2014, Lucas Ou-Yang'

from html import unescape

from extraction_tools.explorer import TreeExplorer
from .texthelper import StopWords


class OutputFormatter(object):

	def __init__(self, language='it', keep_article_html=True):
		self.top_node = None
		self.keep_article_html = keep_article_html
		self._tree_explorer = TreeExplorer
		self.language = language
		self.stopwords_class = StopWords(language)

	def update_language(self, meta_lang):
		'''Required to be called before the extraction process in some
		cases because the stopwords_class has to set incase the lang
		is not latin based
		'''
		if meta_lang:
			self.language = meta_lang
			self.stopwords_class = StopWords(self.language)

	def get_top_node(self):
		return self.top_node

	def get_formatted(self, top_node):
		"""Returns the body text of an article, and also the body article
		html if specified. Returns in (text, html) form
		"""
		self.top_node = top_node
		html, text = '', ''

		self.remove_negativescores_nodes()

		if self.keep_article_html:
			html = self.convert_to_html()

		self.links_to_text()
		self.add_newline_to_br()
		self.add_newline_to_li()
		self.replace_with_text()
		self.remove_empty_tags()
		self.remove_trailing_media_div()
		text = self.convert_to_text()
		return text, html

	def convert_to_text(self):
		txts = []
		for node in list(self.get_top_node()):
			try:
				txt = self._tree_explorer.get_text(node)
			except ValueError as err:  # lxml error
				txt = None

			if txt:
				txt = unescape(txt)
				txt_lis = " ".join(txt.split())
				#txt_lis = [n.strip(' ') for n in txt_lis]
				txts.append(txt_lis)
		return ' '.join(txts)

	# def convert_to_text(self):
	# 	txts = list()
	# 	for node in list(self.get_top_node()):
	# 		try:
	# 			txt = self._tree_explorer.get_text(node)
	# 		except ValueError as err:  # lxml error
	# 			txt = None
	#
	# 		if txt:
	# 			txt = unescape(txt)
	# 			txt_lis = txt.split()
	# 			txts.extend(txt_lis)
	# 	return " ".join(txts)

	def convert_to_html(self):
		cleaned_node = self._tree_explorer.clean_article_html(self.get_top_node())
		return self._tree_explorer.node_to_string(cleaned_node)

	def add_newline_to_br(self):
		for e in self._tree_explorer.get_elements_by_tag_name(self.top_node, tag='br'):
			e.text = r'\n'

	def add_newline_to_li(self):
		for e in self._tree_explorer.get_elements_by_tag_name(self.top_node, tag='ul'):
			li_list = self._tree_explorer.get_elements_by_tag_name(e, tag='li')
			for li in li_list[:-1]:
				li.text = self._tree_explorer.get_text(li) + r'\n'
				for c in self._tree_explorer.get_children(li):
					self._tree_explorer.remove(c)

	def links_to_text(self):
		"""Cleans up and converts any nodes that should be considered
		text into text.
		"""
		self._tree_explorer.strip_tags(self.get_top_node(), 'a')

	def remove_negativescores_nodes(self):
		"""If there are elements inside our top node that have a
		negative gravity score, let's give em the boot.
		"""
		gravity_items = self._tree_explorer.css_select(
			self.top_node, "*[gravityScore]")
		for item in gravity_items:
			score = self._tree_explorer.get_attribute(item, 'gravityScore')
			score = float(score) if score else 0
			if score < 1:
				item.getparent().remove(item)

	def replace_with_text(self):
		"""
		Replace common tags with just text so we don't have any crazy
		formatting issues so replace <br>, <i>, <strong>, etc....
		With whatever text is inside them.
		code : http://lxml.de/api/lxml.etree-module.html#strip_tags
		"""
		self._tree_explorer.strip_tags(
			self.get_top_node(), 'b', 'strong', 'i', 'br', 'sup')

	def remove_empty_tags(self):
		"""It's common in top_node to exit tags that are filled with data
		within properties but not within the tags themselves, delete them
		"""
		all_nodes = self._tree_explorer.get_elements_by_tags(self.get_top_node(), ['*'])
		all_nodes.reverse()
		for el in all_nodes:
			tag = self._tree_explorer.get_tag(el)
			text = self._tree_explorer.get_text(el)
			if (tag != 'br' or text != '\\r') \
					and not text \
					and len(self._tree_explorer.get_elements_by_tag_name(el, tag='object')) == 0 \
					and len(self._tree_explorer.get_elements_by_tag_name(el, tag='embed')) == 0:
				self._tree_explorer.remove(el)

	def remove_trailing_media_div(self):
		"""Punish the *last top level* node in the top_node if it's
		DOM depth is too deep. Many media non-content links are
		eliminated: "related", "loading gallery", etc
		"""

		def get_depth(node, depth=1):
			"""Computes depth of an lxml element via BFS, this would be
			in parser if it were used anywhere else besides this method
			"""
			children = self._tree_explorer.get_children(node)
			if not children:
				return depth
			max_depth = 0
			for c in children:
				e_depth = get_depth(c, depth + 1)
				if e_depth > max_depth:
					max_depth = e_depth
			return max_depth

		top_level_nodes = self._tree_explorer.get_children(self.get_top_node())
		if len(top_level_nodes) < 3:
			return

		last_node = top_level_nodes[-1]
		if get_depth(last_node) >= 2:
			self._tree_explorer.remove(last_node)
