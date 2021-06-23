import itertools
from enum import Enum, IntEnum

from scipy import ndimage

from map.elements.effector import Effectors, Effector
from map.elements.node import Node
from map.elements.nodes import Nodes
from map.elements.planimetry.point import Point3D, StairPoint3D, LiftPoint3D, ConnectionPoint3D
from map.elements.planimetry.point_type import PointType, Direction, MessageDirection
from map.elements.poi import PoI, PoIs, PoIWithBuilding
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
            kwargs.get('points', None), kwargs.get('name', "")
        self.unique_z_from_file = None

        self.connections, self.floors, self.floorsObjects, self.anchors, self.effectors, self.pois = \
            None, None, None, None, None, None

        is_home, is_antlab, is_edificio11 = kwargs.get('is_home', False), kwargs.get('is_antlab', False), \
                                            kwargs.get('is_edificio11', False)

        if is_home:
            points = Building.home_planimetry()
        elif is_antlab:
            points = Building.antlab_planimetry()
        elif is_edificio11:
            self.init_edificio11()

        Position.__init__(self, x, y, z, name)

        if not is_edificio11:

            # it is None if it is not a static import
            if self.unique_z_from_file is None:
                self.unique_z_from_file = kwargs.get('floors', None)
                if self.unique_z_from_file is not None:
                    self.unique_z_from_file = sorted([round(z, 2) for z in self.unique_z_from_file])

            #self.points: list[Point3D] = points
            self.__initBuilding(points)
        '''
        for floor in range(self.numFloors):
            pois, pivots = self.pois[floor], self.pivots[floor]
            for (poi, pivot) in itertools.product(*[pois, pivots]):
                # TODO non va bene per un cheiz
                position1, position2 = poi.getPosition(), pivot.getPosition()
                self.distanceMatrixPivotsPoIs["{}_{}".format(poi.__hash__(), pivot.__hash__())] = abs(poi.x-pivot.x)+abs(poi.y-pivot-y)
        '''
        # routing table: comprehends distances between each pivot and those to which it is connected

    def build_dict_points(self, points):
        return {p.__hash__() for p in points}

    def initRouting(self):
        # routing table: it's a dict of dicts, s.t. routingTable[poi] = dictAnchor; routingTable[poi][anchor] = nextPoint
        dictAnchors = {anchor: {} for anchor in self.raw_anchors()}
        self.routingTable = {poi: dictAnchors for poi in self.raw_pois()}

        # computing distances for pois - pivots on same floor: comprehends distances between pois and pivots of same floor
        for floor in range(self.numFloors):
            for poi in self.pois[floor]:
                poi.updateDistanceMatrix(self.floors)
            for pivot in self.pivots[floor]:
                pivot.updateDistanceMatrix(self.floors)
            for anchor in self.anchors[floor]:
                anchor.updateDistanceMatrix(self.floors)
            for effector in self.effectors[floor]:
                effector.updateDistanceMatrix(self.floors)

        # initializing the dictionary of the form: key = {<poi>|<effector>|<anchor>-pivot} -> distance
        self.distanceMatrixPoiPivot = {}
        floorsCombination = itertools.product(*[range(self.numFloors),range(self.numFloors)])

        for floor1, floor2 in floorsCombination:
            pois_1, effectors_1, anchors_1 = self.pois[floor1], self.effectors[floor1], self.anchors[floor1]
            pivots2 = self.pivots[floor2]
            for poi, pivot in itertools.product(*[pois_1, pivots2]):
                key = "{}_{}".format(poi.__hash__(), pivot.__hash__())
                if key in self.distanceMatrixPoiPivot:
                    print()
                self.distanceMatrixPoiPivot.update({key: self.computeDistanceAnchorPivot(poi, pivot)})
            for effector, pivot in itertools.product(*[effectors_1, pivots2]):
                key = "{}_{}".format(effector.__hash__(), pivot.__hash__())
                if key in self.distanceMatrixPoiPivot:
                    print()
                self.distanceMatrixPoiPivot.update(
                    {key: self.computeDistanceAnchorPivot(effector, pivot)})
            for anchor, pivot in itertools.product(*[anchors_1, pivots2]):
                key = "{}_{}".format(anchor.__hash__(), pivot.__hash__())
                if key in self.distanceMatrixPoiPivot:
                    print()
                self.distanceMatrixPoiPivot.update(
                    {key: self.computeDistanceAnchorPivot(anchor, pivot)})

        '''
        self.distanceMatrixPoiPivot = {"{}_{}".format(poi.__hash__(), pivot.__hash__()): self.computeDistance(poi, pivot) \
                               for floor1, floor2 in floorsCombination for poi, pivot in
                               itertools.product(*[self.pois[floor1], self.pivots[floor2]])}
        '''

    '''
    Two buildings are equal if they both are instance of Building class and the ID is the same
    '''
    def __eq__(self, other):
        return isinstance(other, Building) and other.getId() == self.id

    '''
    Get the smallest cube that includes all the points of the building 
    '''
    def getMinMaxVals(self, points = None):
        if points is None:
            points = self.points
        x_arr, y_arr, z_arr = \
            [point.x for point in points], \
            [point.y for point in points], \
            [point.z for point in points]

        return min(x_arr), max(x_arr), min(y_arr), max(y_arr), min(z_arr), max(z_arr)
    '''
    Get floor range 
    '''
    def getFloorRange(self):
        min_floor = 0
        max_floor = self.floors.shape[0]
        return min_floor, max_floor

    def size_floor(self):
        minX, maxX, minY, maxY, _, _ = self.getMinMaxVals()
        width, height = (maxX - minX) + 1, (maxY - minY) + 1
        return width, height

    def grid_sizes(self):
        return 5, 5

    @staticmethod
    def grid_intervals(num, size, begin):
        n = num//size
        if n*size != num:
            n += 1
            max_n = n*size
            remaining = max_n-num
            cell_sizes = remaining*[size-1] + (n-remaining) * [size]
        else:
            cell_sizes = [size]*n
        intervals, start_point = [], begin
        for cell_size in cell_sizes:
            intervals.append((start_point, start_point + cell_size - 1))
            start_point += min(cell_size, num-1)
        return intervals

    def horizontal_grid_intervals(self):
        width_grid, _ = self.grid_sizes()
        width, _ = self.size_floor()
        min_x, _, _, _, _, _ = self.getMinMaxVals()
        return Building.grid_intervals(width, width_grid, min_x)

    def vertical_grid_intervals(self):
        _, height_grid = self.grid_sizes()
        _, height = self.size_floor()
        _, _, min_y, _, _, _ = self.getMinMaxVals()
        return Building.grid_intervals(height, height_grid, min_y)

    def get_position_from_grid_number(self, grid_number, floor):
        x_intervals, y_intervals = self.horizontal_grid_intervals(), self.vertical_grid_intervals()
        x_lims = x_intervals[grid_number % len(x_intervals)]
        y_lims = y_intervals[grid_number // len(x_intervals)]
        # TODO in questi range, trovare uno spazio libero, possibilmente al centro; ad ora, forzo con il centro
        start_x_val, start_y_val = (x_lims[0]+x_lims[1])//2, (y_lims[0]+y_lims[1])//2
        #assert self.isValid(x_val, y_val, floor), "WRONG POSITION"
        x_increases, y_increases = [1, -1, 0, 0, 1, -1, 1, -1], [0, 0, 1, -1, 1, 1, -1, -1]
        x_val, y_val = start_x_val, start_y_val
        i = 0
        while i < len(x_increases) and not self.isValid(x_val, y_val, floor):
            x_val, y_val = start_x_val + x_increases[i], start_y_val + y_increases[i]
            i += 1
        assert self.isValid(x_val, y_val, floor), "WRONG POSITION"
        return Position(x_val, y_val, floor)

    def searchPoints(self, x, y, z):
        # TODO currently returning list for previous implementation
        key = Position.computeHash(x, y, z)
        if key in self.dictPoints:
            return [self.dictPoints[key]]
        else:
            print("WARNING: point was not available")
            return []

    def searchPoint(self, x, y, z, className = None):
        points = self.searchPoints(x, y, z)
        if className is not None:
            points = list(filter(lambda x: isinstance(x, className), points))
        if len(points) <= 0:
            return None
        return points[0]

    def searchPivotPoint(self, x, y, floor):
        points = self.searchPoints(x, y, floor)
        if len(points) <= 0:
            return None
        point = points[0]
        if not point.isConnection():
            return None
        point: ConnectionPoint3D = point
        # can be none
        return point.getPivot()

    # Old implementation of searchPivotPoint
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
            if len(size) >= 1:   # true if I have something on this floor
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
                                if point is not None:
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
        if self.unique_z_from_file is None:
            _, nonConnectionPoints = self.split_points_into_connection()
            # init the floors with the Z values. The floor is a transformation into discrete values of Z
            # computing the floors for those points that are not connection ones
            unique_z = set()
            for p in nonConnectionPoints:
                unique_z.add(p.z)
            unique_z = list(unique_z)
            unique_z.sort()
            return unique_z
        else:
            return self.unique_z_from_file

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
            point_between_floors = list(filter(lambda p: minZ <= p.z <= maxZ, self.points))
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

            if len(size) >= 1:   # true if I have something on this floor
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
                            pivotDown = self.searchPivotPoint(x, y, floor)
                            i += 1
                        assert pivotDown is not None, "PIVOT NON ESISTE!!!"
                        i, pivotUp = 0, None
                        xVals, yVals = np.where(intersection_2 > 0)
                        while i < len(xVals) and pivotUp is None:
                            x, y = xVals[i], yVals[i]
                            pivotUp = self.searchPivotPoint(x, y, floor+1)
                            i += 1
                        assert pivotUp is not None, "PIVOT NON ESISTE!!!"
                        pivotDown.setPointUp(pivotUp.getPivot())
                        pivotUp.setPointDown(pivotDown.getPivot())

    def split_points_into_connection(self, points=None):
        if points is None:
            points = self.points
        connection_points, non_connection_points = [], []
        if self.unique_z_from_file is None:
            for p in points:
                if not p.isConnection():
                    non_connection_points.append(p)
                else:
                    connection_points.append(p)
        else:
            for p in points:
                if p.z in self.unique_z_from_file:
                    non_connection_points.append(p)
                else:
                    connection_points.append(p)
        return connection_points, non_connection_points

    def sort_points(self):
        self.points.sort(key=lambda p: p.z * 1000000 + p.y * 10000 + p.x)

    def init_num_floors(self, unique_z):
        self.numFloors = len(unique_z)

    def init_floors(self, nonConnectionPoints, width, height):
        self.floors = np.zeros(shape=(self.numFloors, width, height))
        for p in self.points:
            self.floors[p.floor, p.x, p.y] = PointType.INDOOR.value if p.isIndoor else PointType.OUTDOOR
        p.drawn = True

    def init_floors_old(self, nonConnectionPoints, width, height):
        self.floors = np.zeros(shape=(self.numFloors, width, height))
        for p in nonConnectionPoints:
            self.floors[p.floor, p.x, p.y] = PointType.INDOOR.value if p.isIndoor else PointType.OUTDOOR
        p.drawn = True

    def init_connections(self, width, height):
        self.connections = np.zeros(shape=(self.numFloors, width, height))

    def set_connections(self, connectionPoints):
        for p in connectionPoints:
            if p.floor >= 0:
                self.connections[p.floor, p.x, p.y] = p.pointType()
                p.drawn = True

    def init_dict_points(self):
        # finally I don't need any more updates on the points: put them in dict to speed up search
        self.dictPoints = {}
        # here init dict
        for p in self.points:
            self.dictPoints[p.__hash__()] = p

    def init_pivots(self):
        self.pivots = [[] for _ in range(self.numFloors)]
    '''
    Init the building given the points.
    The output would be a list of floor obj (one for each floor), i.e. matrices having walkable / non-walkable points
    '''
    def __initBuilding(self, points):
        # sort points by (x, y, z). To do that, I need to normalize the value, so that I know how to weight differently
        # the coordinates
        # round all vals of points
        for p in points:
            p.x, p.y, p.z = round(p.x, 2), round(p.y, 2), round(p.z, 2)

        # check if points are too many: if so, sample regularly some (x, y) vals
        # TODO do that only for points of the floors
        if self.unique_z_from_file is not None:
            points_of_floor = [p for p in points if p.z in self.unique_z_from_file]
            unique_x = {p.x: True for p in points_of_floor}
            x_vals = sorted(unique_x.keys())
            if len(x_vals) > 20000:
                sample_period_x = 2
                for i, x in enumerate(x_vals):
                    if i % sample_period_x != 0:
                        unique_x.pop(x)
            unique_y = {p.y: True for p in points_of_floor}
            y_vals = sorted(unique_y.keys())
            if len(y_vals) > 20000:
                sample_period_y = 2
                for i, y in enumerate(y_vals):
                    if i % sample_period_y != 0:
                        unique_y.pop(y)
            for i, p in enumerate(points):
                if p.z in self.unique_z_from_file:
                    if p.x not in unique_x and p.y not in unique_y:
                        points.pop(i)

        self.numFloors = 0
        # min and max for normalization
        minX, maxX, minY, maxY, minZ, maxZ = self.getMinMaxVals(points=points)
        getDeltaOrZero = lambda x1, x2: 1 if x1 == x2 else x1-x2
        deltaX, deltaY, deltaZ = getDeltaOrZero(maxX, minX), getDeltaOrZero(maxY, minY), getDeltaOrZero(maxZ, minZ)
        # first: remove the negative values by summing to each the min val if negative
        for p in points:
            if minX < 0:
                p.x += abs(minX)
            if minY < 0:
                p.y += abs(minY)
            if minZ < 0:
                p.z += abs(minZ)
        if minZ < 0 and self.unique_z_from_file is not None:
            self.unique_z_from_file = [z+abs(minZ) for z in self.unique_z_from_file]
        # recomputation of min, max vals
        minX, maxX, minY, maxY, minZ, maxZ = self.getMinMaxVals(points=points)

        # normalizing points in the range [0, 1]
        for p in points:
            p.x, p.y, p.z = (p.x - minX) / deltaX, \
                            (p.y - minY) / deltaY, \
                            round((p.z - minZ) / deltaZ, 2)
        if self.unique_z_from_file is not None:
            self.unique_z_from_file = [round((z - minZ) / deltaZ, 2) for z in self.unique_z_from_file]

        # init the floors with the Z values. The floor is a transformation into discrete values of Z
        # computing the floors for those points that are not connection ones
        floor_given_z, unique_z = self.dictFloorGivenZ()
        z_given_floor, _ = self.dictZGivenFloor()

        connectionPoints, nonConnectionPoints = self.split_points_into_connection(points=points)

        for p in nonConnectionPoints:
            p.floor = floor_given_z[p.z]

        # sort points by (in order): x, y, z with a weight to be minimized computed as: x + 10*y + 100*z,
        # being x, y, z in the range [0, 1]

        self.points = points
        self.sort_points()
        self.init_num_floors(unique_z)

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

        width, height = self.size_floor()
        # build list of matrices: WxH for each floor
        # self.floors is a list of masks defining whether it is indoor, outdoor or invalid
        self.init_floors(nonConnectionPoints, width, height)

        # this should be defined by color, but there may be no stair point in case color is not defined; if so, all connection points are considered stairs
        # (kinda strong assumption)
        stairPoints = list(filter(lambda x: x.isStair(), connectionPoints))
        if len(stairPoints) <= 0:
            stairPoints = connectionPoints

        self.init_connections(width, height)
        if self.unique_z_from_file is not None:
            # in the current implementation, when reading from file
            # connection points are considered to be stairs
            for p in connectionPoints:
                self.connections[p.floor, p.x, p.y] = PointType.STAIR

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

        self.set_connections(connectionPoints)

        #assert len([p for p in self.points if not p.drawn]) == 0, "Some points are not drawn!"

        # finally I don't need any more updates on the points: put them in dict to speed up search
        self.init_dict_points()
        self.init_pivots()

        # I find the pivot points and assign to the other stair / lift points the corresponding
        self.__assignConnectionsPivot(PointType.STAIR)
        self.__assignConnectionsPivot(PointType.LIFT)

        # clear duplicate points (due to connections)
        self.__clearDuplicatePoints(connectionPoints)

        # compute, for each stair pivot, the connection to other floors
        self.__computeStairConnections(z_given_floor)

        # self.floorsObjects is a list of masks defining, for the valid places, the objects (anchors, effectors, point of interest)
        if self.floorsObjects is None:
            self.floorsObjects = np.zeros(shape=(self.numFloors, width, height))
        if self.anchors is None:
            self.anchors = [Nodes([], None) for _ in range(self.numFloors)]
        if self.effectors is None:
            self.effectors = [Effectors([]) for _ in range(self.numFloors)]
        if self.pois is None:
            self.pois = [PoIs([]) for _ in range(self.numFloors)]


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
            poisAtLevel.updateDistanceMatrix(self.floors)
        for level, anchorsAtLevel in enumerate(self.anchors):
            anchorsAtLevel.updateDistanceMatrix(self.floors)
        for level, effectorsAtLevel in enumerate(self.effectors):
            effectorsAtLevel.updateDistanceMatrix(self.floors)
        # building the routing table (2*)
        # take all pois and anchors
        pois = self.raw_pois()          #[poi for poi in [poisAtLevel for poisAtLevel in self.pois]]
        anchors = self.raw_anchors()    #[anchor for anchor in [anchorsAtLevel for anchorsAtLevel in self.anchors]]
        for poi, anchor in itertools.product(*[pois, anchors]):
            # if on same floor: find first anchor on path, if existing; if not, assign the poi
            if poi.isSameFloor(anchor):
                path = poi.computePathList(anchor, self.floors)
                path_floor = anchor.z
            else:
                # if not, must consider the pivot
                # first: assume that there is an anchor between the anchor itself and the pivot
                pivot = self.get_best_pivot(anchor, poi)
                path = pivot.computePathList(anchor, self.floors)
                path_floor = anchor.z
            try:
                # if assumption is wrong, we fall here;
                # assume that there is an anchor between the end point of the pivot and the poi
                nextAnchor = self.getObjectInPath(path_floor, path, PointType.ANCHOR)
            except:
                assert not poi.isSameFloor(anchor), "Same floor case has already been handled"
                # ASSUMPTION: path does not alternate up and down, so if poi is on upper floor, we only go up
                if poi.z > anchor.z:
                    pivot = pivot.nextPointUp
                else:
                    pivot = pivot.nextPointDown
                if poi.isSameFloor(pivot):
                    path = poi.computePathList(pivot, self.floors)
                    path_floor = poi.z
                else:
                    pivot_2 = self.get_best_pivot(pivot, poi)
                    path = pivot_2.computePathList(pivot, self.floors)
                    path_floor = pivot_2.z
                nextAnchor = self.getObjectInPath(path_floor, path, PointType.ANCHOR)

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

    def computeDistanceAnchorPivot(self, start: Position, destination: ConnectionPoint3D):
        if start.z == destination.z:
            return start.getDistance(destination)
        # TODO bug here: function called for computing distance for different floors (for pivot-pois)
        #   but it always return +inf when different floors, due to distanceSoFar being +inf
        # we only consider paths following the direction monotonically
        isStartPointUp = destination.z < start.z
        candidates = [PositionOnlinePath(destination.getPosition(), 0, 0)]
        visitedCandidates = set()
        distance = float("+inf")
        while len(candidates) > 0:
            candidate = candidates.pop()
            visitedCandidates.add(candidate)
            if candidate.z == start.z:
                distanceCurrentFloor = start.getDistance(candidate)
                distance = min(distance, candidate.distanceSoFar + distanceCurrentFloor)
            else:
                candidatePivots = [p for p in self.pivots[candidate.z] if
                                   p.nextPointUp is not None and isStartPointUp or
                                   p.nextPointDown is not None and not isStartPointUp]

                nextPivotsPosition = []
                for p in candidatePivots:
                    nextPivot = None
                    if p.nextPointUp is not None and isStartPointUp:
                        nextPivot = p.nextPointUp
                    if p.nextPointDown is not None and not isStartPointUp:
                        nextPivot = p.nextPointDown
                    if nextPivot is not None:
                        nextPivotsPosition.append((p, nextPivot))
                '''
                newCandidates = [PositionOnlinePath(p.getPosition(), candidate.distanceSoFar + p.getPosition().getDistance(candidate) + p.connectionLength(), candidate.navigatedFloors + 1) \
                                 for p in nextPivotsPosition]
                                 '''
                '''
                newCandidates = [PositionOnlinePath(p.getPosition(), candidate.distanceSoFar + p.getDistance(candidate) + p.connectionLength(), candidate.navigatedFloors + 1) \
                                 for p in nextPivotsPosition]
                                 '''
                # TODO c'è un problema qui, inizializzo male la distance matrix per i pivot. Sistemare questo per far funzionare ...
                newCandidates = [PositionOnlinePath(p[1].getPosition(), candidate.distanceSoFar + p[0].getDistance(candidate) + p[0].connectionLength(), candidate.navigatedFloors + 1) \
                                 for p in nextPivotsPosition]
                candidates = list(set(candidates).union(set(newCandidates)).difference(visitedCandidates))
                candidates = list(filter(lambda p: p.distanceSoFar < distance, candidates))
                candidates.sort(key = lambda p: p.navigatedFloors)

        return distance

    def deleteObject(self, x, y, z):
        # update building matrix
        self.floorsObjects[z, x, y] = self.floors[z, x, y]
        # delete object
        toDelete = self.getObjectAt(z, (x, y))
        # update instance of effector or whatever
        if toDelete.isEffector():
            self.effectors[toDelete.z].remove(toDelete)
        elif toDelete.isPoI():
            try:
                self.pois[toDelete.z].remove(toDelete)
                self.initRouting()
            except:
                print("WARNING: routing not initialized")
        elif toDelete.isAnchor():
            self.anchors[toDelete.z].remove(toDelete)

    '''
    Given (x, y) 
    Retrieves the poi
    '''
    def getPoi(self, position: Position, floor = 0):
        assert self.floorsObjects[floor][position.x, position.y] == PointType.POI, "Wrong object"
        return self.getObjectAt(floor, position.getCoordinates())

    def findClosestEffectorOnSameFloor(self, point: Position):
        floor = point.z
        distances_current_floor = [point.getDistance(e) for e in self.effectors[floor]]
        assert min(distances_current_floor) != float("+inf"), "Something wrong"
        return self.effectors[floor][np.argmin(distances_current_floor)]

    def findClosestEffector(self, start: Position, destination: Position):
        # TODO bug qui: start.getDistance da inf, quindi non riconosce che quell'effettore non è da considerare
        if start.z == destination.z:
            return self.findClosestEffectorOnSameFloor(start)
        effectors_to_check = self.effectors[start.z]
        floor = start.z
        distances_current_floor = [self.get_distance(start, e) for e in effectors_to_check]
        distance_start_destination = self.get_distance(start, destination)
        distances_effector_destination = [self.get_distance(e, destination) for e in effectors_to_check]

        # TODO distancescurrent_floor are needed to compute the closest effector on the floor
        #  among those that are close enough to the destination!
        #  Distance_effector_destination is needed to understand whether the effector is to be considered or not
        #  but it is not computed properly

        # not considering those having higher distance than the one from the inferenced (start)
        distances_current_floor = [d for d in distances_current_floor]
        update_code = False #if true, does not consider simply the closest
        if update_code:
            for i, d in enumerate(distances_effector_destination):
                if d > distance_start_destination:
                    # make effector invalid: distance from it is higher than going from the anchor
                    distances_current_floor[i] = float("+inf")
        if min(distances_current_floor) == float("+inf"):
            # check effectors of next floor following pivot
            closest_effector = None
            while closest_effector is None:
                # get right pivot for that OD on same floor as start
                pivot = self.get_best_pivot(start, destination)
                # get the next connection point and assign it to pivot
                if start.z > destination.z:
                    pivot = pivot.nextPointDown
                else:
                    pivot = pivot.nextPointUp
                # now we have pivot of next floor: if there is any effector on that floor, take it
                try:
                    closest_effector = self.findClosestEffectorOnSameFloor(pivot)
                    return closest_effector
                except:
                    start = pivot
        else:
            return self.effectors[floor][np.argmin(distances_current_floor)]

    def get_pivot_distance(self, pivot, destination):
        return self.distanceMatrixPoiPivot.get(
            "{}_{}".format(destination.__hash__(), pivot.__hash__()))

    def get_distance(self, point: Position, destination: Position):
        if point.isSameFloor(destination):
            return point.getDistance(destination)
        else:
            pivot = self.get_best_pivot(point, destination)
            return point.getDistance(pivot) + self.get_pivot_distance(pivot, destination)

    '''
    Returns the best pivot for a starting point, given a destination.
    It assumes the pivot is needed (i.e., start and destination are on different floors)
    '''
    def get_best_pivot(self, start, destination):
        pivots = self.pivots[start.z]
        isGoingUp = destination.z > start.z
        distances = [float("+inf") if not((isGoingUp and pivot.nextPointUp) or (not isGoingUp and pivot.nextPointDown)) else pivot.getDistance(start) + self.get_pivot_distance(pivot, destination) for pivot in pivots]

        pivotIdx = np.argmin(distances)
        return pivots[pivotIdx]

    @staticmethod
    def history_from_path(path):
        i = 0
        history_directions = []
        while i < len(path) - 1:
            currentPosition, nextPosition = path[i:i + 2]
            if nextPosition is not None:
                # compute the direction
                xDiffer, yDiffer = currentPosition.x != nextPosition.x, currentPosition.y != nextPosition.y
                right, top = currentPosition.x < nextPosition.x, currentPosition.y < nextPosition.y
                if xDiffer:
                    if right:
                        history_directions.append(Direction.RIGHT)
                    else:
                        history_directions.append(Direction.LEFT)
                else:
                    if top:
                        history_directions.append(Direction.TOP)
                    else:
                        history_directions.append(Direction.BOTTOM)

            i += 1
        return history_directions

    def get_next_pivot(self, start: Position, destination: Position):
        assert start.z != destination.z, "No need for pivot"
        pivot = self.get_best_pivot(start, destination)
        if start.z > destination.z:
            return pivot.nextPointDown
        else:
            return pivot.nextPointUp

    def compute_entire_path_list_from_matrix_OLD(self, start: Position, destination: PoI):
        current_point = start
        path = []
        while not current_point.isSameFloor(destination):
            pivot = self.get_best_pivot(current_point, destination)
            nextPivot = self.get_next_pivot(current_point, destination)
            path += current_point.computePathList(pivot, self.floors)
            current_point = nextPivot
        path += current_point.computePathList(destination, self.floors)
        return path

    def compute_entire_path_list_from_matrix(self, start: Position, destination: PoI):
        current_point = start
        path = []
        reached_destination = False
        while not reached_destination:
            if current_point.isSameFloor(destination):
                next_anchor = self.get_object_from_od(current_point, destination, PointType.ANCHOR)
                if next_anchor and next_anchor.getDistance(destination) < current_point.getDistance(destination):
                    # it means the next anchor is actually in the path
                    next_effector = self.findClosestEffector(next_anchor, destination)
                    if next_effector != current_point:
                        next_point = next_effector
                        path += current_point.computePathList(next_point, self.floors)
                        current_point = next_point
                    else:
                        # it means, even though there is a new anchor, it is not reasonable to follow it
                        reached_destination = True
                        path += current_point.computePathList(destination, self.floors)
                else:
                    # it means, even though there is a new anchor, it is not reasonable to follow it
                    reached_destination = True
                    path += current_point.computePathList(destination, self.floors)
            else:
                next_point = self.get_best_pivot(current_point, destination)
                next_pivot = self.get_next_pivot(current_point, destination)
                next_anchor = self.get_object_from_od(current_point, next_point, PointType.ANCHOR)
                if next_anchor:
                    next_effector = self.findClosestEffector(next_anchor, destination)
                    if current_point != next_effector:
                        next_point = next_effector
                path += current_point.computePathList(next_point, self.floors)
                if not next_anchor:
                    current_point = next_pivot
                else:
                    current_point = next_point

        return path

    def compute_last_path_list_from_matrix(self, start: Position, destination: PoI, num_values = 15):
        return self.compute_entire_path_list_from_matrix(start, destination)[-1*num_values:]

    def compute_first_path_list_from_matrix(self, start: Position, destination: PoI, num_values = 15):
        return self.compute_entire_path_list_from_matrix(start, destination)[:num_values]

    def toActivate(self, start: Position, destination: Position, origin: Position):
        floor = start.z
        effector_to_activate = self.findClosestEffector(start, destination)

        if floor == destination.z:
            # check if it has arrived at destination
            closest_effector_to_destination = self.findClosestEffectorOnSameFloor(destination)

            if closest_effector_to_destination.getId() == effector_to_activate.getId():
                return effector_to_activate, Direction.ALL, MessageDirection.ARRIVED

        path_origin_effector = self.compute_last_path_list_from_matrix(origin, effector_to_activate)
        history_directions = Building.history_from_path(path_origin_effector)
        direction_face = Direction(np.argmax(np.bincount(history_directions)))

        path_effector_destination = self.compute_first_path_list_from_matrix(effector_to_activate, destination)
        history_directions = Building.history_from_path(path_effector_destination)
        absolute_message_to_show = Direction(np.argmax(np.bincount(history_directions)))

        dict_faces = {
            Direction.TOP: Direction.BOTTOM,
            Direction.BOTTOM: Direction.TOP,
            Direction.LEFT: Direction.LEFT,
            Direction.RIGHT: Direction.RIGHT,
        }

        face_to_show = dict_faces[direction_face]

        dict_messages = {
            Direction.TOP: {
                Direction.TOP: MessageDirection.BACK,
                Direction.RIGHT: MessageDirection.RIGHT,
                Direction.BOTTOM: MessageDirection.FORWARD,
                Direction.LEFT: MessageDirection.LEFT
            }, Direction.RIGHT: {
                Direction.TOP: MessageDirection.RIGHT,
                Direction.RIGHT: MessageDirection.FORWARD,
                Direction.BOTTOM: MessageDirection.LEFT,
                Direction.LEFT: MessageDirection.BACK
            }, Direction.BOTTOM: {
                Direction.TOP: MessageDirection.FORWARD,
                Direction.RIGHT: MessageDirection.LEFT,
                Direction.BOTTOM: MessageDirection.BACK,
                Direction.LEFT: MessageDirection.RIGHT
            }, Direction.LEFT: {
                Direction.TOP: MessageDirection.LEFT,
                Direction.RIGHT: MessageDirection.BACK,
                Direction.BOTTOM: MessageDirection.RIGHT,
                Direction.LEFT: MessageDirection.FORWARD
            }
        }
        relative_message_to_show = dict_messages[face_to_show][absolute_message_to_show]
        return effector_to_activate, face_to_show, relative_message_to_show

    def toActivateV2(self, start: Position, destination: Position):
        floor = start.z
        effector_to_activate = self.findClosestEffector(start, destination)

        if floor == destination.z:
            # check if it has arrived at destination
            closest_effector_to_destination = self.findClosestEffectorOnSameFloor(destination)

            if closest_effector_to_destination.getId() == effector_to_activate.getId():
                return effector_to_activate, Direction.ALL, MessageDirection.ARRIVED

        if start.isSameFloor(effector_to_activate):
            path_position_effector = start.computePathList(effector_to_activate, self.floors)
        else:
            nextPivot = self.get_next_pivot(start, effector_to_activate)
            path_position_effector = nextPivot.computePathList(effector_to_activate, self.floors)
        # initializing history directions
        history_directions = Building.history_from_path(path_position_effector)

        direction_face = Direction(np.argmax(np.bincount(history_directions)))

        if effector_to_activate.isSameFloor(destination):
            # reverse it: I want to know path from anchor to poi
            # TODO instead, compute effector_to_activate by executing getClosestObject; remaining is the same
            # effector_to_activate, history_directions, remaining_path = self.getObjectInPath(floor, path, PointType.EFFECTOR)

            path_effector_poi = effector_to_activate.computePathList(destination, self.floors)
            # TODO same goes here
            history_directions = Building.history_from_path(path_effector_poi)
            absolute_message_to_show = Direction(np.argmax(np.bincount(history_directions)))
        else:
            pivotForEffector = self.get_best_pivot(effector_to_activate, destination)

            path_effector_pivot = effector_to_activate.computePathList(pivotForEffector, self.floors)

            history_directions = Building.history_from_path(path_effector_pivot)

            absolute_message_to_show = Direction(np.argmax(np.bincount(history_directions)))
            '''
            path = pivot.computePathList(start, self.floors)
            effector_to_activate, history_directions, remaining_path = self.getObjectInPath(floor, path, PointType.EFFECTOR)
            '''
        # TODO parse this to actual directions

        '''
        # check if we arrived at destination
        if not effector_to_activate or effector_to_activate is None:
            effector_to_activate = self.findClosestEffector(floor, destination)
            face_to_show, relative_message_to_show = Direction.ALL, MessageDirection.ARRIVED
        else:
            # finding face to activate: depends on  history directions
            if len(history_directions) > 0:
                direction_face = Direction(np.argmax(np.bincount(history_directions)))
            else:
                print("WARNING: no history directions")
                direction_face = 0
            # compute the directions with the remaining path
            i = 0
            THRESHOLD_NEXT = 3
            next_directions = []
            remaining_path = destination.computePathList(effector_to_activate, self.floors)
            while i+1 < min(len(remaining_path), THRESHOLD_NEXT):
                currentPosition = remaining_path[i]
                nextPosition = remaining_path[i+1]
                # compute the direction
                xDiffer, yDiffer = currentPosition.x != nextPosition.x, currentPosition.y != nextPosition.y
                right, top = currentPosition.x < nextPosition.x, currentPosition.y < nextPosition.y
                if xDiffer:
                    if right:
                        next_directions.append(Direction.RIGHT)
                    else:
                        next_directions.append(Direction.LEFT)
                else:
                    if top:
                        next_directions.append(Direction.TOP)
                    else:
                        next_directions.append(Direction.BOTTOM)
                    # remove, given the direction, the limits given by the map
                i += 1

            # finding message to show: depends on history directions of the remaining path
            if len(next_directions) > 0:
                absolute_message_to_show = Direction(np.argmax(np.bincount(next_directions)))
            else:
                print("WARNING: no next directions")
                absolute_message_to_show = 0

            dict_faces = {
                Direction.TOP: Direction.BOTTOM,
                Direction.BOTTOM: Direction.TOP,
                Direction.LEFT: Direction.LEFT,
                Direction.RIGHT: Direction.RIGHT,
            }

            face_to_show = dict_faces[direction_face]

            dict_messages = {
                Direction.TOP: {
                    Direction.TOP: MessageDirection.BACK,
                    Direction.RIGHT: MessageDirection.RIGHT,
                    Direction.BOTTOM: MessageDirection.FORWARD,
                    Direction.LEFT: MessageDirection.LEFT
                },Direction.RIGHT: {
                    Direction.TOP: MessageDirection.RIGHT,
                    Direction.RIGHT: MessageDirection.FORWARD,
                    Direction.BOTTOM: MessageDirection.LEFT,
                    Direction.LEFT: MessageDirection.BACK
                },Direction.BOTTOM: {
                    Direction.TOP: MessageDirection.FORWARD,
                    Direction.RIGHT: MessageDirection.LEFT,
                    Direction.BOTTOM: MessageDirection.BACK,
                    Direction.LEFT: MessageDirection.RIGHT
                },Direction.LEFT: {
                    Direction.TOP: MessageDirection.LEFT,
                    Direction.RIGHT: MessageDirection.BACK,
                    Direction.BOTTOM: MessageDirection.RIGHT,
                    Direction.LEFT: MessageDirection.FORWARD
                }
            }
            relative_message_to_show = dict_messages[face_to_show][absolute_message_to_show]
        '''
        dict_faces = {
            Direction.TOP: Direction.BOTTOM,
            Direction.BOTTOM: Direction.TOP,
            Direction.LEFT: Direction.LEFT,
            Direction.RIGHT: Direction.RIGHT,
        }

        face_to_show = dict_faces[direction_face]

        dict_messages = {
            Direction.TOP: {
                Direction.TOP: MessageDirection.BACK,
                Direction.RIGHT: MessageDirection.RIGHT,
                Direction.BOTTOM: MessageDirection.FORWARD,
                Direction.LEFT: MessageDirection.LEFT
            }, Direction.RIGHT: {
                Direction.TOP: MessageDirection.RIGHT,
                Direction.RIGHT: MessageDirection.FORWARD,
                Direction.BOTTOM: MessageDirection.LEFT,
                Direction.LEFT: MessageDirection.BACK
            }, Direction.BOTTOM: {
                Direction.TOP: MessageDirection.FORWARD,
                Direction.RIGHT: MessageDirection.LEFT,
                Direction.BOTTOM: MessageDirection.BACK,
                Direction.LEFT: MessageDirection.RIGHT
            }, Direction.LEFT: {
                Direction.TOP: MessageDirection.LEFT,
                Direction.RIGHT: MessageDirection.BACK,
                Direction.BOTTOM: MessageDirection.RIGHT,
                Direction.LEFT: MessageDirection.FORWARD
            }
        }
        relative_message_to_show = dict_messages[face_to_show][absolute_message_to_show]
        return effector_to_activate, face_to_show, relative_message_to_show

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
        return self.floors[floor, x, y] > 0 and not PointType.isConnection(self.floorsObjects[floor, x, y] )

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
                if self.isValid(i, j, floor) and (i,j, floor) not in toAvoid:
                    return (i,j)

    '''
    Iterates the floor matrix from (0,0) to (width, height) and returns the first valid position for that floor
    '''
    def findFirstValidCoordinateInGrid(self, floor, position_in_grid):
        matrix = self.floorsObjects[floor]
        toAvoid = self.getUsedPositions(floor)
        for i, row in enumerate(matrix):
            for j, cell in enumerate(row):
                if self.isValid(i, j, floor) and (i,j, floor) not in toAvoid:
                    return (i,j)
    '''
    Adds an anchor to the floor at the first available position
    '''
    def addAnchor(self, floor, anchor = None):
        if anchor is None:
            validCoordinates = self.findFirstValidCoordinate(floor)
        else:
            validCoordinates = anchor.x, anchor.y
        anchors = self.anchors[floor]

        number_of_anchors = 0
        for iter_floor in range(len(self.anchors)):
            number_of_anchors += len(self.anchors[iter_floor])

        if anchor is None:
            anchor = Node(number_of_anchors, validCoordinates[0], validCoordinates[1], floor, "Ancora {}".format(len(anchors)), "RNDM")

        x, y = anchor.x, anchor.y
        anchors.add(anchor)
        self.floorsObjects[floor, x, y] = PointType.ANCHOR

    '''
    Adds an effector to the floor at the first available position
    '''
    def addEffector(self, floor, effector = None):
        if effector is None:
            validCoordinates = self.findFirstValidCoordinate(floor)
            mac = "RNDM"
        else:
            validCoordinates = effector.x, effector.y
            mac = effector.mac
        effectors = self.effectors[floor]

        number_of_effectors = 0
        for iter_floor in range(len(self.effectors)):
            number_of_effectors += len(self.effectors[iter_floor])

        effectors.add(Effector(number_of_effectors, validCoordinates[0], validCoordinates[1], floor, "Effettore {}".format(len(effectors)), mac))
        self.floorsObjects[floor, validCoordinates[0], validCoordinates[1]] = PointType.EFFECTOR

    '''
    Adds a PoI to the floor at the first available position
    '''
    def addPoI(self, floor):
        validCoordinates = self.findFirstValidCoordinate(floor)
        pois = self.pois[floor]

        number_of_pois = 0

        for iter_floor in range(len(self.pois)):
            number_of_pois += len(self.pois[iter_floor])
        
        pois.add(PoI(number_of_pois, validCoordinates[0], validCoordinates[1], floor, "PoI {}".format(len(pois))))
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
    TODO now it is implemented in s.w.t. it will find only one type of object; with this assumption, we have to insert an effector at the POI position or similar. 
            In any case we need to check if a POI is reached
            
    TODO should be updated with the multilevel concept
    '''
    def getObjectInPath_OLD(self, numFloor, path, objectType, thresholdClose = 2, threshold_history = 5):
        floor = self.floorsObjects[numFloor]
        width, height = floor.shape
        i, objectToRetrieve = 0, False
        history_directions = []
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
                        history_directions.append(Direction.RIGHT)
                    else:
                        maxX = currentPosition.x
                        history_directions.append(Direction.LEFT)
                else:
                    if top:
                        minY = currentPosition.y
                        history_directions.append(Direction.TOP)
                    else:
                        maxY = currentPosition.y
                        history_directions.append(Direction.BOTTOM)
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

        if objectType == PointType.EFFECTOR or objectType == PointType.POI:
            #history_directions = path[:i]
            remaining_path = path[i:]
            if len(history_directions) > threshold_history:
                history_directions = history_directions[i-threshold_history:]
            return objectToRetrieve, history_directions, remaining_path
        else:
            return objectToRetrieve

    def getObjectInPath(self, numFloor, path, objectType, thresholdClose = 4):
        floor = self.floorsObjects[numFloor]
        width, height = floor.shape
        i, objectToRetrieve = 0, False
        history_directions = []
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
                        history_directions.append(Direction.RIGHT)
                    else:
                        maxX = currentPosition.x
                        history_directions.append(Direction.LEFT)
                else:
                    if top:
                        minY = currentPosition.y
                        history_directions.append(Direction.TOP)
                    else:
                        maxY = currentPosition.y
                        history_directions.append(Direction.BOTTOM)
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

    def get_object_from_od(self, start: Position, destination: Position, objectType):
        assert start.isSameFloor(destination), "Must be in same floor"
        path = start.computePathList(destination, self.floors)
        return self.getObjectInPath(start.z, path, objectType)

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
        return val1, val2, val3

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

    @staticmethod
    def antlab_planimetry():
        points: list[Point3D] = []
        z_const = 1
        # primo corridoio
        for x in range(0, 12):
            for y in range(0, 2):
                points.append(Point3D(x, y, z_const, True))
        # secondo corridoio
        for x in range(0, 12):
            for y in range(4, 6):
                points.append(Point3D(x, y, z_const, True))
        # terzo corridoio
        for x in range(0, 12):
            for y in range(8, 10):
                points.append(Point3D(x, y, z_const, True))
        # corridoio verticale
        for x in range(5, 7):
            for y in range(0, 10):
                points.append(Point3D(x, y, z_const, True))

        for x in range(0, 12):
            for y in range(11, 14):
                points.append(Point3D(x, y, z_const, True))

        # porte
        points.append(Point3D(1, 10, z_const, True))
        points.append(Point3D(2, 10, z_const, True))
        return points

    def init_edificio11(self):
        dict_points = {}

        points_to_add = {
            0: {
                "points": [
                    [0, 10, 0, 70],
                ],
                "stairs": [
                    [0, 10, 60, 70],
                ]
            },
            1: {
                "points": [
                    [0, 10, 70, 90],
                    [0, 30, 80, 90],
                    [20, 30, 70, 80],
                    [30, 40, 80, 90],
                ],
                "stairs": [
                    [0, 10, 70, 80],
                    [20, 30, 70, 80]
                ]
            },
            2: {
                "points": [
                    [20, 30, 50, 60],
                    [20, 30, 30, 50],
                    [0, 30, 40, 60]
                ],
                "stairs": [
                    [20, 30, 50, 60]
                ]
            }
        }

        for floor in points_to_add.keys():
            blocks_points = points_to_add[floor]["points"]
            for (x1, x2, y1, y2) in blocks_points:
                for x in range(x1, x2):
                    for y in range(y1, y2):
                        p = Point3D(x, y, floor, True)
                        p.floor = floor
                        dict_points[p.__hash__()] = p
            stair_points = points_to_add[floor]["stairs"]

            for (x1, x2, y1, y2) in stair_points:
                for x in range(x1, x2):
                    for y in range(y1, y2):
                        key = Position.computeHash(x, y, floor)
                        if key in dict_points:
                            p = StairPoint3D(x, y, floor, True)
                            p.floor = floor
                            dict_points[key] = p

        self.points = list(dict_points.values())
        self.unique_z_from_file = [0, 1, 2]

        connectionPoints, nonConnectionPoints = [], []
        for p in self.points:
            if p.isConnection():
                connectionPoints.append(p)
            else:
                nonConnectionPoints.append(p)

        width, height = self.size_floor()

        self.sort_points()
        self.init_num_floors(self.unique_z_from_file)
        self.init_floors(nonConnectionPoints, width, height)
        self.init_connections(width, height)
        self.set_connections(connectionPoints)

        # assert len([p for p in self.points if not p.drawn]) == 0, "Some points are not drawn!"

        # finally I don't need any more updates on the points: put them in dict to speed up search
        self.init_dict_points()
        self.init_pivots()

        # I find the pivot points and assign to the other stair / lift points the corresponding
        self.__assignConnectionsPivot(PointType.STAIR)
        self.__assignConnectionsPivot(PointType.LIFT)

        pivotFirstFloor = self.pivots[0][0]
        pivotSecondFloorToFirst = self.pivots[1][0]
        pivotSecondFloorToThird = self.pivots[1][1]
        pivotThirdFloor = self.pivots[2][0]

        pivotFirstFloor.setPointUp(pivotSecondFloorToFirst)

        pivotSecondFloorToFirst.setPointDown(pivotFirstFloor)
        pivotSecondFloorToThird.setPointUp(pivotThirdFloor)

        pivotThirdFloor.setPointDown(pivotSecondFloorToThird)

        if self.floorsObjects is None:
            self.floorsObjects = np.zeros(shape=(self.numFloors, width, height))
        if self.anchors is None:
            self.anchors = [Nodes([], None) for _ in range(self.numFloors)]
        if self.effectors is None:
            self.effectors = [Effectors([]) for _ in range(self.numFloors)]
        if self.pois is None:
            self.pois = [PoIs([]) for _ in range(self.numFloors)]



    def get_anchors(self, floor = None):
        if floor is None:
            return self.raw_anchors()
        else:
            return self.anchors[floor]

    def get_effectors(self, floor = None):
        if floor is None:
            return self.raw_effectors()
        else:
            return self.effectors[floor]

    def clean_anchors(self):
        self.anchors = [Nodes([], None) for _ in range(self.numFloors)]
        idxs = self.floorsObjects==PointType.ANCHOR
        self.floorsObjects[idxs] = self.floors[idxs]

    def raw_pois(self):
        pois = []
        for row_pois in self.pois:
            for p in row_pois:
                pois.append(PoIWithBuilding(p, self.id))
        return pois

    def raw_anchors(self):
        anchors = []
        for row_anchors in self.anchors:
            anchors += row_anchors
        return anchors

    def get_new_anchor_id(self):
        num_anchors = len(self.raw_anchors())
        return num_anchors

    def raw_effectors(self):
        effectors = []
        for row_effectors in self.effectors:
            effectors += row_effectors
        return effectors

    def getInvalidIndices(self):
        invalids = np.argwhere(self.floors == PointType.INVALID)
        dict_invalids = [[] for _ in range(self.floors.shape[0])]
        for invalid in invalids:
            point_xy = invalid[1:]
            dict_invalids[invalid[0]].append({"x": int(point_xy[0]), "y": int(point_xy[1])})
        return dict_invalids

    def findPoI(self, idx_poi):
        pois = self.raw_pois()
        return [p for p in pois if p.idx == idx_poi][0]
