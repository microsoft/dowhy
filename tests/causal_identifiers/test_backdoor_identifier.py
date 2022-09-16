import pytest

from dowhy.causal_graph import CausalGraph
from dowhy.causal_identifier.identify_effect import CausalIdentifierEstimandType
from dowhy.causal_identifier import BackdoorIdentifier, BackdoorAdjustmentMethod

from .base import IdentificationTestGraphSolution, example_graph_solution


class TestBackdoorIdentification(object):
    def test_identify_backdoor_no_biased_sets(self, example_graph_solution: IdentificationTestGraphSolution):
        graph = example_graph_solution.graph
        biased_sets = example_graph_solution.biased_sets
        identifier = BackdoorIdentifier(
            estimand_type=CausalIdentifierEstimandType.NONPARAMETRIC_ATE,
            backdoor_adjustment=BackdoorAdjustmentMethod.BACKDOOR_EXHAUSTIVE,
        )

        backdoor_results = identifier.identify_backdoor(graph, "X", "Y", include_unobserved=False)
        backdoor_sets = [
            set(backdoor_result_dict["backdoor_set"])
            for backdoor_result_dict in backdoor_results
            if len(backdoor_result_dict["backdoor_set"]) > 0
        ]

        assert (len(backdoor_sets) == 0 and len(biased_sets) == 0) or all(  # No biased sets exist and that's expected.
            [set(biased_backdoor_set) not in backdoor_sets for biased_backdoor_set in biased_sets]
        )  # No sets that would induce biased results are present in the solution.

    def test_identify_backdoor_unobserved_not_in_backdoor_set(
        self, example_graph_solution: IdentificationTestGraphSolution
    ):
        graph = example_graph_solution.graph
        observed_variables = example_graph_solution.observed_variables
        identifier = BackdoorIdentifier(
            estimand_type=CausalIdentifierEstimandType.NONPARAMETRIC_ATE,
            backdoor_adjustment=BackdoorAdjustmentMethod.BACKDOOR_EXHAUSTIVE,
        )

        backdoor_results = identifier.identify_backdoor(graph, "X", "Y", include_unobserved=False)
        backdoor_sets = [
            set(backdoor_result_dict["backdoor_set"])
            for backdoor_result_dict in backdoor_results
            if len(backdoor_result_dict["backdoor_set"]) > 0
        ]

        assert all(
            [variable in observed_variables for backdoor_set in backdoor_sets for variable in backdoor_set]
        )  # All variables used in the backdoor sets must be observed.

    def test_identify_backdoor_minimal_adjustment(self, example_graph_solution: IdentificationTestGraphSolution):
        graph = example_graph_solution.graph
        expected_sets = example_graph_solution.minimal_adjustment_sets
        identifier = BackdoorIdentifier(
            estimand_type=CausalIdentifierEstimandType.NONPARAMETRIC_ATE,
            backdoor_adjustment=BackdoorAdjustmentMethod.BACKDOOR_MIN,
            proceed_when_unidentifiable=False,
        )

        backdoor_results = identifier.identify_backdoor(graph, "X", "Y", include_unobserved=False)
        backdoor_sets = [set(backdoor_result_dict["backdoor_set"]) for backdoor_result_dict in backdoor_results]

        assert (
            (len(backdoor_sets) == 0) and (len(expected_sets) == 0)
        ) or all(  # No adjustments exist and that's expected.
            [set(expected_set) in backdoor_sets for expected_set in expected_sets]
        )

    def test_identify_backdoor_maximal_adjustment(self, example_graph_solution: IdentificationTestGraphSolution):
        graph = example_graph_solution.graph
        expected_sets = example_graph_solution.maximal_adjustment_sets
        identifier = BackdoorIdentifier(
            estimand_type=CausalIdentifierEstimandType.NONPARAMETRIC_ATE,
            backdoor_adjustment=BackdoorAdjustmentMethod.BACKDOOR_MAX,
            proceed_when_unidentifiable=False,
        )

        backdoor_results = identifier.identify_backdoor(graph, "X", "Y", include_unobserved=False)

        backdoor_sets = [set(backdoor_result_dict["backdoor_set"]) for backdoor_result_dict in backdoor_results]
        print(backdoor_sets, expected_sets, example_graph_solution.graph_str)
        assert (
            (len(backdoor_sets) == 0) and (len(expected_sets) == 0)
        ) or all(  # No adjustments exist and that's expected.
            [set(expected_set) in backdoor_sets for expected_set in expected_sets]
        )

    def test_identify_backdoor_maximal_direct_effect(self, example_graph_solution: IdentificationTestGraphSolution):
        graph = example_graph_solution.graph
        expected_sets = example_graph_solution.direct_maximal_adjustment_sets
        identifier = BackdoorIdentifier(
            estimand_type=CausalIdentifierEstimandType.NONPARAMETRIC_CDE,
            backdoor_adjustment=BackdoorAdjustmentMethod.BACKDOOR_MAX,
            proceed_when_unidentifiable=False,
        )

        backdoor_results = identifier.identify_backdoor(graph, "X", "Y", direct_effect=True)

        backdoor_sets = [set(backdoor_result_dict["backdoor_set"]) for backdoor_result_dict in backdoor_results]
        print(backdoor_sets, expected_sets, example_graph_solution.graph_str)
        assert (
            (len(backdoor_sets) == 0) and (len(expected_sets) == 0)
        ) or all(  # No adjustments exist and that's expected.
            [set(expected_set) in backdoor_sets for expected_set in expected_sets]
        )
