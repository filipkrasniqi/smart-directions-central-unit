from map.elements.planimetry.point_type import PointType
from map.elements.position import Position


class PoI(Position):
    def __init__(self, idx, latitude, longitude, name):
        Position.__init__(self, latitude, longitude, name)
        self.idx = idx

    def getColor(self):
        return [0, 0, 255]

    def getSelectedColor(self):
        return [0, 128, 255]

    def getObjectType(self):
        return PointType.POI

    def getId(self):
        return "POI_{}".format(self.idx)

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