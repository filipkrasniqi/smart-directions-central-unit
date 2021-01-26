import sys
import os.path
import networkx as nx

import numpy as np
import matplotlib.pyplot as plt

from map.elements.planimetry.building import Building
from map.elements.planimetry.point import Point3D
from map.elements.position import Position
from utils.parser import Parser

from rhino3dm import *

import bisect
import tkinter

if __name__ == "__main__":
    data_path = "/Users/filipkrasniqi/PycharmProjects/smartdirections/assets/"
    building = Parser(data_path).getInstance().read_buildings()[0]
    building.computeOfflineMap()

    # we are going to camera, starting from cucina. To activate: it should be corridoio
    destination = building.pois[0][2]
    start = [anchor for anchor in building.anchors[0] if anchor.name.lower() == 'cucina'][0]

    effectorFromCucina = building.toActivate(start, destination, 0)
    print("Going from {} to {}, first effector: {}".format(start, destination, effectorFromCucina))
    # from ingresso
    start = [anchor for anchor in building.anchors[0] if anchor.name.lower() == 'ingresso'][0]
    effectorFromIngresso = building.toActivate(start, destination, 0)
    print("Going from {} to {}, first effector: {}".format(start, destination, effectorFromIngresso))

    # from ospiti
    start = [anchor for anchor in building.anchors[0] if anchor.name.lower() == 'ospiti'][0]
    effectorFromOspiti = building.toActivate(start, destination, 0)
    print("Going from {} to {}, first effector: {}".format(start, destination, effectorFromOspiti))
