class Point3D:
    def __init__(self, x, y, z, isIndoor):
        self.x, self.y, self.z, self.isIndoor = x, y, z, isIndoor
        self.floor = -1