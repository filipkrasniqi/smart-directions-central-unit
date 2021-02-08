from map.elements.node import Node
import numpy as np

class Nodes:


    def __init__(self, nodes = [], adjacency_matrix = None):
        self.nodes, self.adjacency_matrix, self.idx_current = nodes, adjacency_matrix, 0

    def np_adj_matrix(self):
        np_adjacency = np.zeros(shape=(len(self.adjacency_matrix), len(self.adjacency_matrix)))
        for i, node in enumerate(self.adjacency_matrix.keys()):
            for adj in self.adjacency_matrix[node]:
                np_adjacency[i][adj] = 1
        return np_adjacency

    def __next__(self):
        if self.idx_current < len(self.nodes):
            current_effector = self.nodes[self.idx_current]
            self.idx_current += 1
            return current_effector
        else:
            self.idx_current = 0
            raise StopIteration

    def remove(self, node):
        self.nodes.remove(node)

    def add(self, node: Node):
        self.nodes.append(node)

    def __len__(self):
        return len(self.nodes)

    def __getitem__(self, i):
        return self.nodes[i]