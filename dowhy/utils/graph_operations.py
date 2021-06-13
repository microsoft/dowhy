import numpy as np
import graphviz
from queue import LifoQueue
from ordered_set import OrderedSet

def adjacency_matrix_to_graph(adjacency_matrix, labels=None):
    # Only consider edges have absolute edge weight > 0.01
    idx = np.abs(adjacency_matrix) > 0.01
    dirs = np.where(idx)
    d = graphviz.Digraph(engine='dot')
    names = labels if labels else [f'x{i}' for i in range(len(adjacency_matrix))]
    for name in names:
        d.node(name)
    for to, from_, coef in zip(dirs[0], dirs[1], adjacency_matrix[idx]):
        d.edge(names[from_], names[to], label=str(coef))
    return d

def str_to_dot(string):
    '''
    Converts input string from graphviz library to valid DOT graph format.
    '''
    graph = string.replace('\n', ';').replace('\t','')
    graph = graph[:9] + graph[10:-2] + graph[-1] # Removing unnecessary characters from string
    return graph

def find_ancestor(node_set, node_names, adjacency_matrix, node2idx, idx2node):
    '''
    Finds ancestors of a given set of nodes in a given graph.
    '''

    def find_ancestor_help(node_name, node_names, adjacency_matrix, node2idx, idx2node):
        ancestors = OrderedSet()
        nodes_to_visit = LifoQueue(maxsize = len(node_names))
        nodes_to_visit.put(node2idx[node_name])
        while not nodes_to_visit.empty():
            child = nodes_to_visit.get()
            ancestors.add(idx2node[child])
            for i in range(len(node_names)):
                if idx2node[i] not in ancestors and adjacency_matrix[i, child] == 1: # For edge a->b, a is along height and b is along width of adjacency matrix
                    nodes_to_visit.put(i)
        return ancestors

    ancestors = OrderedSet()
    for node_name in node_set:
        ancestors |= find_ancestor_help(node_name, node_names, adjacency_matrix, node2idx, idx2node)
    return ancestors

def induced_graph(node_set, adjacency_matrix, node2idx):
    node_idx_list = [node2idx[node] for node in node_set]
    node_idx_list.sort()
    adjacency_matrix_induced = adjacency_matrix.copy()
    adjacency_matrix_induced = adjacency_matrix_induced[node_idx_list]
    adjacency_matrix_induced = adjacency_matrix_induced[:, node_idx_list]
    return adjacency_matrix_induced        

def find_c_components(adjacency_matrix, node_set, idx2node):
    num_nodes = len(node_set)
    adj_matrix = adjacency_matrix.copy()
    adjacency_list = [[] for _ in range(num_nodes)]

    # Modify graph such that it only contains bidirected edges
    for h in range(0, num_nodes-1):
        for w in range(h+1, num_nodes):
            if adjacency_matrix[h, w]==1 and adjacency_matrix[w, h]==1:
                adjacency_list[h].append(w)
                adjacency_list[w].append(h)
            else:
                adj_matrix[h, w] = 0
                adj_matrix[w, h] = 0

    # Find c components by finding connected components on the undirected graph
    visited = [False for _ in range(num_nodes)]

    def dfs(node_idx, component):
        visited[node_idx] = True
        component.add(idx2node[node_idx])
        for neighbour in adjacency_list[node_idx]:
            if visited[neighbour] == False:
                dfs(neighbour, component)

    c_components = []
    for i in range(num_nodes):
        if visited[i] == False:
            component = OrderedSet()
            dfs(i, component)
            c_components.append(component)

    return c_components