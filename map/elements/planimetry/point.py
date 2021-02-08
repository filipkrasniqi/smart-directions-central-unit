import numpy as np

from map.elements.planimetry.point_type import PointType
from map.elements.position import Position, WithPosition


class Point3D(WithPosition):
    def __init__(self, x, y, z, isIndoor):
        self.x, self.y, self.z, self.isIndoor = x, y, z, isIndoor
        self.floor = -1
        self.drawn = False
        self.position = None

    def getPosition(self):
        if self.position is None:
            self.position = self.initPosition()
        return self.position

    def initPosition(self):
        return Position(self.x, self.y, self.floor)
    '''
    Hash is unique if values are normalized; if not, that is not true anymore
    '''
    def __hash__(self):
        return Position.computeHash(self.x, self.y, self.floor)

    def __eq__(self, other):
        return isinstance(other, Point3D) and other.x == self.x and other.y == self.y and other.floor == self.floor

    def __str__(self):
        return "(X, Y) = {}, {}\nPIANO: {}".format(self.x, self.y, self.floor)

    @staticmethod
    def buildPoint(x, y, z, isIndoor, isLectureRoom, isWideArea, isHallway, isStair, isToilet, isLift):
        if isStair:
            return StairPoint3D(x, y, z, isIndoor)
        elif isLectureRoom:
            return LectureRoomPoint3D(x, y, z, isIndoor)
        elif isWideArea:
            return WideAreaPoint3D(x, y, z, isIndoor)
        elif isHallway:
            return HallwayPoint3D(x, y, z, isIndoor)
        elif isToilet:
            return ToiletPoint3D(x, y, z, isIndoor)
        elif isLift:
            return LiftPoint3D(x, y, z, isIndoor)
        else:
            return Point3D(x, y, z, isIndoor)

    def pointFloorUp(self, nextZ):
        return Point3D(self.x, self.y, nextZ)

    def isStair(self):
        return False

    def isLift(self):
        return False

    def isWideArea(self):
        return False

    def isLectureRoom(self):
        return False

    def isToilet(self):
        return False

    def isHallway(self):
        return False

    def isConnection(self):
        return self.isStair() or self.isLift()

    def pointType(self):
        if self.isStair():
            return PointType.STAIR
        elif self.isLift():
            return PointType.LIFT

        if self.isIndoor:
            return PointType.INDOOR
        else:
            return PointType.OUTDOOR

class ConnectionPoint3D(Point3D):
    def __init__(self, x, y, z, isIndoor):
        super().__init__(x, y, z, isIndoor)
        self.nextFloor = -1
        self.pivot = None
        self.nextPointUp, self.nextPointDown = None, None

    # TODO this could consider the length of the stairs (e.g.: number of points going up and down)
    # TODO while for lifts this could be less
    def connectionLength(self):
        return 10

    # we assume floors are connected to floor+1 or floor-1
    def setNextFloor(self, isUp):
        self.nextFloor = self.floor + (1 if isUp else -1)

    def setPivot(self, point):
        self.pivot = point

    def isPivot(self):
        assert self.pivot is not None, 'Pivot shouldn\'t be none'
        return self.pivot == self

    def getPivot(self):
        return self.pivot

    def setPointUp(self, nextNode):
        if not self.isPivot():
            self.pivot.setPointUp(nextNode)
        else:
            self.nextPointUp = nextNode

    def __str__(self):
        val = super().__str__()
        if self.nextPointUp is not None:
            val += "\nUp: {} {} {}".format(self.nextPointUp.x, self.nextPointUp.y, self.nextPointUp.floor)
        if self.nextPointDown is not None:
            val += "\nDown: {} {} {}".format(self.nextPointDown.x, self.nextPointDown.y, self.nextPointDown.floor)
        return val

    def setPointDown(self, nextNode):
        if not self.isPivot():
            self.pivot.setPointDown(nextNode)
        else:
            self.nextPointDown = nextNode

class StairPoint3D(ConnectionPoint3D):
    def __init__(self, x, y, z, isIndoor):
        super().__init__(x, y, z, isIndoor)

    def isStair(self):
        return True


class LiftPoint3D(ConnectionPoint3D):
    def __init__(self, x, y, z, isIndoor):
        super().__init__(x, y, z, isIndoor)

    def isLift(self):
        return True

class WideAreaPoint3D(Point3D):
    def __init__(self, x, y, z, isIndoor):
        super().__init__(x, y, z, isIndoor)

    def isWideArea(self):
        return True

class LectureRoomPoint3D(Point3D):
    def __init__(self, x, y, z, isIndoor):
        super().__init__(x, y, z, isIndoor)

    def isLectureRoom(self):
        return True

class ToiletPoint3D(Point3D):
    def __init__(self, x, y, z, isIndoor):
        super().__init__(x, y, z, isIndoor)

    def isToilet(self):
        return True

class HallwayPoint3D(Point3D):
    def __init__(self, x, y, z, isIndoor):
        super().__init__(x, y, z, isIndoor)

    def isHallway(self):
        return True