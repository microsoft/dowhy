import networkx as nx
import numpy as np
import pandas as pd

import networkx as nx

def unroll_graph(graph: nx.DiGraph) -> nx.DiGraph:
    """
    Unrolls a graph by creating a new node for every time lag to the original node and adding those edges to a new graph.

    :param graph: The directed graph object.
    :type graph: networkx.DiGraph
    :return: An unrolled graph.
    :rtype: networkx.DiGraph
    """
    unrolled_graph = nx.DiGraph()
    node_mapping = {}  # Maps original node names to their unrolled counterparts
    
    for node in graph.nodes:
        node_mapping[node] = set()  # Use a set to avoid duplicate entries

    for node in graph.nodes:
        for parent in graph.predecessors(node):
            edge_data = graph.get_edge_data(parent, node)
            if "time_lag" in edge_data:
                time_lags = edge_data["time_lag"]
                if not isinstance(time_lags, tuple):
                    time_lags = (time_lags,)

                # Create a new node for the current child node if its mapping set is empty
                if not node_mapping[node]:
                    new_node_name = f"{node}_0"
                    node_mapping[node].add(new_node_name)
                    unrolled_graph.add_node(new_node_name)
                else:
                    # Use the existing child node for edge creation
                    new_node_name = f"{node}_0"  # This will represent the current node's base name

                # Add edges from parent to all existing time-lagged children
                for lag in time_lags:
                    parent_unrolled_name = f"{parent}_{-lag}"
                    if parent_unrolled_name not in node_mapping[parent]:
                        node_mapping[parent].add(parent_unrolled_name)
                        unrolled_graph.add_node(parent_unrolled_name)

                    # Add edge from the parent to the current child node
                    unrolled_graph.add_edge(parent_unrolled_name, new_node_name)

                # Add edges from parent to all existing time-lagged children of this node
                for existing_child in node_mapping[node]:
                    unrolled_graph.add_edge(parent_unrolled_name, existing_child)

    return unrolled_graph

def create_graph_from_user() -> nx.DiGraph:
    """
    Creates a directed graph based on user input from the console.

    The time_lag parameter of the networkx graph represents the maximal causal lag of an edge between any 2 nodes in the graph.

    The user is prompted to enter edges one by one in the format 'node1 node2 time_lag',
    where 'node1' and 'node2' are the nodes connected by the edge, and 'time_lag' is a numerical
    value representing the weight of the edge. The user should enter 'done' to finish inputting edges.

    :return: A directed graph created from the user's input.
    :rtype: nx.DiGraph

    Example user input:
        Enter an edge: A B 4
        Enter an edge: B C 2
        Enter an edge: done
    """
    # Initialize an empty directed graph
    graph = nx.DiGraph()

    # Instructions for the user
    print("Enter the graph as a list of edges with time lags. Enter 'done' when you are finished.")
    print("Each edge should be entered in the format 'node1 node2 time_lag'. For example: 'A B 4'")

    # Loop to receive user input
    while True:
        edge = input("Enter an edge: ")
        if edge.lower() == "done":
            break
        edge = edge.split()
        if len(edge) != 3:
            print("Invalid edge. Please enter an edge in the format 'node1 node2 time_lag'.")
            continue
        node1, node2, time_lag = edge
        try:
            time_lag = int(time_lag)
        except ValueError:
            print("Invalid weight. Please enter a numerical value for the time_lag.")
            continue
        graph.add_edge(node1, node2, time_lag=time_lag)

    return graph


def create_graph_from_csv(file_path: str) -> nx.DiGraph:
    """
    Creates a directed graph from a CSV file.

    The time_lag parameter of the networkx graph represents the maximal causal lag of an edge between any 2 nodes in the graph.

    The CSV file should have at least three columns: 'node1', 'node2', and 'time_lag'.
    Each row represents an edge from 'node1' to 'node2' with a 'time_lag' attribute.

    :param file_path: The path to the CSV file.
    :type file_path: str
    :return: A directed graph created from the CSV file.
    :rtype: nx.DiGraph

    Example:
        Example CSV content:

        .. code-block:: csv

            node1,node2,time_lag
            A,B,5
            B,C,2
            A,C,7
    """
    # Read the CSV file into a DataFrame
    df = pd.read_csv(file_path)

    # Initialize an empty directed graph
    graph = nx.DiGraph()

    # Add edges with time lag to the graph
    for index, row in df.iterrows():
        # Add validation for the time lag column to be a number
        try:
            time_lag = int(row["time_lag"])
        except ValueError:
            print(
                "Invalid weight. Please enter a numerical value for the time_lag for the edge between {} and {}.".format(
                    row["node1"], row["node2"]
                )
            )
            return None

        # Check if the edge already exists
        if graph.has_edge(row["node1"], row["node2"]):
            # If the edge exists, append the time_lag to the existing tuple
            current_time_lag = graph[row["node1"]][row["node2"]]["time_lag"]
            if isinstance(current_time_lag, tuple):
                graph[row["node1"]][row["node2"]]["time_lag"] = current_time_lag + (time_lag,)
            else:
                graph[row["node1"]][row["node2"]]["time_lag"] = (current_time_lag, time_lag)
        else:
            # If the edge does not exist, create a new edge with a tuple containing the time_lag
            graph.add_edge(row["node1"], row["node2"], time_lag=(time_lag,))

    return graph


def create_graph_from_dot_format(file_path: str) -> nx.DiGraph:
    """
    Creates a directed graph from a DOT file and ensures it is a DiGraph.

    The time_lag parameter of the networkx graph represents the maximal causal lag of an edge between any 2 nodes in the graph.

    The DOT file should contain a graph in DOT format.

    :param file_path: The path to the DOT file.
    :type file_path: str
    :return: A directed graph (DiGraph) created from the DOT file.
    :rtype: nx.DiGraph
    """
    # Read the DOT file into a MultiDiGraph
    multi_graph = nx.drawing.nx_agraph.read_dot(file_path)

    # Initialize a new DiGraph
    graph = nx.DiGraph()

    # Iterate over edges of the MultiDiGraph
    for u, v, data in multi_graph.edges(data=True):
        if "label" in data:
            try:
                time_lag = int(data["label"])

                # Handle multiple edges between the same nodes
                if graph.has_edge(u, v):
                    existing_data = graph.get_edge_data(u, v)
                    if "time_lag" in existing_data:
                        # Use maximum time_lag if multiple edges exist
                        existing_data["time_lag"] = max(existing_data["time_lag"], time_lag)
                    else:
                        existing_data["time_lag"] = time_lag
                else:
                    graph.add_edge(u, v, time_lag=time_lag)

            except ValueError:
                print(f"Invalid weight for the edge between {u} and {v}.")
                return None

    return graph


def create_graph_from_networkx_array(array: np.ndarray, var_names: list) -> nx.DiGraph:
    """
    Create a NetworkX directed graph from a numpy array with time lag information.

    The time_lag parameter of the networkx graph represents the maximal causal lag of an edge between any 2 nodes in the graph.

    The resulting graph will be a directed graph with edge attributes indicating
    the type of link based on the array values.

    :param array: A numpy array of shape (n, n, tau) representing the causal links.
    :type array: np.ndarray
    :param var_names: A list of variable names.
    :type var_names: list
    :return: A directed graph with edge attributes based on the array values.
    :rtype: nx.DiGraph
    """
    n = array.shape[0]  # Number of variables
    tau = array.shape[2]  # Number of time lags

    # Initialize a directed graph
    graph = nx.DiGraph()

    # Add nodes with names
    graph.add_nodes_from(var_names)

    # Iterate over all pairs of nodes
    for i in range(n):
        for j in range(n):
            if i == j:
                continue  # Skip self-loops

            # Check for contemporaneous links (tau = 0)
            if array[i, j, 0] == "-->":
                graph.add_edge(var_names[i], var_names[j], type="contemporaneous", direction="forward")
            elif array[i, j, 0] == "<--":
                graph.add_edge(var_names[j], var_names[i], type="contemporaneous", direction="backward")
            elif array[i, j, 0] == "o-o":
                # raise error
                graph.add_edge(var_names[i], var_names[j], type="adjacency", style="circle")
                graph.add_edge(var_names[j], var_names[i], type="adjacency", style="circle")
            elif array[i, j, 0] == "x-x":
                # raise dag error / not supported / conflicting
                graph.add_edge(var_names[i], var_names[j], type="conflicting", style="cross")
                graph.add_edge(var_names[j], var_names[i], type="conflicting", style="cross")

            # Check for lagged links (tau > 0)
            for t in range(1, tau):
                if array[i, j, t] == "-->":
                    graph.add_edge(var_names[i], var_names[j], time_lag=t)
                elif array[j, i, t] == "-->":
                    graph.add_edge(var_names[j], var_names[i], time_lag=t)

    return graph
