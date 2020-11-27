from map.elements.position import Position


class Node(Position):
    def __init__(self, idx, latitude, longitude, name, mac):
        Position.__init__(self, latitude, longitude, name)
        self.idx = idx
        self.mac = mac.lower()
