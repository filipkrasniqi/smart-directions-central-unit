from localization.WifiLocalizer import WifiLocalizer
from map.elements.node import Node
from map.elements.planimetry.building import Building


class SmartDirectionWrapperInstance:
    def __init__(self, id, name):
        self.id, self.name = id, name

    def getWrapper(self):
        return SmartDirectionWrapperInstance(self.id, self.name)

    '''
    Two SD instances are equal if they both are instance of SmartDirectionWrapperInstance class and the ID is the same
    '''
    def __eq__(self, other):
        return isinstance(other, SmartDirectionWrapperInstance) and other.id == self.id

class SmartDirectionInstance(SmartDirectionWrapperInstance):
    def __init__(self, id, buildings = [], name="Nuova istanza Smart Direction"):
        SmartDirectionWrapperInstance.__init__(self, id, name)
        self.buildings = buildings
        self.wf_localizer = None

    def get_building_from_id(self, id_building):
        return [b for b in self.buildings if b.id == id_building][0]

    def get_position_from_grid(self, id_building, position_in_grid, floor):
        building: Building = self.get_building_from_id(id_building)
        return building.get_position_from_grid_number(position_in_grid, floor)

    def add_node(self, id_building, mac, wifi):
        b = [b for b in self.buildings if b.id == id_building][0]
        wf_localizer = WifiLocalizer(self)
        id_building = wf_localizer.infer_building(wifi, [], False)
        floor = wf_localizer.infer_floor(wifi, [], id_building, False)
        position_in_grid = wf_localizer.infer_position(wifi, [], id_building, False)
        position = self.get_position_from_grid(id_building, position_in_grid, floor)
        try:
            n = [n for n in b.nodes if n.mac == mac][0]
        except:
            idx = len(b.nodes)
            n = Node(idx, position.x, position.y, position.z, "Ancora {}".format(idx), mac)
            b.addAnchor(position.z, n)
        return n

    def initRouting(self):
        # TODO faccio routing di tutti i building. Poi dovrò aggiungere la navigazione extra
        for b in self.buildings:
            b.initRouting()

    def rawAnchors(self):
        anchors = []
        for b in self.buildings:
            anchors += b.rawAnchors()
        return anchors

    def rawEffectors(self):
        effectors = []
        for b in self.buildings:
            effectors += b.rawEffectors()
        return effectors