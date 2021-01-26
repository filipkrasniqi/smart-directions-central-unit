from map.elements.planimetry.point_type import PointType
from map.elements.position import Position
import numpy as np

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

class PoI(Position):
    def __init__(self, idx, x, y, z, name):
        Position.__init__(self, x, y, z, name)
        self.idx = idx
        self.distanceMatrix = None

    def getColor(self):
        return [0, 0, 255]

    def getSelectedColor(self):
        return [0, 128, 255]

    def getObjectType(self):
        return PointType.POI

    def getId(self):
        return "POI_{}".format(self.idx)

    def updateDistanceMatrix(self, floors, level = 0):
        # floors is a matrix. Currently computing the routing for the single
        floorObj = floors[level]
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

    def getDistance(self, position: Position):
        assert self.distanceMatrix is not None, "Init distance matrix first"
        if position is None:
            return float("+inf")
        return self.distanceMatrix[position.x, position.y]

    '''
    
    '''
    def computePathMatrix(self, position: Position):
        assert self.distanceMatrix is not None, "Init distance matrix first"
        pathMatrix = np.zeros(shape=self.distanceMatrix)
        currentPosition, currentDistance = self.getDistance(position), self.distanceMatrix[position.x, position.y]
        pathMatrix[currentPosition.x, currentPosition.y] = currentDistance
        while currentPosition != self:
            neighbours = currentPosition.left(), currentPosition.right(self.distanceMatrix.shape[0]), currentPosition.top(), currentPosition.bottom(self.distanceMatrix.shape[1])
            i = 0
            currentNeighbour = self.getDistance(neighbours[i])
            while currentNeighbour > currentDistance:
                i += 1
                currentNeighbour = self.getDistance(neighbours[i])
            pathMatrix[currentNeighbour.currentPosition.x, currentPosition.y] = currentNeighbour.distance
            currentPosition = currentNeighbour
        return pathMatrix

    def computePathList(self, position: Position):
        assert self.distanceMatrix is not None, "Init distance matrix first"
        currentPosition = SearchPosition(position, self.getDistance(position))
        path = [currentPosition]
        while currentPosition != self:
            neighbours = [currentPosition.left(), currentPosition.right(self.distanceMatrix.shape[0]), \
                         currentPosition.top(), currentPosition.bottom(self.distanceMatrix.shape[1])]
            for neighbour in neighbours:
                if neighbour is not None:
                    neighbour.distance = self.getDistance(neighbour)
            distances = np.array([neighbour.distance if neighbour is not None else float("+inf") for neighbour in neighbours])
            idx = np.argmin(distances)
            currentPosition = neighbours[idx]
            path.append(currentPosition)
        return path

class PoIs:
    def __init__(self, pois = []):
        self.pois = pois
        self.idx_current = 0

    def add(self, poi):
        self.pois.append(poi)

    def __next__(self):
        if self.idx_current < len(self.pois):
            current_poi = self.pois[self.idx_current]
            self.idx_current += 1
            return current_poi
        else:
            self.idx_current = 0
            raise StopIteration

    def __len__(self):
        return len(self.pois)

    def __getitem__(self, i):
        return self.pois[i]

    def updateDistanceMatrix(self, floors, level):
        for poi in self.pois:
            poi.updateDistanceMatrix(floors, level)