import networkx as nx
import pandas as pd

def create_graph_from_user() -> nx.DiGraph:
    """
    Creates a directed graph based on user input from the console.

    The user is prompted to enter edges one by one in the format 'node1 node2 time_lag',
    where 'node1' and 'node2' are the nodes connected by the edge, and 'time_lag' is a numerical
    value representing the weight of the edge. The user should enter 'done' to finish inputting edges.

    Returns:
    - nx.DiGraph: A directed graph created from the user's input.

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
            time_lag = float(time_lag)
        except ValueError:
            print("Invalid weight. Please enter a numerical value for the time_lag.")
            continue
        graph.add_edge(node1, node2, time_lag=time_lag)
    
    return graph

def create_graph_from_csv(file_path:str) -> nx.DiGraph:
    """
    Creates a directed graph from a CSV file.

    The CSV file should have at least three columns: 'node1', 'node2', and 'time_lag'.
    Each row represents an edge from 'node1' to 'node2' with a 'time_lag' attribute.

    Parameters:
    - file_path (str): The path to the CSV file.

    Returns:
    - nx.DiGraph: A directed graph created from the CSV file.

    Example CSV content:
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
        graph.add_edge(row['node1'], row['node2'], time_lag=row['time_lag'])
    
    return graph