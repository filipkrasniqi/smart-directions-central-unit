from map.elements.planimetry.point_type import PointType
from map.elements.position import Position


class Node(Position):
    def __init__(self, idx, x, y, z, name, mac):
        Position.__init__(self, x, y, z, name)
        self.idx = idx
        self.mac = mac.lower()

    def getColor(self):
        return [0, 255, 0]

    def getSelectedColor(self):
        return [128, 255, 0]

    def getObjectType(self):
        return PointType.ANCHOR

    def getId(self):
        return "ANCHOR_{}".format(self.idx)

    def isAnchor(self):
        return True

    def __str__(self):
        position_str = Position.__str__(self)
        return "{}\n{}\n{}".format(position_str, self.mac, self.idx)
