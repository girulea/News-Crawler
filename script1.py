from os import listdir
from os.path import isfile, join
import sqlite3
from multiprocessing import Pool
import time
mypath = '/media/amerigo/9cc91086-99d7-4d4b-87c1-202b79c2173d/'
only_files = [join(mypath, f) for f in listdir(mypath) if isfile(join(mypath, f))]
only_db = [f for f in only_files if f.endswith('.db')]


def vacuum_func(file_):
	connection = sqlite3.connect(file_)
	connection.cursor().execute("PRAGMA journal_mode=WAL")
	cursor = connection.cursor()
	cursor.execute("VACUUM")
	connection.commit()
	cursor.close()
	connection.close()
	time.sleep(0.02)

def delete_noise_har(file_):
	condiction = True
	while condiction:
		connection = sqlite3.connect(file_)
		# connection.setbusytimeout(500)
		connection.cursor().execute("PRAGMA journal_mode=WAL")
		connection.cursor().execute('PRAGMA foreign_keys = TRUE;')
		cursor = connection.cursor()
		cursor.execute("delete from har_urls where id in (select id from har_urls where checked=1 and is_advertising=0 limit 2000)")
		condiction = False if cursor.rowcount in (0, 1) else True
		# cursor.execute("VACUUM")
		connection.commit()
		cursor.close()
		connection.close()
	vacuum_func(file_)
	print('finito db: %s' % file_)


pool = Pool(10)
pool.map(vacuum_func, only_db)
pool.close()
pool.join()
