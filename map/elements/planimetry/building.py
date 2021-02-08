import itertools
from enum import Enum, IntEnum

from scipy import ndimage

from map.elements.effector import Effectors, Effector
from map.elements.node import Node
from map.elements.nodes import Nodes
from map.elements.planimetry.point import Point3D, StairPoint3D, LiftPoint3D, ConnectionPoint3D
from map.elements.planimetry.point_type import PointType
from map.elements.poi import PoI, PoIs
from map.elements.position import Position, PositionOnlinePath

import bisect
import numpy as np
import scipy

from scipy.spatial import distance_matrix

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
        self.connections, self.floors, self.floorsObjects, self.anchors, self.effectors, self.pois = \
            None, None, None, None, None, None
        # inits anchors, effectors, pois, ...
        self.__initBuilding(points)
        # TODO here I potentially could build the distance matrix also among different floors
        '''
        for floor in range(self.numFloors):
            pois, pivots = self.pois[floor], self.pivots[floor]
            for (poi, pivot) in itertools.product(*[pois, pivots]):
                # TODO non va bene per un cheiz
                position1, position2 = poi.getPosition(), pivot.getPosition()
                self.distanceMatrixPivotsPoIs["{}_{}".format(poi.__hash__(), pivot.__hash__())] = abs(poi.x-pivot.x)+abs(poi.y-pivot-y)
        '''
        # routing table: comprehends distances between each pivot and those to which it is connected

    def initRouting(self):
        # routing table: it's a dict of dicts, s.t. routingTable[poi] = dictAnchor; routingTable[poi][anchor] = nextPoint
        dictAnchors = {anchor: {} for anchor in self.anchors}
        self.routingTable = {poi: dictAnchors for poi in self.pois}

        # computing distances for pois - pivots on same floor: comprehends distances between pois and pivots of same floor
        for floor in range(self.numFloors):
            for poi in self.pois[floor]:
                poi.getPosition().updateDistanceMatrix(self.floors)
            for pivot in self.pivots[floor]:
                pivot.getPosition().updateDistanceMatrix(self.floors)

        floorsCombination = itertools.product(*[range(self.numFloors),range(self.numFloors)])

        # initializing the dictionary of the form: key = <poi> - <anchor> -> distance
        self.distanceMatrixPoiPivot = {"{}_{}".format(poi.__hash__(), pivot.__hash__()): self.computeDistance(poi, pivot) \
                               for floor1, floor2 in floorsCombination for poi, pivot in
                               itertools.product(*[self.pois[floor1], self.pivots[floor2]])}

        '''
        for floor in range(self.numFloors):
            self.distanceMatrix[]
        '''

        # TODO sono in un ancora; ho poi; controllo piani: se sono uguali, poi.computeDistance;
        # TODO se sono diversi: decido a quale scala devo andare, attivo il primo effettore disponibile,
        # TODO e trovo il nodo che si dovrà a

        '''
        self.distanceMatrixAnchorPivot = {}
        for floorAnchor, floorPoi in floorsCombination:
            anchor, poi = self.anchors[floorAnchor], self.pois[floorPoi]
            if floorAnchor == floorPoi:
                # I am simply checking the distance between anchors and pois of same floor
                self.distanceMatrixAnchorPivot.update("{}_{}".format(anchor, poi),
                                                      poi.getPosition().getDistance(anchor))
            else:
                # compute all distances anchor - pivot + ...
                pivots = self.pivots[floorAnchor]
                distance = np.min()
        '''
        # TODO

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

    def searchPoints(self, x, y, z):
        points = [p for p in self.points if p.__hash__() == Position.computeHash(x, y, z)]
        assert len(points) > 0, 'Point not found'
        return points

    def searchPoint(self, x, y, z, className = None):
        points = self.searchPoints(x, y, z)
        if className is not None:
            points = list(filter(lambda x: isinstance(x, className), points))
        return None if len(points) <= 0 else points[0]

    def searchPointFromPivotList(self, x, y, floor):
        pivots = self.pivots[floor]
        points = [p for p in pivots if p.x == x and p.y == y]
        point = None
        if len(points) > 0:
            point = points[0]
        return point

    def searchPointFromDict(self, x, y, floor):
        hashVal = Position.computeHash(x, y, floor)
        point = self.dictPoints.get(hashVal, None)
        return point

    '''
    Given a type of search (STAIR or LIFT)
    Algorithm sets cells in connections as PIVOT by finding the center of mass of each group.
    That will be the point that is checked for shortest path when searching a connection
    '''
    def __assignConnectionsPivot(self, typeToSearch: PointType, z_given_floor = None):
        assert self.connections is not None, "First init building"
        assert PointType.isConnection(typeToSearch), "Connection point required"
        if z_given_floor is None:
            z_given_floor = self.dictZGivenFloor()
        typeToSet = PointType.STAIR_PIVOT if typeToSearch == PointType.STAIR else PointType.LIFT_PIVOT
        className = StairPoint3D if typeToSearch == PointType.STAIR else LiftPoint3D

        for floor in range(self.connections.shape[0]):
            connectionPoints = self.connections[floor] == typeToSearch
            # we compute the groups
            uniqueGroupsIdxs, _ = ndimage.label(connectionPoints)
            size = np.bincount(uniqueGroupsIdxs.ravel())
            if len(size) > 1:   # true if I have something on this floor
                biggestIdx = uniqueGroupsIdxs.max()
                for labelNum in range(biggestIdx):
                    clumpVal = labelNum+1
                    # finding approximate center of max
                    centerOfMass = ndimage.center_of_mass(connectionPoints, uniqueGroupsIdxs, clumpVal)
                    # to int
                    centerOfMass = (int(centerOfMass[0]), int(centerOfMass[1]))
                    # computing actual distances from the CM.
                    # We start by defining the distance to non-stair values: +inf
                    dm = np.ones(shape=connectionPoints.shape)*np.inf
                    dm[connectionPoints] = 1
                    # distancesFromCM will contain the distances from each point of the map wrt the CoM
                    distancesFromCM = np.array([abs(int(cellPos/connectionPoints.shape[1])-centerOfMass[0])+abs(int(cellPos%connectionPoints.shape[1])-centerOfMass[1]) for cellPos in range(connectionPoints.shape[0]*connectionPoints.shape[1])]).reshape(connectionPoints.shape)
                    # finally we compute the intersection (inf*k=inf)
                    dm = np.multiply(dm, distancesFromCM)
                    # and we get the coordinates of a valid CoM (closest stair point)
                    centerOfMass = np.unravel_index(dm.argmin(), dm.shape)
                    self.connections[floor][centerOfMass] = typeToSet
                    pivotPoint = self.searchPoint(centerOfMass[0], centerOfMass[1], floor, className)

                    self.pivots[floor].append(pivotPoint)

                    # for each point of the uniqueGroup, assign the pivot point
                    for x in range(uniqueGroupsIdxs.shape[0]):
                        for y in range(uniqueGroupsIdxs.shape[1]):
                            if uniqueGroupsIdxs[x, y] == clumpVal:
                                point = self.searchPoint(x, y, floor, ConnectionPoint3D)
                                point.setPivot(pivotPoint)

    '''
    Duplicate points are removed.
    They may appear due to stairs being in between floors.
    '''
    def __clearDuplicatePoints(self, connectionPoints = None):
        if connectionPoints is None:
            connectionPoints = list(filter(lambda x: x.isConnection(), self.points))
        hashVals = {}
        for p in connectionPoints:
            hashVals.update({p.__hash__(): True})
        # then I check, among the non-connection points, the duplicates, and I remove them
        for p in self.points:
            if p in hashVals and not p.isConnection():
                self.points.remove(p)
            hashVals.update({p.__hash__(): True})

    '''
    Returns z values associated to any floor.
    It does that by taking all distinct z values related to non connection points
    '''
    def floorUniqueZ(self):
        nonConnectionPoints = list(filter(lambda x: not x.isConnection(), self.points))
        # init the floors with the Z values. The floor is a transformation into discrete values of Z
        # computing the floors for those points that are not connection ones
        unique_z = set()
        for p in nonConnectionPoints:
            unique_z.add(p.z)
        unique_z = list(unique_z)
        unique_z.sort()
        return unique_z

    '''
    Returns a dict having floor value as key pointing at the corresponding z
    '''
    def dictZGivenFloor(self):
        unique_z = self.floorUniqueZ()
        return {i: z for i, z in enumerate(unique_z)}, unique_z

    '''
    Returns a dict having Z value as key pointing at the corresponding floor
    '''
    def dictFloorGivenZ(self):
        unique_z = self.floorUniqueZ()
        return {z: i for i, z in enumerate(unique_z)}, unique_z

    '''
    For each stair pivot, computes where it brings
    '''
    def __computeStairConnections(self, z_given_floor = None):
        if z_given_floor is None:
            z_given_floor = self.dictZGivenFloor()

        # find the corresponding end points for each connection point
        for floor in range(self.numFloors-1):
            minZ, maxZ = z_given_floor[floor], z_given_floor[floor+1]
            point_between_floors = list(filter(lambda p: minZ < p.z < maxZ, self.points))
            # consider them as flattened to the floor and compute the intersection
            # so build a matrix with them
            stairsFlattened = np.zeros(shape=self.floors[0].shape)
            for p in point_between_floors:
                stairsFlattened[p.x, p.y] = 1
            # compute groups
            connectionPoints = stairsFlattened == 1
            # we compute the groups
            uniqueGroupsIdxs, _ = ndimage.label(connectionPoints)
            size = np.bincount(uniqueGroupsIdxs.ravel())

            if len(size) > 1:   # true if I have something on this floor
                biggestIdx = uniqueGroupsIdxs.max()
                for labelNum in range(biggestIdx):
                    clumpVal = labelNum+1
                    group = uniqueGroupsIdxs == clumpVal
                    conn_1, conn_2 = self.connections[floor] > 0, self.connections[floor+1] > 0
                    intersection_1, intersection_2 = \
                        np.multiply(group, conn_1), np.multiply(group, conn_2)
                    numIntersections1, numIntersections2 = intersection_1.sum(), intersection_2.sum()
                    if numIntersections1 > 0 and numIntersections2 > 0:
                        xVals, yVals = np.where(intersection_1 > 0)
                        # find one point of intersection having the pivot
                        i, pivotDown = 0, None
                        while i < len(xVals) and pivotDown is None:
                            x, y = xVals[i], yVals[i]
                            pivotDown = self.searchPointFromPivotList(x, y, floor)
                            i += 1
                        assert pivotDown is not None, "PIVOT NON ESISTE!!!"
                        i, pivotUp = 0, None
                        xVals, yVals = np.where(intersection_2 > 0)
                        while i < len(xVals) and pivotUp is None:
                            x, y = xVals[i], yVals[i]
                            pivotUp = self.searchPointFromPivotList(x, y, floor+1)
                            i += 1
                        assert pivotUp is not None, "PIVOT NON ESISTE!!!"
                        pivotDown.setPointUp(pivotUp.getPivot())
                        pivotUp.setPointDown(pivotDown.getPivot())


    '''
    Init the building given the points.
    The output would be a list of floor obj (one for each floor), i.e. matrices having walkable / non-walkable points
    '''
    def __initBuilding(self, points):
        # sort points by (x, y, z). To do that, I need to normalize the value, so that I know how to weight differently
        # the coordinates
        self.points: list[Point3D] = points
        # round all vals of points
        for p in self.points:
            p.x, p.y, p.z = round(p.x, 2), round(p.y, 2), round(p.z, 2)
        self.numFloors = 0
        # min and max for normalization
        minX, maxX, minY, maxY, minZ, maxZ = self.getMinMaxVals()
        getDeltaOrZero = lambda x1, x2: 1 if x1 == x2 else x1-x2
        deltaX, deltaY, deltaZ = getDeltaOrZero(maxX, minX), getDeltaOrZero(maxY, minY), getDeltaOrZero(maxZ, minZ)
        # first: remove the negative values by summing to each the min val if negative
        for p in self.points:
            if minX < 0:
                p.x += abs(minX)
            if minY < 0:
                p.y += abs(minY)
            if minZ < 0:
                p.z += abs(minZ)
        # recomputation of min, max vals
        minX, maxX, minY, maxY, minZ, maxZ = self.getMinMaxVals()

        # normalizing points in the range [0, 1]
        for p in self.points:
            p.x, p.y, p.z = (p.x - minX) / deltaX, \
                            (p.y - minY) / deltaY, \
                            round((p.z - minZ) / deltaZ, 2)

        # filter out points that refer to stairs / lifts: they are not relevant
        nonConnectionPoints = list(filter(lambda x: not x.isConnection(), self.points))
        # init the floors with the Z values. The floor is a transformation into discrete values of Z
        # computing the floors for those points that are not connection ones
        floor_given_z, unique_z = self.dictFloorGivenZ()
        z_given_floor, _ = self.dictZGivenFloor()

        for p in nonConnectionPoints:
            p.floor = floor_given_z[p.z]

        # sort points by (in order): x, y, z with a weight to be minimized computed as: x + 10*y + 100*z,
        # being x, y, z in the range [0, 1]
        self.points.sort(key=lambda p: p.z * 10000000000 + p.y * 100000 + p.x)
        self.numFloors = len(unique_z)
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
            if idx_y < 0:
                bisect.insort(unique_y, p.y)
                currentY += 1
            # updating x and y with corresponding value of index; we change the SdR to natural numbers

        # assign to points values in new SdR
        for p in self.points:
            p.x, p.y = unique_x.index(p.x), unique_y.index(p.y)

        minX, maxX, minY, maxY, minZ, maxZ = self.getMinMaxVals()
        width, height = (maxX - minX) + 1, (maxY - minY) + 1
        # build list of matrices: WxH for each floor
        # self.floors is a list of masks defining whether it is indoor, outdoor or invalid
        self.floors = np.zeros(shape=(self.numFloors, width, height))
        for p in nonConnectionPoints:
            self.floors[p.floor, p.x, p.y] = PointType.INDOOR.value if p.isIndoor else PointType.OUTDOOR
            p.drawn = True

        connectionPoints = list(filter(lambda x: x.isConnection(), self.points))
        stairPoints = list(filter(lambda x: x.isStair(), connectionPoints))

        self.connections = np.zeros(shape=(self.numFloors, width, height))
        unique_zStairs = list(set([p.z for p in stairPoints]))
        unique_zStairs.sort()
        dictStairZFloors = {}
        isUpDictStair = {}

        for floor, zPoint in enumerate(unique_z):
            diffsWithSign = [(round(abs(zPoint - zStairPoint), 3), zPoint < zStairPoint) for zStairPoint in unique_zStairs]   # second attribute tells whether it's going down or up
            absDiffs, isUpList = [d[0] for d in diffsWithSign], [d[1] for d in diffsWithSign]
            THRESHOLD = 0.1
            validStairPoints = [i for i, d in enumerate(absDiffs) if d < THRESHOLD]
            for idx in validStairPoints:
                dictStairZFloors[unique_zStairs[idx]] = floor
                isUpDictStair[unique_zStairs[idx]] = isUpList[idx]

        for p in connectionPoints:
            added = False
            # this should be the lifts...
            if p.z in floor_given_z:
                p.floor = floor_given_z[p.z]
                added = True
            # ... and this the stairs
            if not added and p.z in dictStairZFloors:
                p.floor = dictStairZFloors[p.z]
                if p.isStair():
                    p.setNextFloor(isUpDictStair[p.z])

        for p in connectionPoints:
            if p.floor >= 0:
                self.connections[p.floor, p.x, p.y] = p.pointType()
                p.drawn = True

        assert len([p for p in self.points if not p.drawn]) == 0, "Some points are not drawn!"

        self.pivots = [[] for _ in range(self.numFloors)]

        self.dictPoints = {}
        # here init dict
        for p in connectionPoints:
            isOnFloor = floor_given_z.get(p.z, -1) > 0
            if isOnFloor:
                self.dictPoints[p.__hash__()] = p

        # I find the pivot points and assign to the other stair / lift points the corresponding
        self.__assignConnectionsPivot(PointType.STAIR)
        self.__assignConnectionsPivot(PointType.LIFT)

        # clear duplicate points (due to connections)
        self.__clearDuplicatePoints(connectionPoints)

        # compute, for each stair pivot, the connection to other floors
        self.__computeStairConnections(z_given_floor)

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
    def computeOfflineMapForFloor(self):
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
                self.routingTable[poi][anchor] = nextAnchor
            else:
                self.routingTable[poi][anchor] = poi
        # now we have a routing table of the form: <key> = anchor -> <value> = anchor | poi
        # TODO goal would be to build another routing table that has: <key> = (anchor, poi) -> <value> = <direction> (LEFT, TOP, RIGHT, BOTTOM)\
        #  but this information depends too much on the orientation of the user, thus it's better to think about this

    def computeEntireOfflineMap(self):
        for anchor, poi in itertools.product(*[self.anchors, self.pois]):
            pass#self.routingTable[poi][anchor] = self.nextOnlinePath(anchor.getPosition(), poi.getPosition())

    def computeDistance(self, start: Position, destination: Position):
        candidates = [PositionOnlinePath(destination.getPosition(), 0, 0)]
        visitedCandidates = set()
        distance = float("+inf")
        while len(candidates) > 0:
            candidate = candidates.pop()
            visitedCandidates.add(candidate)
            if candidate.z == start.z:
                distanceCurrentFloor = start.getDistance(candidate)
                distance = min(distance, candidate.distanceSoFar + distanceCurrentFloor)

            candidatePivots = self.pivots[candidate.z]
            nextPivotsPosition = []
            for p in candidatePivots:
                if p.nextPointUp is not None:
                    nextPivotsPosition.append(p.nextPointUp)
                if p.nextPointDown is not None:
                    nextPivotsPosition.append(p.nextPointDown)

            newCandidates = [PositionOnlinePath(p.getPosition(), candidate.distanceSoFar + p.getPosition().getDistance(candidate) + p.connectionLength(), candidate.navigatedFloors+1) \
                             for p in nextPivotsPosition]
            candidates = list(set(candidates).union(set(newCandidates)).difference(visitedCandidates))
            candidates = list(filter(lambda p: p.distanceSoFar < distance, candidates))
            candidates.sort(key = lambda p: p.navigatedFloors)

        return distance

    def deleteObject(self, x, y, z):
        toDelete = self.getObjectAt(z, (x, y))
        if toDelete.isEffector():
            self.effectors[toDelete.z].remove(toDelete)
        elif toDelete.isPoI():
            self.pois[toDelete.z].remove(toDelete)
            self.initRouting()
        elif toDelete.isAnchor():
            self.anchors[toDelete.z].remove(toDelete)

    '''
    Given (x, y) 
    Retrieves the poi
    '''
    def getPoi(self, position: Position, floor = 0):
        assert self.floorsObjects[floor][position.x, position.y] == PointType.POI, "Wrong object"
        return self.getObjectAt(floor, position.getCoordinates())

    '''
    Given start position and destination to reach (a PoI)
    Returns the effector to activate
    '''
    def toActivateSameFloor(self, position: Position, destination: Position, numFloor):
        poi: PoI = self.getPoi(destination)
        path = poi.computePathList(position)
        effectorToActivate = self.getObjectInPath(numFloor, path, PointType.EFFECTOR)
        return effectorToActivate

    def toActivate(self, start: Position, destination: Position):
        if start.isSameFloor(destination):
            path = destination.computePathList(start)
            effectorToActivate = self.getObjectInPath(start.z, path, PointType.EFFECTOR)
        else:
            pivots = self.pivots[start.z]
            distances = [pivot.getPosition().getDistance(start) + self.distanceMatrixPoiPivot.get(
                "{}_{}".format(destination.__hash__(), pivot.__hash__())) for pivot in pivots]
            pivotIdx = np.argmin(distances)
            pivot = pivots[pivotIdx].getPosition()
            path = pivot.computePathList(start)
            effectorToActivate = self.getObjectInPath(start.z, path, PointType.EFFECTOR)
        if effectorToActivate is None:
            print("WARNING: effettore non presente")
        # TODO we should retrieve the direction depending on <whatever>
        return effectorToActivate

    '''
    Return the indoor / outdoor mask for the points indoor / outdoor
    '''
    def getFloor(self, idx):
        return self.floors[idx]

    '''
    Return the indoor / outdoor mask for the connections
    '''
    def getConnectionsMatrix(self, idx):
        return self.connections[idx]

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

    def __hash__(self):
        return self.getId()

    '''
    Returns an object given the position in terms of [x, y]
    '''
    def getObjectAt(self, floor, position):
        objectType = self.getObjectTypeAt(position[0], position[1], floor)
        if objectType == PointType.ANCHOR:
            toChange = self.anchors[floor]
        elif objectType == PointType.EFFECTOR:
            toChange = self.effectors[floor]
        else:
            toChange = self.pois[floor]
        i, found = 0, False
        while i < len(toChange) and not found:
            otherPosition = toChange[i].getCoordinates()
            if otherPosition[0] == position[0] and otherPosition[1] == position[1] and toChange[i].z == floor:
                found = True
            else:
                i += 1
        assert found, "WARNING: no value"
        return toChange[i]

    '''
    Search for connection object from the pivot list, assuming x,y,z are associated with a pivot object
    '''
    def getConnectionAt(self, x, y, z):
        return self.searchPointFromPivotList(x, y, z)

    def getConnectionTypeAt(self, x, y, floor):
        return self.connections[floor, x, y]
    '''
    Given a floor and two positions (in terms of [x,y]), with the first associated with an object,
    it updates such position with the second one.
    '''
    def changeObjectPosition(self, floor, oldPosition, newPosition):
        # find object at old position
        toChange = self.getObjectAt(floor, oldPosition)
        currentPosition = toChange.getCoordinates()
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
        usedPositions = [p.getCoordinates() for p in self.anchors[floor].nodes + self.effectors[floor].effectors + self.pois[floor].pois]
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
    def getObjectInPath(self, numFloor, path, objectType, thresholdClose = 2):
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
    def getObjectTypeAt(self, i, j, numFloor):
        val, _, _ = self.getCellInfoAt(numFloor, i, j)
        if val <= 0:
            return self.floors[numFloor, i, j]
        else:
            return val

    def getCellInfoAt(self, numFloor, i, j):
        val1 = self.floorsObjects[numFloor, i, j]
        val2 = self.floors[numFloor, i, j]
        val3 = self.connections[numFloor, i, j]
        return (val1, val2, val3)

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

