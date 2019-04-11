from browsermobproxy import Server


class ProxyDistributor:
	browsermob_proxy_path = "/home/amerigo/PycharmProjects/Progetto/tesi/risorse/browsermob-proxy/bin/browsermob-proxy"

	def __init__(self):
		self.server = Server(self.browsermob_proxy_path)
		self.actual_port = 9090


	def get_new_proxy(self):    
		proxy = self.server.create_proxy({'port':self.actual_port,'captureHeaders': True, 'captureContent': True, 'captureBinaryContent': True})
		self.actual_port += 1
		return proxy

	def start(self):
		if self.server is None:
			self.server = Server(self.browsermob_proxy_path)
		self.server.start()

	def stop(self):
		if self.server is not None:
			self.server.stop()