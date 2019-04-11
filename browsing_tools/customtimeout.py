import threading
import time


class CustomTimeout(object):

	def __init__(self, args, sec, function_handler):
		self.args = args
		self.sec = sec
		self.function_handler = function_handler
		self.sec_remaining = sec
		self._current_thread = None
		self.active = False
		self.running = True
		self.temp_args = None
		self._current_thread = threading.Thread(target=self._run)
		self._current_thread.start()

	def start_countdown(self, temp_args):
		if self.active:
			print("Errore: si sta provando ad avviare un timer già avviato")
		else:
			self.temp_args = temp_args
			self.reset_countdown()
			self.active = True

	def _run(self):
		while self.running:
			time.sleep(0.1)
			if self.active:
				self.sec_remaining -= 0.1
				if self.sec_remaining <= 0:
					self.function_handler(self.args, self.temp_args)
					self.active = False
			#print("browser_id: " + self.args + "sec rimanenti: " + str(self.sec_remaining))

	def stop_countdown(self):
		self.active = False
		# self._stop_current_thread()
		# time.sleep(0.3)

	def reset_countdown(self):
		self.active = False
		self.sec_remaining = self.sec

	def _stop_current_thread(self):
		self.active = False
