import sys
import os.path
import networkx as nx

import numpy as np
import matplotlib.pyplot as plt

from map.elements.planimetry.building import Building
from map.elements.planimetry.point import Point3D
from utils.parser import Parser

from rhino3dm import *

import bisect
import tkinter

if __name__ == "__main__":
    # checks for input vals
    force_import = len(sys.argv) <= 0 or sys.argv[0] == "f"
    data_path = "../assets/"
    '''
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
    '''

    f = open("{}{}".format(data_path, "map-v1/points.txt"), 'r')
    lines = f.readlines()
    points_x, points_y, points_z, points_isIndoor, unique_z = [], [], [], [], []
    for line in lines:
        vals = line.split(",")
        x, y, z, r, g, b = float(vals[0]), float(vals[1]), float(vals[2]), int(vals[3]), int(vals[4]), int(vals[5])
        points_x.append(x)
        points_y.append(y)
        points_z.append(z)
        if z not in unique_z:
            bisect.insort(unique_z, z)
        points_isIndoor.append(r == 255)
    points: list[Point3D] = [Point3D(x, y, z, isIndoor) for x, y, z, isIndoor in zip(points_x, points_y, points_z, points_isIndoor)]
    building = Building(0, 0, 0, points, "Edificio 11")
