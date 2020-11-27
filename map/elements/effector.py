from map.elements.node import Node
from map.elements.position import Position
import numpy as np
import geopy
import geopy.distance as distance

THRESHOLD_DISTANCE = 2  # meters s.t. I activate the effectors

class Effector(Position):
    def __init__(self, idx, latitude, longitude, name, mac):
        Position.__init__(self, latitude, longitude, name)
        self.idx = idx
        self.mac = mac.lower()

class Effectors:
    def __init__(self, effectors):
        self.effectors = effectors

    def activate_effectors(self, current_position: Position):
        filtered_effectors = [effector for effector in self.effectors if distance.distance(current_position.getPosition(), effector.getPosition()).m < THRESHOLD_DISTANCE]
        # TODO communicate with them
        return filtered_effectors


