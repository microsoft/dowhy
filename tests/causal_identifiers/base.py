import pytest
from dowhy.causal_graph import CausalGraph

from .example_graphs import TEST_GRAPH_SOLUTIONS


class IdentificationTestGraphSolution(object):

    def __init__(self, graph_str, observed_variables, biased_sets, expected_sets):
        self.graph = CausalGraph("X", "Y", graph_str, observed_node_names=observed_variables)
        self.observed_variables = observed_variables
        self.biased_sets = biased_sets
        self.expected_sets = expected_sets


@pytest.fixture(params=TEST_GRAPH_SOLUTIONS.keys())
def example_graph_solution(request):
    return IdentificationTestGraphSolution(**TEST_GRAPH_SOLUTIONS[request.param])
