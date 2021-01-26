from abc import abstractmethod


class Position:
    def __init__(self, x: float, y: float, z: float, name = ""):
        self.x, self.y, self.z, self.name = x, y, z, name

    def getPosition(self):
        return (self.x, self.y)

    def changePosition(self, x, y):
        self.x, self.y = x, y

    @abstractmethod
    def getColor(self):
        pass

    @abstractmethod
    def getObjectType(self):
        pass

    def getName(self):
        return self.name

    def __str__(self):
        return "{}\nX: {}, Y: {}".format(self.name, self.x, self.y)

    def __eq__(self, other):
        return isinstance(other, Position) and other.x == self.x and other.y == self.y and other.z == self.z

    def __hash__(self):
        return "{}_{}_{}".format(self.x, self.y, self.z)

    def left(self):
        if self.x-1 >= 0:
            return Position(self.x-1, self.y, self.z)
        else:
            return None
    def right(self, width):
        if self.x+1 < width:
            return Position(self.x+1, self.y, self.z)
        else:
            return None
    def bottom(self, height):
        if self.y+1 < height:
            return Position(self.x, self.y+1, self.z)
        else:
            return None
    def top(self):
        if self.y-1 >= 0:
            return Position(self.x, self.y-1, self.z)
        else:
            return None

    @abstractmethod
    def getSelectedColor(self):
        pass

    @abstractmethod
    def getId(self):
        pass