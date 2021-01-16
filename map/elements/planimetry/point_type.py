from enum import IntEnum


class PointType(IntEnum):
    INVALID = 0
    INDOOR = 1
    OUTDOOR = 2
    ANCHOR = 3
    EFFECTOR = 4
    POI = 5

    @staticmethod
    def isObject(pointType):
        return pointType >= 3

    @staticmethod
    def isValid(pointType):
        return pointType >= 1