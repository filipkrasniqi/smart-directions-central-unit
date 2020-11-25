from map.elements.node import Node
import numpy as np

class Nodes:


    def __init__(self, nodes, adjacency_matrix):
        self.nodes, self.adjacency_matrix = nodes, adjacency_matrix

    def np_adj_matrix(self):
        np_adjacency = np.zeros(shape=(len(self.adjacency_matrix), len(self.adjacency_matrix)))
        for i, node in enumerate(self.adjacency_matrix.keys()):
            for adj in self.adjacency_matrix[node]:
                np_adjacency[i][adj] = 1
        return np_adjacency