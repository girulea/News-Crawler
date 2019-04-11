from adblockparser import AdblockRules
from threading import Lock
import copy


class AdsExtractor:

	def __init__(self, filter_path='risorse/easylistitaly.txt'):
		self._adblock_rules = copy.deepcopy(_adbclok_rules_preloaded)
		self.filter_path = filter_path
		self._adblock_lock = Lock()

	def mark_ads(self, urls, domain):
		result = dict()
		options = {'domain': domain}
		with self._adblock_lock:
			for url in urls:
				if url not in result:
					result[url] = self._adblock_rules.should_block(url)
		return result

	def is_advertisement(self, url):
		return self._adblock_rules.should_block(url)


def _load_advertising_rules():
	with open('/media/amerigo/9cc91086-99d7-4d4b-87c1-202b79c2173d/risorse/easylistitaly.txt', 'r') as f:
		raw_rules = f.read().split('\n')
	return AdblockRules(raw_rules, use_re2=True, max_mem=512 * 1024 * 1024)


_adbclok_rules_preloaded = _load_advertising_rules()


