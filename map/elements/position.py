from abc import abstractmethod

import numpy as np


class WithPosition:
    def getPosition(self):
        pass

class Position(WithPosition):
    def __init__(self, x: float, y: float, z: float, name = ""):
        self.x, self.y, self.z, self.name = x, y, z, name
        self.distanceMatrix = None

    def getCoordinates(self):
        return (self.x, self.y, self.z)

    def changePosition(self, x, y):
        self.x, self.y = x, y

    def getPosition(self):
        return self

    def isSameFloor(self, position):
        return self.z == position.z

    def isPoI(self):
        return False

    def isAnchor(self):
        return False

    def isEffector(self):
        return False

    def updateDistanceMatrix(self, floors):
        # floors is a matrix. Currently computing the routing for the single
        floorObj = floors[self.z]
        distanceMatrix = np.ones(shape=floorObj.shape) * -10
        distanceMatrix[self.x, self.y] = 0
        toCheck = set()
        toCheck.add(SearchPosition(self, 0))
        alreadyVisited = set()
        while len(toCheck) > 0:
            # using list to easily get the one with lower distance
            listToCheck = list(toCheck)
            listToCheck.sort(key=lambda x: x.distance)
            currentPosition = listToCheck.pop(0)
            # going back to sets: I want unique vals
            toCheck = set(listToCheck)
            # adding the current position as already visited
            alreadyVisited.add(currentPosition)
            # computing neighbours
            neighbours = set()
            left, right, top, bottom = \
                currentPosition.left(), currentPosition.right(floorObj.shape[0]), \
                currentPosition.top(), currentPosition.bottom(floorObj.shape[1])
            # fill neighbours if they are in the matrix and they are walkable
            if left and floorObj[left.x][left.y] > 0:
                neighbours.add(left)
            if right and floorObj[right.x][right.y] > 0:
                neighbours.add(right)
            if bottom and floorObj[bottom.x][bottom.y] > 0:
                neighbours.add(bottom)
            if top and floorObj[top.x][top.y] > 0:
                neighbours.add(top)
            # add with updated difference into those to be checked. It is a set, so if they are present, they are not added
            distance = currentPosition.distance+1
            for toAdd in neighbours.difference(alreadyVisited):
                if distanceMatrix[toAdd.x, toAdd.y] < 0:
                    distanceMatrix[toAdd.x, toAdd.y] = distance
                toCheck.add(SearchPosition(toAdd, distance))
        self.distanceMatrix = distanceMatrix
        self.distanceMatrix[np.where(self.distanceMatrix == -10)] = float("+inf")

    def computePathList(self, position, floors = None):
        assert self.distanceMatrix is not None or floors is not None, "Init distance matrix first"
        #assert self.distanceMatrix is not None, "Init distance matrix first"
        if self.distanceMatrix is None:
            self.updateDistanceMatrix(floors)
        currentPosition = SearchPosition(position, self.getDistance(position))
        path = [currentPosition]
        #alreadyVisited = set([currentPosition])
        distance = self.getDistance(position)
        while distance > 0:
            neighbours = [currentPosition.left(), currentPosition.right(self.distanceMatrix.shape[0]), \
                         currentPosition.top(), currentPosition.bottom(self.distanceMatrix.shape[1])]
            #neighbours = list(set(neighbours).difference(alreadyVisited))
            #alreadyVisited = alreadyVisited.union(set(neighbours))
            for neighbour in neighbours:
                if neighbour is not None:
                    neighbour.distance = self.getDistance(neighbour)
            distances = np.array([neighbour.distance if neighbour is not None else float("+inf") for neighbour in neighbours])

            idx = np.argmin(distances)
            distance = distances[idx]
            currentPosition = neighbours[idx]
            path.append(currentPosition)
        return path

    def getDistance(self, position):
        assert self.distanceMatrix is not None, "Init distance matrix first"
        if position is None:
            return float("+inf")
        return self.distanceMatrix[position.x, position.y]

    @abstractmethod
    def getColor(self):
        pass

    @abstractmethod
    def getObjectType(self):
        pass

    def getName(self):
        return self.name

    def __str__(self):
        return "{}\nX: {}, Y: {}, Z: {}".format(self.name, self.x, self.y, self.z)

    def __eq__(self, other):
        return isinstance(other, Position) and other.x == self.x and other.y == self.y and other.z == self.z

    @staticmethod
    def computeHash(x, y, z, H=100, W = 10000):
        return (z + y * W + x * H)

    def __hash__(self):
        try:
            self.x = self.x.item()
        except:
            # for some reason sometimes z is an int64 and hash is bothered...
            pass
        try:
            self.y = self.y.item()
        except:
            # for some reason sometimes z is an int64 and hash is bothered...
            pass
        try:
            self.z = self.z.item()
        except:
            # for some reason sometimes z is an int64 and hash is bothered...
            pass
        return Position.computeHash(self.x, self.y, self.z)

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

class PositionOnlinePath(Position):
    def __init__(self, other: Position, distanceSoFar, navigatedFloors):
        super().__init__(other.x, other.y, other.z, other.name)
        self.distanceSoFar, self.navigatedFloors = distanceSoFar, navigatedFloors

class SearchPosition(Position):
    def __init__(self, position: Position, distance):
        Position.__init__(self, position.x, position.y, position.z)
        self.distance = distance

    def left(self):
        position = Position.left(self)
        return None if position is None else SearchPosition(position, distance=self.distance+1)

    def right(self, width):
        position = Position.right(self, width)
        return None if position is None else SearchPosition(position, distance=self.distance+1)

    def bottom(self, height):
        position = Position.bottom(self, height)
        return None if position is None else SearchPosition(position, distance=self.distance+1)

    def top(self):
        position = Position.top(self)
        return None if position is None else SearchPosition(position, distance=self.distance+1)
