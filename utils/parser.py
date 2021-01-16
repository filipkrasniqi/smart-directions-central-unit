from map.elements.effector import Effectors, Effector
from map.elements.node import Node
from map.elements.nodes import Nodes
import re
import pickle

from map.elements.planimetry.point import Point3D

patt = re.compile("[^\t]+")

class Parser:
    class __Parser:
        def __init__(self, data_dir):
            self.data_dir = data_dir

        '''
        Read so far updated buildings
        '''
        def read_buildings(self):
            try:
                with open("{}buildings.pkl".format(self.data_dir), 'rb') as file:
                        buildings = pickle.load(file)
            except:
                buildings = []
            return buildings

        '''
        Update buildings list
        '''
        def write_buildings(self, buildings):
            with open("{}buildings.pkl".format(self.data_dir), 'wb') as file:
                pickle.dump(buildings, file)

        # TODO I should also validate the file
        '''
        Loads the 3D points associated to a building with discrimination of indoor and outdoor
        '''
        def read_points_from_txt(self, file_path = None, f = None):
            assert file_path is not None or f is not None, "No file"
            if f is None:
                # file_path = "{}{}".format(file_path, "map-v1/points.txt")
                f = open(file_path, 'r')
            lines = f.readlines()
            points_x, points_y, points_z, points_isIndoor, unique_z = [], [], [], [], []
            # parse the file to have list of x, y, z vals
            for line in lines:
                vals = line.split(",")
                x, y, z, r, g, b = float(vals[0]), float(vals[1]), float(vals[2]), int(vals[3]), int(vals[4]), int(
                    vals[5])
                points_x.append(x)
                points_y.append(y)
                points_z.append(z)
                # currently we have colors to understand whether space is indoor or outdoor; r is 255 for indoor
                points_isIndoor.append(r == 255)
            points: list[Point3D] = [Point3D(x, y, z, isIndoor) for x, y, z, isIndoor in
                                     zip(points_x, points_y, points_z, points_isIndoor)]
            return points

        def parse_node(self, idx, node):
            # splits = node.split(r'\t+')
            splits = list(filter(lambda x : x != "", node.replace("\n", "").split(" ")))
            assert len(splits) == 4, "Wrong init of node"
            return Node(idx, float(splits[0]), float(splits[1]), splits[2], splits[3])

        def parse_effector(self, idx, effector):
            splits = list(filter(lambda x : x != "", effector.replace("\n", "").split(" ")))
            assert len(splits) == 4, "Wrong init of effector"
            return Effector(idx, float(splits[0]), float(splits[1]), splits[2], splits[3])

        def read_nodes(self):
            nodes = []
            with open(self.data_dir+"nodes.txt", "r") as nodes_data:
                for i, data in enumerate(nodes_data):
                    if i > 0:
                        nodes.append(self.parse_node(i, data))
                    else:
                        num_nodes = int(data.replace("\n", ""))
            adjacency = {}
            with open(self.data_dir+"adjacency.txt", "r") as adjacency_matrix:
                # saving adjacency as dictionary
                for i, adjacency_row in enumerate(adjacency_matrix):
                    adjacency[i] = []
                    for j, val in enumerate(adjacency_row.split(r'\t+')):
                        if val == "1":
                            adjacency[i].append(j)
            return Nodes(nodes, adjacency)

        def read_effectors(self):
            effectors = []
            with open(self.data_dir + "effectors.txt", "r") as effectors_data:
                for i, data in enumerate(effectors_data):
                    if i > 0:
                        effectors.append(self.parse_effector(i, data))
                    else:
                        num_effectors = int(data.replace("\n", ""))
            return Effectors(effectors)

    __instance = None

    def __init__(self, data_dir):
        if not Parser.__instance:
            Parser.__instance = Parser.__Parser(data_dir)
        else:
            Parser.__instance.data_dir = data_dir

    def __getattr__(self, name):
        return getattr(self.__instance, name)

    def getInstance(self):
        return Parser.__instance