class Position:
    def __init__(self, latitude: float, longitude: float, name = ""):
        self.latitude, self.longitude, self.name = latitude, longitude, name

    def getPosition(self):
        return (self.latitude, self.longitude)