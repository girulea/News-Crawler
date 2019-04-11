from abc import ABC, abstractmethod
from threading import Lock
import time

class AbstractDataCollector(ABC):

	def __init__(self, directory=None, db_name='tmp.db'):
		self.directory = directory
		self.db_name = db_name
		self.db_locker = Lock()
		self.last_exception = None
		#self._db_connection = None

	@abstractmethod
	def start(self):
		pass

	@abstractmethod
	def stop(self):
		pass

	@abstractmethod
	def create_connection(self):
		pass

	@abstractmethod
	def commit_change(self, connection, cursor):
		pass

	@abstractmethod
	def rollback(self, connection):
		pass

	@abstractmethod
	def close_connection(self, connection):
		pass

	@abstractmethod
	def get_cursor_from_connection(self, connection):
		pass

	@abstractmethod
	def read_data(self, cursor, query_string, values_condictions=None):
		'''
		:param query_string:
		:type query_string: str
		:return: list
		'''
		pass

	@abstractmethod
	def write_data(self, cursor, statement, data_to_associate):
		pass

	def insert_data(self, table_name, params, data_to_associate, max_attempts=3):
		'''
		:param table_name:
		:type table_name: str
		:param params_values:
		:type params_values: list
		:return:
		'''
		result = False
		connection = None
		attempts = 0
		statement = self._prepare_insert_statement(table_name, params)
		while not result and attempts < max_attempts:
			try:
				connection = self.create_connection()
				cursor = self.get_cursor_from_connection(connection)
				with self.db_locker:
					self.write_data(cursor, statement, data_to_associate)
					self.commit_change(connection, cursor)
				self.close_connection(connection)
				result = True
			except Exception as ex:
				self.last_exception = str(ex)
				self.rollback(connection)
				self.close_connection(connection)
				attempts = attempts + 1
				time.sleep(1)
		return result

	def update_data(self, table_name, params_list, data_to_associate, where_condictions, max_attempts=3):
		'''
		:param query_string:
		:type query_string: str
		:param data_to_associate:
		:type data_to_associate: list
		:return:
		'''
		result = False
		connection = None
		attempts = 0
		statement = self._prepare_update_statement(table_name, params_list, where_condictions)
		while not result and attempts < max_attempts:
			try:
				connection = self.create_connection()
				cursor = self.get_cursor_from_connection(connection)
				with self.db_locker:
					self.write_data(cursor, statement, data_to_associate)
					self.commit_change(connection, cursor)
				self.close_connection(connection)
				result = True
			except Exception as ex:
				self.last_exception = str(ex)
				self.rollback(connection)
				self.close_connection(connection)
				attempts = attempts + 1
				time.sleep(1)
		return result

	def _prepare_update_statement(self, table_name, params_list, where_condictions):
		result = None
		if table_name and params_list:
			result = 'UPDATE %s SET ' % table_name
			result = result + '%s=?' % params_list[0]
			for i in range(1, len(params_list)):
				param = params_list[i]
				result = result + ', %s=?' % param
			if where_condictions:
				tmp = self._prepare_where_condiction(where_condictions)
				result = '%s %s' % (result, tmp,)
		return result

	def _prepare_insert_statement(self, table_name, params_list):
		result = None
		if params_list:
			params_section = '(%s' % params_list[0]
			values_section = 'VALUES(?'
			for i in range(1, len(params_list)):
				param = params_list[i]
				params_section = params_section + ', %s' % param
				values_section = values_section + ', ?'
			params_section = params_section + ')'
			values_section = values_section + ')'
			result = 'INSERT OR IGNORE INTO %s %s %s' % (table_name, params_section, values_section)
		return result

	def select_from_table(self, table_name, params, condictions=None, values_condictions=None, limit=0, max_attempts=3):
		'''
		:param table_name:
		:type table_name: str
		:param params:
		:type params: list
		:param condictions:
		:type condictions: list
		:return:
		'''
		result = None
		connection = None
		attempts = 0
		statement = self._prepare_select_statement(table_name, params, condictions, limit)
		while result is None and attempts < max_attempts:
			try:
				connection = self.create_connection()
				cursor = self.get_cursor_from_connection(connection)
				result = self.read_data(cursor, statement, values_condictions)
				self.close_connection(connection)
			except Exception as ex:
				self.last_exception = str(ex)
				self.rollback(connection)
				self.close_connection(connection)
				attempts = attempts + 1
				time.sleep(1)
		return result

	def raw_read(self, query_, max_attempts=3):
		'''
		:param table_name:
		:type table_name: str
		:param params:
		:type params: list
		:param condictions:
		:type condictions: list
		:return:
		'''
		result = None
		connection = None
		attempts = 0
		while result is None and attempts < max_attempts:
			try:
				connection = self.create_connection()
				cursor = self.get_cursor_from_connection(connection)
				result = self.read_data(cursor, query_, None)
				self.close_connection(connection)
			except Exception as ex:
				self.last_exception = str(ex)
				self.rollback(connection)
				self.close_connection(connection)
				attempts = attempts + 1
				time.sleep(1)
		return result

	def custom_select_from_table(self, table_name, params, custom_condictions, values_condictions=None, limit=0, max_attempts=3):
		'''
		:param table_name:
		:param params:
		:param custom_condictions:
		:param limit:
		:return:
		'''
		result = None
		connection = None
		attempts = 0
		tmp = self._prepare_select_statement(table_name, params, condictions=None, limit=0)
		statement = '%s %s' % (tmp, custom_condictions)
		while result is None and attempts < max_attempts:
			try:
				connection = self.create_connection()
				cursor = self.get_cursor_from_connection(connection)
				result = self.read_data(cursor, statement, values_condictions)
				self.close_connection(connection)
			except Exception as ex:
				self.rollback(connection)
				self.close_connection(connection)
				self.last_exception = str(ex)
				attempts = attempts + 1
				time.sleep(1)
		return result

	def _prepare_select_statement(self, table_name, params, condictions, limit=0):
		result = self._prepare_selected_parameter_section(params)
		if result and table_name:
			result = result + ' FROM %s ' % table_name
			if condictions:
				result = result + self._prepare_where_condiction(condictions)
			if limit > 0:
				result = result + ' LIMIT %d;' % limit
		return result

	def _prepare_selected_parameter_section(self, params):
		result = None
		if params:
			result = 'SELECT %s ' % params[0]
			for i in range(1, len(params)):
				param = params[i]
				result = result + ',%s ' % param
		return result

	def _prepare_condictions_section(self, condictions):
		result = None
		if condictions:
			keys = list(condictions.keys())
			result = ' WHERE %s=%s ' % (keys[0], condictions[keys[0]])
			for i in range(1, len(keys)):
				key = keys[i]
				result = result + ' and %s=%s ' % (key, condictions[key])
		return result

	def _prepare_where_condiction(self, condictions):
		result = None
		if condictions:
			result = ' WHERE %s=? ' % (condictions[0],)
			for i in range(1, len(condictions)):
				result = result + ' and %s=? ' % condictions[i]
		return result