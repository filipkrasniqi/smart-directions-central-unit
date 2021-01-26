import itertools
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

# TODO gestire multi livello
class Building(Position):
    '''
    Each floor has its own SdR, that in a 2x2 matrix it would be:
    (0,0)   (1,0)
    (0,1)   (1,1)
    '''
    def __init__(self, **kwargs):
        self.id, x, y, z, points, name = \
            kwargs.get('id', -1), kwargs.get('x', 0), kwargs.get('y', 0), kwargs.get('z', 0), \
            kwargs.get('points', Building.home_planimetry()), kwargs.get('name', "")
        Position.__init__(self, x, y, z, name)
        # init everything: floors, sort points
        self.routingTable = {}
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
    Init the building given the points.
    The output would be a list of floor obj (one for each floor), i.e. matrices having walkable / non-walkable points
    '''
    def __initBuilding(self, points):
        # sort points by (x, y, z). To do that, I need to normalize the value, so that I know how to weight differently
        # the coordinates
        self.points: list[Point3D] = points
        self.numFloors = 0
        # min and max for normalization
        minX, maxX, minY, maxY, minZ, maxZ = self.getMinMaxVals()
        getDeltaOrZero = lambda x1, x2: 1 if x1 == x2 else x1-x2
        deltaX, deltaY, deltaZ = getDeltaOrZero(maxX, minX), getDeltaOrZero(maxY, minY), getDeltaOrZero(maxZ, minZ)
        # normalizing points in the range [0, 1]
        for p in self.points:
            p.x, p.y, p.z = (p.x - minX) / deltaX, \
                            (p.y - minY) / deltaY, \
                            (p.z - minZ) / deltaZ

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
    Builds the routing table for SD purposes.
    The routing table consists of a matrix NxP, being N = |anchors|, P = |pois|.
    For each pair (anchor, poi), we save the next anchor to reach OR the poi itself.
    We first compute, for each poi, the distance matrix (1*) for each level.
    We use this information to compute the path given a position in the map. Such path is useful for:
    - retrieving the effector in the path (i.e., to activate), given a pair (position, poi). Position can be an anchor
    - building the routing table, as we simply enumerate all the anchors and pois, compute the path, and retrieve the 
        closest anchor in the path (2*).
    Last thing we need to compute, is the direction to communicate.
    '''
    def computeOfflineMap(self):
        # for each poi, compute the DISTANCE MATRIX (1*)
        for level, poisAtLevel in enumerate(self.pois):
            poisAtLevel.updateDistanceMatrix(self.floors, level)
        # building the routing table (2*)
        # take all pois and anchors
        pois = [poi for poi in [poisAtLevel for poisAtLevel in self.pois]]
        anchors = [anchor for anchor in [anchorsAtLevel for anchorsAtLevel in self.anchors]]
        for poi, anchor in itertools.product(*[pois, anchors]):
            path = poi.computePathList(anchor)
            # TODO here I should check the level: should I return the value when computing the path???
            nextAnchor = self.getObjectInPath(level, path, PointType.ANCHOR)
            # anchor is assigned iff there exists something in the middle. If not, it assigns the poi
            if nextAnchor:
                self.routingTable[anchor] = nextAnchor
            else:
                self.routingTable[anchor] = poi
        # now we have a routing table of the form: <key> = anchor -> <value> = anchor | poi
        # TODO goal would be to build another routing table that has: <key> = (anchor, poi) -> <value> = <direction> (LEFT, TOP, RIGHT, BOTTOM)\
        #  but this information depends too much on the orientation of the user, thus it's better to think about this


    '''
    Given (x, y) 
    Retrieves the poi
    '''
    def getPoi(self, position: Position, floor = 0):
        assert self.floorsObjects[floor][position.x, position.y] == PointType.POI, "Wrong object"
        return self.getObjectAt(floor, position.getPosition())

    '''
    Given start position and destination to reach (a PoI)
    Returns the effector to activate
    '''
    def toActivate(self, position: Position, destination: Position, numFloor):
        poi: PoI = self.getPoi(destination)
        path = poi.computePathList(position)
        effectorToActivate = self.getObjectInPath(numFloor, path, PointType.EFFECTOR)
        # TODO retrieve the direction
        return effectorToActivate

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
        anchors.add(Node(len(anchors), validCoordinates[0], validCoordinates[1], floor, "Ancora {}".format(len(anchors)), "RNDM"))
        self.floorsObjects[floor, validCoordinates[0], validCoordinates[1]] = PointType.ANCHOR

    '''
    Adds an effector to the floor at the first available position
    '''
    def addEffector(self, floor):
        validCoordinates = self.findFirstValidCoordinate(floor)
        effectors = self.effectors[floor]
        effectors.add(Effector(len(effectors), validCoordinates[0], validCoordinates[1], floor, "Effettore {}".format(len(effectors)), "RNDM"))
        self.floorsObjects[floor, validCoordinates[0], validCoordinates[1]] = PointType.EFFECTOR

    '''
    Adds a PoI to the floor at the first available position
    '''
    def addPoI(self, floor):
        validCoordinates = self.findFirstValidCoordinate(floor)
        pois = self.pois[floor]
        pois.add(PoI(len(pois), validCoordinates[0], validCoordinates[1], floor, "PoI {}".format(len(pois))))
        self.floorsObjects[floor, validCoordinates[0], validCoordinates[1]] = PointType.POI

    '''
    Given a floor and a position [x,y], it returns a list of close objects 
    (close means in the surroundings of the thresholdClose variable)
    '''
    def getCloseObjects(self, numFloor, x, y, thresholdClose = 1):
        floor = self.floorsObjects[numFloor]
        width, height = floor.shape
        objs = []
        for i in range(max(0, x-thresholdClose), min(x+thresholdClose, width)):
            for j in range(max(0, y-thresholdClose), min(y+thresholdClose, height)):
                cell = floor[i, j]
                if PointType.isObject(cell):
                    objs.append(cell)
        return objs

    '''
    Given floor, path in the floor and object type (e.g.: effector) to check
    Returns the object instance.
    TODO should be updated with the multilevel concept
    '''
    def getObjectInPath(self, numFloor, path, objectType, thresholdClose = 1):
        floor = self.floorsObjects[numFloor]
        width, height = floor.shape
        i, objectToRetrieve = 0, False
        while not objectToRetrieve and i < len(path):
            currentPosition = path[i]
            # improving the algorithm by checking the next direction: we don't want to check objs that were located in previous part of the path
            if i+1 < len(path):
                nextPosition = path[i+1]
                # first: take the square that is built from the position in the path
                minX, maxX, minY, maxY = currentPosition.x - thresholdClose, currentPosition.x + thresholdClose, currentPosition.y - thresholdClose, currentPosition.y + thresholdClose
                # compute the direction
                xDiffer, yDiffer = currentPosition.x != nextPosition.x, currentPosition.y != nextPosition.y
                right, top = currentPosition.x < nextPosition.x, currentPosition.y < nextPosition.y
                if xDiffer:
                    if right:
                        minX = currentPosition.x
                    else:
                        maxX = currentPosition.x
                else:
                    if top:
                        minY = currentPosition.y
                    else:
                        maxY = currentPosition.y
                # remove, given the direction, the limits given by the map
                minX, maxX, minY, maxY = max(0, minX), min(width, maxX), max(0, minY), min(height, maxY)
            else:
                # shouldn't reach here, but if so, I simply take everything in the surroundings
                minX, maxX = max(0, currentPosition.x - thresholdClose), min(width, currentPosition.x + thresholdClose)
                minY, maxY = max(0, currentPosition.y - thresholdClose), min(height, currentPosition.y + thresholdClose)
            neighboursMatrix = floor[minX:maxX, minY:maxY]
            # find in the mask any (x, y) s.t. it is an objectToRetrieve. If not present, keep going
            cols, rows = np.nonzero(neighboursMatrix == objectType)
            if len(cols) > 0:
                objectToRetrieve = self.getObjectAt(numFloor, (cols[0]+minX, rows[0]+minY))
            else:
                i += 1
        return objectToRetrieve

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

    @staticmethod
    def home_planimetry():
        points: list[Point3D] = []
        z_const = 1
        # soggiorno
        for x in range(0, 8):
            for y in range(0, 5):
                points.append(Point3D(x, y, z_const, True))
        # cucina
        for x in range(0, 6):
            for y in range(6, 8):
                points.append(Point3D(x, y, z_const, True))
        # corridoio ingresso - cucina
        for x in range(4, 13):
            points.append(Point3D(x, 5, z_const, True))
        # ingresso
        for x in range(8, 13):
            for y in range(6, 8):
                points.append(Point3D(x, y, z_const, True))
        # porte
        points.append(Point3D(4, 10, z_const, True))
        points.append(Point3D(7, 10, z_const, True))
        points.append(Point3D(11, 10, z_const, True))
        points.append(Point3D(8, 8, z_const, True))
        # corridoio + bagno
        for x in range(0, 13):
            points.append(Point3D(x, 9, z_const, True))
        # camera 1 (grande)
        for x in range(0, 5):
            for y in range(11, 15):
                points.append(Point3D(x, y, z_const, True))
        # camera 2
        for x in range(7, 9):
            for y in range(11, 15):
                points.append(Point3D(x, y, z_const, True))
        # camera 3
        for x in range(11, 13):
            for y in range(11, 15):
                points.append(Point3D(x, y, z_const, True))
        return points

