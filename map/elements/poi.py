from map.elements.planimetry.point_type import PointType
from map.elements.position import Position, SearchPosition
import numpy as np

class PoI(Position):
    def __init__(self, idx, x, y, z, name):
        Position.__init__(self, x, y, z, name)
        self.idx = idx

    def getColor(self):
        return [0, 0, 255]

    def getSelectedColor(self):
        return [0, 128, 255]

    def getObjectType(self):
        return PointType.POI

    def isPoI(self):
        return True

    def getId(self):
        return "POI_{}".format(self.idx)
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

class PoIWithBuilding(PoI):
    def __init__(self, poi: PoI, id_building: int):
        PoI.__init__(self, poi.idx, poi.x, poi.y, poi.z, poi.name)
        self.id_building = id_building

class PoIs:
    def __init__(self, pois):
        self.pois = pois
        self.idx_current = 0

    def add(self, poi):
        self.pois.append(poi)

    def remove(self, poi):
        self.pois.remove(poi)

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