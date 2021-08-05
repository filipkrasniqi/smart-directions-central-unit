from enum import IntEnum


class PointType(IntEnum):
    INVALID = 0
    INDOOR = 1
    OUTDOOR = 2
    ANCHOR = 3
    EFFECTOR = 4
    POI = 5
    STAIR = 6
    LIFT = 7
    STAIR_PIVOT = 8
    LIFT_PIVOT = 9

    @staticmethod
    def isObject(pointType):
        return pointType >= 3 and pointType < 6

    @staticmethod
    def isValid(pointType):
        return pointType >= 1

    @staticmethod
    def isConnection(pointType):
        return 6 <= pointType <= 7


class Direction(IntEnum):
    TOP = 0
    RIGHT = 1
    BOTTOM = 2
    LEFT = 3
    ALL = 4


class MessageDirection(IntEnum):
    FORWARD = 0
    RIGHT = 1
    BACK = 2
    LEFT = 3
    ARRIVED = 4
    START = 5
