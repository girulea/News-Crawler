from os import listdir
from os.path import isfile, join
import sqlite3

mypath = '/media/amerigo/9cc91086-99d7-4d4b-87c1-202b79c2173d/'
only_files = [join(mypath, f) for f in listdir(mypath) if isfile(join(mypath, f))]
only_db = [f for f in only_files if f.endswith('.db')]
filtered_news_count_query = " select count(pages.url)"\
			" from pages "\
			" where  "\
			" pages.text_art in  "\
			" (select sub_select.text  "\
			" from  "\
			" (select text_art AS text, count(id) as numb  "\
			" from pages  "\
			" where scraped=1  "\
			" and is_webnews=1  "\
			" and length(text_art)>500  "\
			" group by text)  "\
			" as sub_select  "\
			" where sub_select.numb < 4)"

news_count_query = "select count(*) from pages where scraped=1 and is_webnews=1"
pages_count_query = "select count(*) from pages where scraped=1"

total_scraped = 0
total_news = 0
filtered_news = 0
for db in only_db:
	connection = sqlite3.connect(db)
	cursors = connection.cursor()
	cursors.execute(pages_count_query)
	res = cursors.fetchone()
	total_scraped = total_scraped + res[0]
	cursors.close()
	cursors = connection.cursor()
	cursors.execute(news_count_query)
	res = cursors.fetchone()
	total_news = total_news + res[0]
	cursors.close()
	cursors = connection.cursor()
	cursors.execute(filtered_news_count_query)
	res = cursors.fetchone()
	filtered_news = filtered_news + res[0]
	cursors.close()
	connection.close()
print(str(total_scraped))
print(str(total_news))
print(str(filtered_news))
