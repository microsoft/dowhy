import copy

import pytest

from dowhy.causal_graph import CausalGraph
from dowhy.causal_identifier.causal_identifier import CausalIdentifierEstimandType
from dowhy.causal_identifier import BackdoorIdentifier, BackdoorAdjustmentMethod
from tests.causal_identifiers.example_graphs_efficient import TEST_EFFICIENT_BD_SOLUTIONS


def test_identify_efficient_backdoor_algorithms():
    for example in TEST_EFFICIENT_BD_SOLUTIONS.values():
        G = CausalGraph(
            graph=example["graph_str"],
            treatment_name="X",
            outcome_name="Y",
            observed_node_names=example["observed_node_names"],
        )
        for method_name in BackdoorIdentifier.EFFICIENT_METHODS:
            ident_eff = BackdoorIdentifier(
                estimand_type=CausalIdentifierEstimandType.NONPARAMETRIC_ATE,
                backdoor_adjustment=method_name,
                costs=example["costs"],
            )
            method_name_results = method_name.value.replace("-", "_")
            if example[method_name_results] is None:
                with pytest.raises(ValueError):
                    ident_eff.identify_effect(
                        G,
                        G.treatment_name,
                        G.outcome_name,
                        conditional_node_names=example["conditional_node_names"],
                    )
            else:
                results_eff = ident_eff.identify_effect(
                    G,
                    G.treatment_name,
                    G.outcome_name,
                    conditional_node_names=example["conditional_node_names"],
                )
                assert set(results_eff.get_backdoor_variables()) == example[method_name_results]


def test_fail_negative_costs_efficient_backdoor_algorithms():
    example = TEST_EFFICIENT_BD_SOLUTIONS["sr22_fig2_example_graph"]
    G = CausalGraph(
        graph=example["graph_str"],
        treatment_name="X",
        outcome_name="Y",
        observed_node_names=example["observed_node_names"],
    )
    mod_costs = copy.deepcopy(example["costs"])
    mod_costs[0][1]["cost"] = 0
    ident_eff = BackdoorIdentifier(
        estimand_type=CausalIdentifierEstimandType.NONPARAMETRIC_ATE,
        backdoor_adjustment=BackdoorAdjustmentMethod.BACKDOOR_MINCOST_EFFICIENT,
        costs=mod_costs,
    )

    with pytest.raises(Exception):
        ident_eff.identify_effect(
            G,
            G.treatment_name,
            G.outcome_name,
            conditional_node_names=example["conditional_node_names"],
        )


def test_fail_unobserved_cond_vars_efficient_backdoor_algorithms():
    example = TEST_EFFICIENT_BD_SOLUTIONS["sr22_fig2_example_graph"]
    G = CausalGraph(
        graph=example["graph_str"],
        treatment_name="X",
        outcome_name="Y",
        observed_node_names=example["observed_node_names"],
    )
    ident_eff = BackdoorIdentifier(
        estimand_type=CausalIdentifierEstimandType.NONPARAMETRIC_ATE,
        backdoor_adjustment=BackdoorAdjustmentMethod.BACKDOOR_MINCOST_EFFICIENT,
        costs=example["costs"],
    )
    mod_cond_names = copy.deepcopy(example["conditional_node_names"])
    mod_cond_names.append("U")
    with pytest.raises(Exception):
        ident_eff.identify_effect(
            G,
            G.treatment_name,
            G.outcome_name,
            conditional_node_names=mod_cond_names,
        )


def test_fail_multivar_treat_efficient_backdoor_algorithms():
    example = TEST_EFFICIENT_BD_SOLUTIONS["sr22_fig2_example_graph"]
    G = CausalGraph(
        graph=example["graph_str"],
        treatment_name=["X", "K"],
        outcome_name="Y",
        observed_node_names=example["observed_node_names"],
    )
    ident_eff = BackdoorIdentifier(
        estimand_type=CausalIdentifierEstimandType.NONPARAMETRIC_ATE,
        backdoor_adjustment=BackdoorAdjustmentMethod.BACKDOOR_MINCOST_EFFICIENT,
        costs=example["costs"],
    )
    with pytest.raises(Exception):
        ident_eff.identify_effect(
            G,
            G.treatment_name,
            G.outcome_name,
            conditional_node_names=example["conditional_node_names"],
        )


def test_fail_multivar_outcome_efficient_backdoor_algorithms():
    example = TEST_EFFICIENT_BD_SOLUTIONS["sr22_fig2_example_graph"]
    G = CausalGraph(
        graph=example["graph_str"],
        treatment_name="X",
        outcome_name=["Y", "R"],
        observed_node_names=example["observed_node_names"],
    )
    ident_eff = BackdoorIdentifier(
        estimand_type=CausalIdentifierEstimandType.NONPARAMETRIC_ATE,
        backdoor_adjustment=BackdoorAdjustmentMethod.BACKDOOR_MINCOST_EFFICIENT,
        costs=example["costs"],
    )
    with pytest.raises(Exception):
        ident_eff.identify_effect(
            G,
            G.treatment_name,
            G.outcome_name,
            conditional_node_names=example["conditional_node_names"],
        )
