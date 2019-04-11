#classe per incapsulare i dati raccolti durante lo 'scraping' delle risorse caricate dalla pagina
class HttpRequest:
    def __init__(self,url, response_status, redirect_URL, mime_type, is_advertising):
        self.url = url
        self.response_status = response_status
        self.redirect_URL = redirect_URL
        self.mime_type = mime_type
        self.is_advertising = is_advertising