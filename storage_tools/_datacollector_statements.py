CREATION_QUERY_DOMAIN = '''CREATE TABLE IF NOT EXISTS domain_info
						(domain_url TEXT PRIMARY KEY, 
						domain_name TEXT,
						domain_videos_path TEXT)'''

CREATION_QUERY_DATES_COLLECT = '''CREATE TABLE IF NOT EXISTS dates_collected	
								(date_type TEXT, 
								date_value timestamp )'''

CREATION_QUERY_PAGES = '''CREATE TABLE IF NOT EXISTS pages
						(id INTEGER PRIMARY KEY AUTOINCREMENT,
						protocol TEXT,
						url TEXT UNIQUE, 
						scraped INT,
						attempts_count INT, 
						mime_type TEXT,
						http_response_code INT,
						language TEXT,
						url_to_refer TEXT,
						generic_text TEXT,
						is_webnews INT,
						title_art TEXT, 
						text_art TEXT, 
						publish_date TEXT, 
						img_art TEXT,
						videos_art TEXT,
						authors TEXT,
						category TEXT,
						har TEXT, 
						error_text Text);'''

GET_CANDIDATES_QUERY = 'SELECT url, protocol, scraped, attempts_count, language, is_webnews, title_art, publish_date, img_art, videos_art, authors, category '\
						'FROM pages ' \
						'WHERE scraped=0 AND ' \
						'attempts_count=0 AND is_webnews=? '\
						'LIMIT ? ;'

INSERT_LINKS_QUERY = "INSERT OR IGNORE INTO pages "\
					"(url, protocol, scraped, attempts_count, is_webnews) "\
					"VALUES(?, ?, ?, ?)"

UPDATE_MANY_DATA_QUERY = 'UPDATE pages ' \
						'SET scraped=?, ' \
						'attempts_count=?, ' \
						'mime_type=?, ' \
						'http_response_code=?, '\
						'language=?, '\
						'url_to_refer=?, ' \
						'generic_text=?, ' \
						'is_webnews=?, ' \
						'title_art=?, ' \
						'text_art=?, ' \
						'publish_date=?, ' \
						'img_art=?, ' \
						'videos_art=?, '\
						'authors=?, '\
						'category=?, '\
						'har=?, ' \
						'error_text=? ' \
						'WHERE url=? and scraped=0;'

CREATION_HAR_URLS_QUERY = 'CREATE TABLE IF NOT EXISTS har_urls'\
						'(id INTEGER PRIMARY KEY AUTOINCREMENT,' \
						'url TEXT UNIQUE,'\
						'is_advertising INT,' \
						'checked INT DEFAULT 0);'

INSERT_HAR_URL_QUERY = 'INSERT OR IGNORE INTO har_urls '\
					'(url, is_advertising)'\
					'VALUES(?, ?)'

CREATION_PAGE_HAR_URL_ASSOCIATED_QUERY = 'CREATE TABLE IF NOT EXISTS page_har_url_associated' \
										'(id_page INTEGER,' \
										'id_har_url INTEGER,' \
										'FOREIGN KEY (id_page) REFERENCES pages(id) ON DELETE CASCADE,' \
										'FOREIGN KEY (id_har_url) REFERENCES har_urls(id) ON DELETE CASCADE,' \
										'CONSTRAINT name_unique UNIQUE (id_page, id_har_url))'

ASSOCIATE_PAGE_AND_HAR_URL_QUERY = 'INSERT OR IGNORE INTO page_har_url_associated' \
									'(id_page, id_har_url)' \
									'VALUES(?,?)'

CREATE_INDEX_ON_DB_QUERY = ['CREATE INDEX IF NOT EXISTS index_url_pages ON pages (url);',
							'CREATE INDEX IF NOT EXISTS index_url_har ON har_urls (url);']

CREATE_FEED_RSS_QUERY = 'CREATE TABLE IF NOT EXISTS feed_rss' \
						'(url TEXT PRIMARY KEY,' \
						'class TEXT,' \
						'language TEXT,' \
						'last_update TIMESTAMP);'

INSERT_FEED_RSS_QUERY = 'INSERT OR IGNORE INTO feed_rss' \
						'(url, class)' \
						'VALUES(?,?)'

UPDATE_FEED_DETAILS_QUERY = 'UPDATE feed_rss ' \
							'SET class=?,' \
							'language=?' \
							'WHERE url=?;'

UPDATE_FEED_TIMESTAMP_QUERY = 'UPDATE feed_rss ' \
								'SET last_update=CURRENT_TIMESTAMP ' \
								'WHERE url=?;'

GET_FEEDS_RSS_QUERY = 'SELECT url, class, language, last_update FROM feed_rss'
