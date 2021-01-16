from abc import abstractmethod


class Position:
    def __init__(self, latitude: float, longitude: float, name = ""):
        self.latitude, self.longitude, self.name = latitude, longitude, name

    def getPosition(self):
        return (self.latitude, self.longitude)

    def changePosition(self, latitude, longitude):
        self.latitude, self.longitude = latitude, longitude

    @abstractmethod
    def getColor(self):
        pass

    @abstractmethod
    def getObjectType(self):
        pass

    def getName(self):
        return self.name

    def __str__(self):
        return "{}\nX: {}, Y: {}".format(self.name, self.longitude, self.latitude)

    @abstractmethod
    def getSelectedColor(self):
        pass

    @abstractmethod
    def getId(self):
        pass