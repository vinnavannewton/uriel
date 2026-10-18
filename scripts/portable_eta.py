"""Portable scalar regression-tree inference, verified against native XGBoost."""
import math
import numpy as np

class PortableRegressor:
    def __init__(self, data):
        self.base = float(data['base_score'])
        self.trees = []
        for root in data['trees']:
            nodes = {}
            def walk(node):
                if 'leaf' in node:
                    nodes[node['nodeid']] = (float(node['leaf']),)
                else:
                    nodes[node['nodeid']] = (int(node['split'][1:]), float(node['split_condition']),
                        node['yes'], node['no'], node['missing'])
                    for child in node['children']:walk(child)
            walk(root)
            self.trees.append(nodes)

    def predict(self, matrix):
        # XGBoost evaluates both features and threshold comparisons as float32.
        matrix = np.asarray(matrix, dtype=np.float32)
        output = []
        for row in matrix:
            value = np.float32(self.base)
            for nodes in self.trees:
                node = nodes[0]
                while len(node) != 1:
                    feature, threshold, yes, no, missing = node
                    x = row[feature]
                    node = nodes[missing if math.isnan(x) else yes if x < np.float32(threshold) else no]
                value = np.float32(value + np.float32(node[0]))
            output.append(float(value))
        return np.asarray(output)
