# -*- coding: utf-8 -*-
"""
Newspaper uses a lot of python-goose's parsing code. View theirlicense:
https://github.com/codelucas/newspaper/blob/master/GOOSE-LICENSE.txt
Parser objects will only contain operations that manipulate
or query an lxml or soup dom object generated from an article's html.
"""
import re
import string
from copy import deepcopy
from html import unescape

import lxml.etree as etree
import lxml.html
import lxml.html.clean


class TreeExplorer(object):

	@classmethod
	def xpath_re(cls, node, expression):
		regexp_namespace = "http://exslt.org/regular-expressions"
		items = node.xpath(expression, namespaces={'re': regexp_namespace})
		return items

	@classmethod
	def xpath(cls, node, expression):
		return node.xpath(expression)

	@classmethod
	def drop_tag(cls, nodes):
		if isinstance(nodes, list):
			for node in nodes:
				node.drop_tag()
		else:
			nodes.drop_tag()

	@classmethod
	def css_select(cls, node, selector):
		return node.cssselect(selector)

	@classmethod
	def get_unicode_html(cls, html):
		if isinstance(html, str):
			return html
		else:
			return str(html)
		# if not html:
		#     return html
		# converted = UnicodeDammit(html, is_html=True)
		# if not converted.unicode_markup:
		#     raise Exception(
		#         'Failed to detect encoding of article HTML, tried: %s' %
		#         ', '.join(converted.tried_encodings))
		# html = converted.unicode_markup
		# return html

	@classmethod
	def fromstring(cls, html):
		html = cls.get_unicode_html(html)
		# Enclosed in a `try` to prevent bringing the entire library
		# down due to one article (out of potentially many in a `Source`)
		try:
			# lxml does not play well with <? ?> encoding tags
			if html.startswith('<?'):
				html = re.sub(r'^\<\?.*?\?\>', '', html, flags=re.DOTALL)
			cls.doc = lxml.html.fromstring(html)
			return cls.doc
		except Exception as e:
			print(e)

	@classmethod
	def clean_article_html(cls, node):
		article_cleaner = lxml.html.clean.Cleaner()
		article_cleaner.javascript = True
		article_cleaner.style = True
		article_cleaner.allow_tags = [
			'a', 'span', 'p', 'br', 'strong', 'b',
			'em', 'i', 'tt', 'code', 'pre', 'blockquote', 'img', 'h1',
			'h2', 'h3', 'h4', 'h5', 'h6',
			'ul', 'ol', 'li', 'dl', 'dt', 'dd']
		article_cleaner.remove_unknown_tags = False
		return article_cleaner.clean_html(node)

	@classmethod
	def node_to_string(cls, node):
		return etree.tostring(node, method='html').decode()

	@classmethod
	def replace_tag(cls, node, tag):
		node.tag = tag

	@classmethod
	def strip_tags(cls, node, *tags):
		etree.strip_tags(node, *tags)

	@classmethod
	def get_element_by_id(cls, node, _id):
		selector = '//*[@id="%s"]' % _id
		elems = node.xpath(selector)
		if elems:
			return elems[0]
		return None

	@classmethod
	def get_elements_by_tag_name(
			cls, node, tag=None, attr=None, value=None, childs=False, use_regex=False) -> list:
		NS = None
		# selector = tag or '*'
		selector = 'descendant-or-self::%s' % (tag or '*')
		if attr and value:
			if use_regex:
				NS = {"re": "http://exslt.org/regular-expressions"}
				selector = '%s[re:test(@%s, "%s", "i")]' % (selector, attr, value)
			else:
				trans = 'translate(@%s, "%s", "%s")' % (attr, string.ascii_uppercase, string.ascii_lowercase)
				selector = '%s[contains(%s, "%s")]' % (selector, trans, value.lower())
		elif attr:
			trans = 'translate(@%s, "%s", "%s")' % (attr, string.ascii_uppercase, string.ascii_lowercase)
			selector = '%s[%s]' % (selector, trans)
		elems = node.xpath(selector, namespaces=NS)
		# remove the root node
		# if we have a selection tag
		if node in elems and (tag or childs):
			elems.remove(node)
		return elems

	@classmethod
	def append_child(cls, node, child):
		node.append(child)

	@classmethod
	def list_child_nodes(cls, node):
		return list(node)

	@classmethod
	def child_nodes_with_text(cls, node):
		root = node
		# create the first text node
		# if we have some text in the node
		if root.text:
			t = lxml.html.HtmlElement()
			t.text = root.text
			t.tag = 'text'
			root.text = None
			root.insert(0, t)
		# loop childs
		for c, n in enumerate(list(root)):
			idx = root.index(n)
			# don't process texts nodes
			if n.tag == 'text':
				continue
			# create a text node for tail
			if n.tail:
				t = cls.create_element(tag='text', text=n.tail, tail=None)
				root.insert(idx + 1, t)
		return list(root)

	@classmethod
	def text_to_para(cls, text):
		return cls.fromstring(text)

	@classmethod
	def get_children(cls, node):
		return node.getchildren()

	@classmethod
	def get_elements_by_tags(cls, node, tags):
		selector = 'descendant::*[%s]' % (
			' or '.join('self::%s' % tag for tag in tags))
		elems = node.xpath(selector)
		return elems

	@classmethod
	def create_element(cls, tag='p', text=None, tail=None):
		t = lxml.html.HtmlElement()
		t.tag = tag
		t.text = text
		t.tail = tail
		return t

	@classmethod
	def get_comments(cls, node):
		return node.xpath('//comment()')

	@classmethod
	def get_parent(cls, node):
		return node.getparent()

	@classmethod
	def get_nearest_parent_by_tag(cls, element, tags):
		result = None
		try:
			_cond = True
			parent = element.getparent()
			while _cond and parent is not None:
				if parent.tag in tags:
					_cond = False
					result = parent
				else:
					parent = parent.getparent()
		except Exception as ex:
			print(ex)
		return result

	@classmethod
	def change_parent(cls, node, new_parent):
		result = False
		if node is not None and new_parent is not None:
			old_parent = node.getparent()
			if old_parent is not None:
				old_parent.remove(node)
			new_parent[len(new_parent)-1].addnext(node)
			result = True
		return result

	@classmethod
	def remove(cls, node, remove_tail=False, to_print=False):
		parent = node.getparent()
		if parent is not None and remove_tail:
			if node.tail:
				prev = node.getprevious()
				if prev is None:
					if not parent.text:
						parent.text = ''
					parent.text += ' ' + node.tail
				else:
					if not prev.tail:
						prev.tail = ''
					prev.tail += ' ' + node.tail
			if to_print:
				print('tag: ' + node.tag + ' ' + cls.get_text(node))
			node.clear()
			parent.remove(node)

	@classmethod
	def get_tag(cls, node):
		return node.tag

	@classmethod
	def get_text(cls, node, clean=True):
		# txts = [i for i in node.itertext()]
		result = ''
		for t in node.itertext():
			result += " " + t
		if clean:
			return cls.clean_text(result)
		return result

	@classmethod
	def get_text_without_child(cls, node, clean=True):
		result = None
		if node is not None:
			result = node.text
		if clean:
			result = cls.clean_text(result)
		return result

	@classmethod
	def get_text_with_count_multi_nodes(cls, nodes, tags_to_ignore=None, clean=True):
		result = ''
		count = 0
		for node in nodes:
			result_tmp, count_tmp = cls.get_text_with_count(node, tags_to_ignore, clean=clean)
			result += result_tmp
			count += count_tmp
		return result, count

	@classmethod
	def get_text_with_count(cls, node, tags_to_ignore=None, clean=True):
		result = ''
		count = 0
		if tags_to_ignore:
			for elem in node.iter():
				if elem.tag not in tags_to_ignore and elem.text is not None:
					text = elem.text
					if clean:
						text = ' '.join(text.split())
					if len(text) > 1:
						result += " " + text
						count += 1
		else:
			for t in node.itertext():
				t = ' '.join(t.split())
				if len(t) > 1:
					result += " " + t
					count += 1
		return result, count

	@classmethod
	def get_links(cls, node, tags_to_ignore=None, tags=None):
		result = list()
		if tags_to_ignore:
			for elem in node.iter():
				if elem.tag not in tags_to_ignore:
					if tags:
						if elem.tag in tags:
							result.append(elem)
					else:
						result.append(elem)
		else:
			for l in node.iterlinks():
				if tags:
					if l[0].tag in tags:
						result.append(l[0])
				else:
					result.append(l[0])
		return result

	@classmethod
	def get_text_first_childs(cls, node, clean=True):
		text = ''
		no_empty_tags = 0
		if node is not None:
			for c in node.iterchildren():
				if c.text is not None and len(c.text) > 1:
					text += " " + c.text
					no_empty_tags += 1
		if clean and len(text) > 0:
			text = " ".join(text.split())
		return text, no_empty_tags

	@classmethod
	def get_text_from_first_anchor(cls, node, clean=True):
		text = ''
		no_empty_tags = 0
		if node is not None:
			for c in node.iterchildren():
				if c.text is not None and len(c.text) > 1:
					if c.tag == 'a':
						text += c.text
						no_empty_tags += 1
		if clean and len(text) > 0:
			text = " ".join(text.split())
		return text, no_empty_tags

	@classmethod
	def has_child_tag(cls, node, tags=None):
		result = False
		for c in node.iterchildren():
			if tags is None:
				result = True
				break
			elif c.tag in tags:
				result = True
				break
		return result

	@classmethod
	def previous_siblings(cls, node):
		"""
			returns preceding siblings in reverse order (nearest sibling is first)
		"""
		return [n for n in node.itersiblings(preceding=True)]

	@classmethod
	def previous_sibling(cls, node):
		return node.getprevious()

	@classmethod
	def next_sibling(cls, node):
		return node.getnext()

	@classmethod
	def is_text_node(cls, node):
		return True if node.tag == 'text' else False

	@classmethod
	def get_attribute(cls, node, attr=None):
		if attr:
			attr = node.attrib.get(attr, None)
		if attr:
			attr = unescape(attr)
		return attr

	@classmethod
	def del_attribute(cls, node, attr=None):
		if attr:
			_attr = node.attrib.get(attr, None)
			if _attr:
				del node.attrib[attr]

	@classmethod
	def set_attribute(cls, node, attr=None, value=None):
		if attr and value:
			node.attrib[attr] = value

	@classmethod
	def get_node_depth(cls, node, stop_node=None):
		result = 0
		parent = node.getparent()
		while parent is not None and (stop_node is None or (len(stop_node) and parent is not stop_node)):
			result += 1
			parent = parent.getparent()
		return result

	@classmethod
	def calculating_subtree_width(cls, node, tagstoevaluate=None):
		if tagstoevaluate:
			expression = "|".join(['//%s' % t for t in tagstoevaluate])
			count = len(node.xpath(expression))
		else:
			count = len(list(node))
		return count

	@classmethod
	def outer_html(cls, node):
		e0 = node
		if e0.tail:
			e0 = deepcopy(e0)
			e0.tail = None
		return cls.node_to_string(e0)

	@classmethod
	def clean_text(cls, value):
		if isinstance(value, str):
			return " ".join(value.split())
		return ''

	@classmethod
	def mark_tags(cls, node, tags_list=None, tag_to_set=None, marker_tag=None, replace_opposite=False, option_tag_to_set=None):
		expression = "|".join(['//%s' % t for t in tags_list])
		elements = node.xpath(expression)
		for element in elements:
			#tag = element.tag
			#element.tag = tag_to_set
			element.attrib[marker_tag] = tag_to_set
		if replace_opposite and option_tag_to_set:
			opt_expression = '//*[not(@%s="%s")]' % (marker_tag, tag_to_set)
			opt_elements = node.xpath(opt_expression)
			for opt_element in opt_elements:
				opt_element.attrib[marker_tag] = option_tag_to_set

	@classmethod
	def get_forms(cls, node):
		return node.forms

