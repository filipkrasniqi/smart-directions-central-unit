from map.elements.effector import Effectors, Effector
from map.elements.node import Node
from map.elements.nodes import Nodes
import re

patt = re.compile("[^\t]+")

class Parser:
    class __Parser:
        def __init__(self, data_dir):
            self.data_dir = data_dir

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