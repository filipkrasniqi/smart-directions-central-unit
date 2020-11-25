import sys
import os.path
import networkx as nx

import numpy as np
import matplotlib.pyplot as plt

from utils.parser import Parser

if __name__ == "__main__":
    # checks for input vals
    force_import = len(sys.argv) <= 0 or sys.argv[0] == "f"
    data_path = "../assets/"
    # create it
    parser = Parser(data_path).getInstance()
    nodes = parser.read_nodes()
    # build graph of nodes
    G = nx.Graph(nodes.np_adj_matrix())
    plt.plot()
    nx.draw(G, with_labels=True, font_weight='bold')
    plt.show()
    # compute routing
    print(nx.shortest_path(G, source=0, target=1))
    # effectors
    effectors = parser.read_effectors()
    filtered_effectors_1 = effectors.activate_effectors(nodes.nodes[0])
    filtered_effectors_2 = effectors.activate_effectors(nodes.nodes[1])
    filtered_effectors_3 = effectors.activate_effectors(nodes.nodes[2])

    # TODO impostare ora i nodi e vedere se si attivano correttamente