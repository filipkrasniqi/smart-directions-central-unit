from map.elements.position import Position
import geopy.distance as distance

THRESHOLD_DISTANCE = 1  # meters s.t. I activate the effectors

class Effector(Position):
    def __init__(self, idx, latitude, longitude, name, mac):
        Position.__init__(self, latitude, longitude, name)
        self.idx = idx
        self.mac = mac.lower()

class Effectors:
    def __init__(self, effectors):
        self.effectors = effectors
        self.idx_current = 0

    def activate_effectors(self, current_position: Position):
        filtered_effectors = [effector for effector in self.effectors if distance.distance(current_position.getPosition(), effector.getPosition()).m < THRESHOLD_DISTANCE]
        return filtered_effectors

    def __next__(self):
        if self.idx_current < len(self.effectors):
            current_effector = self.effectors[self.idx_current]
            self.idx_current += 1
            return current_effector
        else:
            self.idx_current = 0
            raise StopIteration




