from localization.WifiLocalizer import WifiLocalizer
from map.elements.effector import Effector
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

    def add_node(self, mac, wifi):
        wf_localizer = WifiLocalizer(self)
        id_building = wf_localizer.infer_building(wifi, [], False)
        b = [b for b in self.buildings if b.id == id_building][0]
        floor = wf_localizer.infer_floor(wifi, [], id_building, False)
        position_in_grid = wf_localizer.infer_position(wifi, [], id_building, False)
        position = self.get_position_from_grid(id_building, position_in_grid, floor)
        anchors = b.get_anchors(floor)
        try:
            n = [n for n in anchors if n.mac == mac][0]
        except:
            idx = b.get_new_anchor_id()
            n = Node(idx, position.x, position.y, position.z, "Ancora {}".format(idx), mac)
            b.addAnchor(position.z, n)

            from utils.parser import Parser
            parser = Parser().getInstance()
            parser.write_sd_buildings(self)
        return {'id_node': n.idx, 'id_building': b.id}

    def add_effector(self, mac, wifi):
        wf_localizer = WifiLocalizer(self)
        id_building = wf_localizer.infer_building(wifi, [], False)
        b = [b for b in self.buildings if b.id == id_building][0]
        floor = wf_localizer.infer_floor(wifi, [], id_building, False)
        position_in_grid = wf_localizer.infer_position(wifi, [], id_building, False)
        position = self.get_position_from_grid(id_building, position_in_grid, floor)
        effectors = b.get_effectors(floor)
        try:
            effector = [n for n in effectors if n.mac == mac][0]
        except:
            idx = b.get_new_anchor_id()
            effector = Effector(idx, position.x, position.y, position.z, "Effettore {}".format(idx), mac)
            b.addEffector(position.z, effector)

            from utils.parser import Parser
            parser = Parser().getInstance()
            parser.write_sd_buildings(self)
        return {'id_node': effector.idx, 'id_building': b.id}

    def initRouting(self):
        # TODO aggiungere navigazione extra building
        for b in self.buildings:
            b.initRouting()

    def raw_anchors(self):
        anchors = []
        for b in self.buildings:
            anchors += b.raw_anchors()
        return anchors

    def raw_effectors(self):
        effectors = []
        for b in self.buildings:
            effectors += b.raw_effectors()
        return effectors

    def raw_pois(self):
        pois = []
        for b in self.buildings:
            pois += b.raw_pois()
        return pois

    def clean_anchors(self):
        for b in self.buildings:
            b.clean_anchors()