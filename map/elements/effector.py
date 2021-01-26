from map.elements.planimetry.point_type import PointType
from map.elements.position import Position
import geopy.distance as distance

THRESHOLD_DISTANCE = 1  # meters s.t. I activate the effectors

class Effector(Position):
    def __init__(self, idx, x, y, z, name, mac):
        Position.__init__(self, x, y, z, name)
        self.idx = idx
        self.mac = mac.lower()

    def getColor(self):
        return [255, 0, 0]

    def getSelectedColor(self):
        return [255, 192, 0]

    def getObjectType(self):
        return PointType.EFFECTOR

    def getId(self):
        return "EFFECTOR_{}".format(self.idx)

    def __str__(self):
        position_str = Position.__str__(self)
        return "{}\n{}".format(position_str, self.mac)

class Effectors:
    def __init__(self, effectors = []):
        self.effectors = effectors
        self.idx_current = 0

    def activate_effectors(self, current_position: Position):
        filtered_effectors = [effector for effector in self.effectors if distance.distance(current_position.getPosition(), effector.getPosition()).m < THRESHOLD_DISTANCE]
        return filtered_effectors

    def add(self, effector):
        self.effectors.append(effector)

    def __next__(self):
        if self.idx_current < len(self.effectors):
            current_effector = self.effectors[self.idx_current]
            self.idx_current += 1
            return current_effector
        else:
            self.idx_current = 0
            raise StopIteration

    def __len__(self):
        return len(self.effectors)

    def __getitem__(self, i):
        return self.effectors[i]
