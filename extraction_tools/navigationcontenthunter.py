import utils
from extraction_tools.explorer import TreeExplorer

_structurally_insignificant = 'structurallyins'
_structurally_important = 'structurallyimp'
_flag_anchor_count = 'qh'
_flag_tag_count = 'qt'
_flag_text_length_anchor = 'lh'
_flag_text_length_tag = 'lt'
_marker_tag = '_marker_tag_'
_namespace_regex = "http://exslt.org/regular-expressions"
_node_to_remove_re = (
	"side|combx|retweet|mediaarticlerelated|menucontainer|"
	"utility-bar|inline-share-tools|nav"
	"|tags|socialnetworking|pagetools|post-attributes"
	"|welcome_form|contentTools2|the_answers"
	"|communitypromo|runaroundLeft|subscribe|vcard|articleheadings"
	"|popup|author-dropdown|tools|socialtools|menu"
)

_micro_data_remove = '//*[@itemtype="http://schema.org/SiteNavigationElement"]|//*[@itemtype="http://schema.org/WPFooter"]|//*[@itemtype="http://schema.org/WPSideBar"]|//*[@itemtype="http://schema.org/WPHeader"]'

class NavigationContentHunter():

	def __init__(self, html_tree):
		self._html_tree = html_tree
		self._tree_explorer = TreeExplorer
		self.body_html = self._tree_explorer.get_elements_by_tags(self._html_tree, ['body'])[0] # viene prelevato il body dal DOM
		self._blocks_to_remove = list()

	def find_candidate(self):
		self._realign_dom_elements()
		# self._remove_noise_tags()
		self._get_candidate_by_heuristics()
		self._get_candidate_by_micro_data()

	def get_candidate(self):
		return self._blocks_to_remove

	def _pruning(self, subtree):
		tag_count = 0
		anchor_count = 0
		tag_text_lenght = 0
		anchor_text_length = 0
		word_count = 0
		anchor_word_count = 0
		subtree_width = self._tree_explorer.calculating_subtree_width(subtree) + 1  # per evitare divisioni per 0
		for important_e in subtree.iterchildren(utils.LIST_OF_IMPORTANT_TAG):
			tmp_result = self._pruning(important_e)
			if tmp_result:
				child_width = tmp_result[-1]
				influence = child_width / subtree_width
				tag_count += tmp_result[0] * influence
				anchor_count += tmp_result[1] * influence
				tag_text_lenght += tmp_result[2] * influence
				anchor_text_length += tmp_result[3] * influence
				word_count += tmp_result[4] * influence
				anchor_word_count += tmp_result[5] * influence
		if subtree_width > 30:
			return None
		for insignificant_e in subtree.iterchildren():
			if insignificant_e.tag not in utils.LIST_OF_IMPORTANT_TAG:
				text_tag_tmp, tag_count_tmp = self._tree_explorer.get_text_with_count(insignificant_e, tags_to_ignore=utils.LIST_OF_IMPORTANT_TAG, clean=False)
				links = self._tree_explorer.get_links(insignificant_e, tags=['a'])
				anchor_text_tmp, anchor_count_tmp = self._tree_explorer.get_text_with_count_multi_nodes(links, tags_to_ignore=utils.LIST_OF_IMPORTANT_TAG, clean=False)
				tag_count += tag_count_tmp
				tag_text_lenght += len(text_tag_tmp)
				anchor_count += anchor_count_tmp
				anchor_text_length += len(anchor_text_tmp)
				word_count += len([w for w in text_tag_tmp.split() if len(w) > 1])
				anchor_word_count += len(anchor_text_tmp.split())
		depth = self._tree_explorer.get_node_depth(subtree)
		tag_count_ratio = 0
		text_length_ratio = 0
		if tag_text_lenght > 0:
			text_length_ratio = anchor_text_length / tag_text_lenght
		if tag_count > 0:
			tag_count_ratio = anchor_count / tag_count
		score = 0
		word_ratio = 0
		if word_count > 0:
			word_ratio = anchor_word_count/word_count
		if tag_count_ratio > 0.6:
			score += 1
		if text_length_ratio > 0.6 and word_ratio > 0.8 and word_count < 20:
			score += 1
		if score >= 2:
			self._blocks_to_remove.append(self._tree_explorer.get_attribute(subtree, 'id'))
			# self._tree_explorer.remove(subtree)
			return None
		return tag_count, anchor_count, tag_text_lenght, anchor_text_length, word_count, anchor_word_count, subtree_width

	def _get_candidate_by_heuristics(self):
		self._pruning(self.body_html)

	def _get_candidate_by_micro_data(self):
		elements = self._tree_explorer.xpath(self.body_html, _micro_data_remove)
		for element in elements:
			_id = self._tree_explorer.get_attribute(element, attr='id')
			if _id not in self._blocks_to_remove:
				self._blocks_to_remove.append(_id)

	def _remove_noise_tags(self):
		elements = self._tree_explorer.xpath(self.body_html, "//a[@href]/span")
		for element in elements:
			self._tree_explorer.drop_tag(element)
		elements = self._tree_explorer.xpath(self.body_html, "//p/a[@href]")
		for element in elements:
			self._tree_explorer.drop_tag(self._tree_explorer.get_parent(element))

	# Riordina ogni sottoalbero in modo che se qualche nodo ha come padre un nodo con tag 'structurallyins', viene riassegnato al suo antenato più vicino con tag 'structurallyimp'.
	# L'albero viene visitato con un ordinamento di tipo post-order, in modo da visitare prima i nodi con una maggiore "profondità"
	def _realign_dom_elements(self):
		try:
			for element in self.body_html.iter():
				parent = self._tree_explorer.get_parent(element)
				if parent is not None and parent is not self.body_html and parent.tag not in utils.LIST_OF_IMPORTANT_TAG:
					new_parent = self._tree_explorer.get_nearest_parent_by_tag(element, tags=utils.LIST_OF_IMPORTANT_TAG)
					self._tree_explorer.change_parent(element, new_parent)
		except IndexError as i_ex:
			print(i_ex)
		except Exception as ex:
			print(ex)