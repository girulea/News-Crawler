import datetime
import re2 as re
import whois
import utils
class WhoisInfo:
	def __init__(self):
		self.creation_date = None
		self.updated_date = None
		self.expiration_date = None
		self.status = True
		self.address = None
		self.org = None
		self.city = None
		self.country = None
		self.zipcode = None
		self.state = None

	# #metodo che restituisce l'età del sito in giorni. Per età del sito si intende i giorni trascorsi dalla registrazione del dominio ad oggi
	# def calculate_age(self):
	# 	current = datetime.datetime.now()
	# 	if len(self.creation_date) == 0 or (len(self.creation_date) > 0 and self.creation_date[0] is None):
	# 		result = -1 #il -1 è stato scelto per evitare, anche se improbabili, casi in cui un sito è stato registrato lo stesso giorno in cui viene visitato
	# 	else:
	# 		result = (current - min(self.creation_date)).days
	# 	return result
	#
	# #metodo che restituisce la durata dell'aggiornamento in giorni
	# def calculate_lifetime_updates(self):
	# 	result = -1
	# 	if len(self.updated_date) != 0 and len(self.expiration_date) != 0:
	# 		if( self.expiration_date[0] is not None and self.updated_date[0] is not None):
	# 			result = (max(self.expiration_date) - max(self.updated_date)).days
	# 	return result

	#metodo statico che permette di creare un oggetto WhoisInfo partendo dall'url passato nei parametri.
	#1) Interroga il whois db
	#2) Si occupa di creare l'oggetto whois e di popolare i campi che sono registrati
	#3) restistuisce l'oggetto creato
	@staticmethod
	def create_whois_container(url):
		domain_info = None
		try:
			domain_info = whois.whois(url)
		except:
			pass
		#print(domain)
		info = WhoisInfo()
		if domain_info:
			WhoisInfo._manage_creation_date(domain_info, info)

			if 'updated_date' in domain_info:
				if not isinstance(domain_info['updated_date'], list):
					info.updated_date = domain_info['updated_date']
				else:
					info.updated_date = max(domain_info['updated_date'])

			if 'expiration_date' in domain_info:
				if not isinstance(domain_info['expiration_date'], list):
					info.expiration_date = domain_info['expiration_date']
				else:
					info.expiration_date = max(domain_info['expiration_date'])

			if 'address' in domain_info:
				if isinstance(domain_info['address'], list):
					info.address = domain_info['address'][0]
				else:
					info.address = domain_info['address']

			if 'org' in domain_info:
				if isinstance(domain_info['org'], list):
					info.org = domain_info['org'][0]
				else:
					info.org = domain_info['org']

			if 'city' in domain_info:
				if isinstance(domain_info['city'], list):
					info.city = domain_info['city'][0]
				else:
					info.city = domain_info['city']

			if 'country' in domain_info:
				if isinstance(domain_info['country'], list):
					info.country = domain_info['country'][0]
				else:
					info.country = domain_info['country']

			if 'zipcode' in domain_info:
				if isinstance(domain_info['zipcode'], list):
					info.zipcode = domain_info['zipcode'][0]
				else:
					info.zipcode = domain_info['zipcode']

			if 'state' in domain_info:
				if isinstance(domain_info['state'], list):
					info.state = domain_info['state'][0]
				else:
					info.state = domain_info['state']

			if 'status' in domain_info:
				status = domain_info['status']
				if isinstance(status, list):
					status = status[0]
				info.status = status
		return info

	@staticmethod
	def _manage_creation_date(domain_info, result):
		if 'creation_date' in domain_info:
			if not isinstance(domain_info['creation_date'], list):
				result.creation_date = domain_info['creation_date']
			else:
				result.creation_date = min(domain_info['creation_date'])

		# match_res = re.findall(r'Registrant(\n(?:\s{2}.*\:?.*\n)*)', domain_info.text, re.MULTILINE)
		# for m in match_res:
		# 	sub_match = re.findall('(.*):\s*(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', m, re.MULTILINE)
		# 	for s_m in sub_match:
		# 		if 'Created' in s_m[0]:
		# 			result.creation_date = utils.parse_date_str(s_m[1])
		# 			return