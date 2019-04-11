#classe utile ad incapsulare i dati riguardanti gli iframe presenti nella pagina caricata
class IframeInfoContainer:
    def __init__(self, url, width, height, location_x, location_y, is_visible):
        self.url = url
        self.width = width
        self.height = height
        self.location_x = location_x
        self.location_y = location_y
        self.is_visible = is_visible
    def __str__(self):
        return str({"url":self.url,"width":self.width,"height":self.height,"location_x":self.location_x, "location_y":self.location_y,"is_visible":self.is_visible}) 