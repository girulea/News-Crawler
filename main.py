import utils
from crawling_tools.crawler_manager import CrawlerManager
from sys import stdin

urls = utils.read_text_file_as_array('risorse/lista_lite.txt')
# urls_1 = utils.read_text_file_as_array('risorse/lista siti attendibili.txt')
# urls_2 = utils.read_text_file_as_array('risorse/lista siti fake.txt')
# urls_1.extend(urls_2)
# urls = urls_1
tmp = list()
for url in urls:
	tmp.append(utils.get_final_url(url))
urls = list(set(tmp))
# w_directory = '/media/amerigo/b76d854a-105f-412d-8e94-38e8af4ce00c/'
w_directory = '/media/amerigo/9cc91086-99d7-4d4b-87c1-202b79c2173d/'
# w_directory = '/home/amerigo/Documenti/download crawler/'
ex_path = '/media/amerigo/9cc91086-99d7-4d4b-87c1-202b79c2173d/risorse/chromedriver'
#crawler_m = CrawlerManager(['https://www.corriere.it/'], headless_mode=True, num_of_crawler=1, num_of_thread_for_crawler=8, working_directory=w_directory, driver_ex_path=ex_path)
crawler_m = CrawlerManager(urls, headless=True, num_of_crawler=4, n_crawler_thread=6, working_dir=w_directory, driver_ex_path=ex_path)
crawler_m.start()
while True:
	stdin.readline()
