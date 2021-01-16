from enum import Enum, IntEnum

from map.elements.effector import Effectors, Effector
from map.elements.node import Node
from map.elements.nodes import Nodes
from map.elements.planimetry.point import Point3D
from map.elements.planimetry.point_type import PointType
from map.elements.poi import PoI, PoIs
from map.elements.position import Position

import bisect
import numpy as np

class Building(Position):
    def __init__(self, id, latitude: float, longitude: float, points, name = ""):
        self.id = id
        Position.__init__(self, latitude, longitude, name)
        # init everything: floors, sort points
        self.__initBuilding(points)

    '''
    Two buildings are equal if they both are instance of Building class and the ID is the same
    '''
    def __eq__(self, other):
        return isinstance(other, Building) and other.getId() == self.id

    '''
    Get the smallest cube that includes all the points of the building 
    '''
    def getMinMaxVals(self):
        x_arr, y_arr, z_arr = \
            [point.x for point in self.points], \
            [point.y for point in self.points], \
            [point.z for point in self.points]

        return min(x_arr), max(x_arr), min(y_arr), max(y_arr), min(z_arr), max(z_arr)

    '''
    Init the building given the points
    '''
    def __initBuilding(self, points):
        # sort points by (x, y, z). To do that, I need to normalize the value, so that I know how to weight differently
        # the coordinates
        self.points: list[Point3D] = points
        self.numFloors = 0
        # min and max for normalization
        minX, maxX, minY, maxY, minZ, maxZ = self.getMinMaxVals()
        # normalizing points in the range [0, 1]
        for p in self.points:
            p.x, p.y, p.z = (p.x - minX) / (maxX - minX), \
                            (p.y - minY) / (maxY - minY), \
                            (p.z - minZ) / (maxZ - minZ)

        # sort points by (in order): x, y, z with a weight to be minimized computed as: x + 10*y + 100*z,
        # being x, y, z in the range [0, 1]
        self.points.sort(key=lambda p: p.x + p.y * 10 + p.z * 100)
        # init the floors with the Z values. The floor is a transformation into discrete values of Z
        current_floor = -1
        previous = -1
        for p in self.points:
            if previous != p.z:
                current_floor += 1
            p.floor, previous = current_floor, p.z
        self.numFloors = current_floor + 1
        # I compute the same transformation for X and Y, so that x € [0, W], y € [0, H]
        unique_x, unique_y, currentX, currentY = [], [], -1, -1
        for p in self.points:
            try:
                idx_x = unique_x.index(p.x)
            except:
                idx_x = -1
            try:
                idx_y = unique_y.index(p.y)
            except:
                idx_y = -1
            if idx_x < 0:
                bisect.insort(unique_x, p.x)
                currentX += 1
                idx_x = currentX
            if idx_y < 0:
                bisect.insort(unique_y, p.y)
                currentY += 1
                idx_y = currentY
            p.x, p.y = idx_x, idx_y
        # build list of matrices: WxH for each floor
        minX, maxX, minY, maxY, minZ, maxZ = self.getMinMaxVals()
        width, height = (maxX - minX) + 1, (maxY - minY) + 1
        # self.floors is a list of masks defining whether it is indoor, outdoor or invalid
        self.floors = np.zeros(shape=(self.numFloors, width, height))
        for p in self.points:
            self.floors[p.floor, p.x, p.y] = PointType.INDOOR.value if p.isIndoor else PointType.OUTDOOR
        # self.floorsObjects is a list of masks defining, for the valid places, the objects (anchors, effectors, point of interest)
        self.floorsObjects = np.zeros(shape=(self.numFloors, width, height))
        self.anchors, self.effectors, self.pois = [Nodes() for _ in range(self.numFloors)],\
                                                  [Effectors() for _ in range(self.numFloors)],\
                                                  [PoIs() for _ in range(self.numFloors)]

    '''
    Return the indoor / outdoor mask for 
    '''
    def getFloor(self, idx):
        return self.floors[idx]

    '''
    Return whether a specific cell is valid (i.e., is an indoor / outdoor space or not)
    '''
    def isValid(self, x, y, floor):
        return self.floors[floor, x, y] > 0

    '''
    Returns ID for the building
    '''
    def getId(self):
        return self.id

    '''
    Returns an object given the position in terms of [x, y]
    '''
    def getObjectAt(self, floor, position):
        objectType = self.getObjectTypeAt(floor, position[0], position[1])
        if objectType == PointType.ANCHOR:
            toChange = self.anchors[floor]
        elif objectType == PointType.EFFECTOR:
            toChange = self.effectors[floor]
        else:
            toChange = self.pois[floor]
        i, found = 0, False
        while i < len(toChange) and not found:
            otherPosition = toChange[i].getPosition()
            if otherPosition[0] == position[0] and otherPosition[1] == position[1]:
                found = True
            else:
                i += 1
        assert found, "WARNING: no value"
        return toChange[i]

    '''
    Given a floor and two positions (in terms of [x,y]), with the first associated with an object,
    it updates such position with the second one.
    '''
    def changeObjectPosition(self, floor, oldPosition, newPosition):
        # find object at old position
        toChange = self.getObjectAt(floor, oldPosition)
        currentPosition = toChange.getPosition()
        previousType = self.floorsObjects[floor, currentPosition[0], currentPosition[1]]
        self.floorsObjects[floor, currentPosition[0], currentPosition[1]] = PointType.INVALID
        toChange.changePosition(newPosition[0], newPosition[1])
        self.floorsObjects[floor, newPosition[0], newPosition[1]] = previousType

    '''
    Returns true if an object is present at the given coordinates [x,y] at the given floor
    '''
    def isOccupied(self, x, y, floor):
        return PointType.isObject(self.floorsObjects[floor, x, y])

    '''
    Returns all the position associated with an object for the given floor
    '''
    def getUsedPositions(self, floor):
        usedPositions = [p.getPosition() for p in self.anchors[floor].nodes+self.effectors[floor].effectors+self.pois[floor].pois]
        return usedPositions

    '''
    Iterates the floor matrix from (0,0) to (width, height) and returns the first valid position for that floor
    '''
    def findFirstValidCoordinate(self, floor):
        matrix = self.floorsObjects[floor]
        toAvoid = self.getUsedPositions(floor)
        for i, row in enumerate(matrix):
            for j, cell in enumerate(row):
                if self.isValid(i, j, floor) and (i,j) not in toAvoid:
                    return (i,j)

    '''
    Adds an anchor to the floor at the first available position
    '''
    def addAnchor(self, floor):
        validCoordinates = self.findFirstValidCoordinate(floor)
        anchors = self.anchors[floor]
        anchors.add(Node(len(anchors), validCoordinates[0], validCoordinates[1], "Ancora {}".format(len(anchors)), "RNDM"))
        self.floorsObjects[floor, validCoordinates[0], validCoordinates[1]] = PointType.ANCHOR

    '''
    Adds an effector to the floor at the first available position
    '''
    def addEffector(self, floor):
        validCoordinates = self.findFirstValidCoordinate(floor)
        effectors = self.effectors[floor]
        effectors.add(Effector(len(effectors), validCoordinates[0], validCoordinates[1], "Effettore {}".format(len(effectors)), "RNDM"))
        self.floorsObjects[floor, validCoordinates[0], validCoordinates[1]] = PointType.EFFECTOR

    '''
    Adds a PoI to the floor at the first available position
    '''
    def addPoI(self, floor):
        validCoordinates = self.findFirstValidCoordinate(floor)
        pois = self.pois[floor]
        pois.add(PoI(len(pois), validCoordinates[0], validCoordinates[1], "PoI {}".format(len(pois))))
        self.floorsObjects[floor, validCoordinates[0], validCoordinates[1]] = PointType.POI

    '''
    Given a floor and a position [x,y], it returns a list of close objects 
    (close means in the surroundings of the thresholdClose variable)
    '''
    def getCloseObjects(self, numFloor, x, y):
        thresholdClose = 2
        floor = self.floorsObjects[numFloor]
        width, height = floor.shape
        objs = []
        for i in range(max(0, x-thresholdClose), min(x+thresholdClose, width)):
            for j in range(max(0, y-thresholdClose), min(y+thresholdClose, height)):
                cell = floor[i, j]
                if cell >= 3:
                    objs.append(cell)
        return objs

    '''
    Given a floor and the position (i,j), returns the object type at that position.
    If the position is not associated with an object, it returns also whether the position is indoor or outdoor.
    '''
    def getObjectTypeAt(self, numFloor, i, j):
        val = self.floorsObjects[numFloor, i, j]
        if val <= 0:
            return self.floors[numFloor, i, j]
        else:
            return val

    '''
    Returns the number of floors of the building
    '''
    def getNumberFloors(self):
        return len(self.floors)

    def __str__(self):
        return "{}".format(self.name)

