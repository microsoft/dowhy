import statsmodels.api as sm
from pytest import mark

import dowhy.datasets
from dowhy.causal_estimators.generalized_linear_model_estimator import GeneralizedLinearModelEstimator

from .base import SimpleEstimator, TestGraphObject, example_graph


@mark.usefixtures("fixed_seed")
class TestGeneralizedLinearModelEstimator(object):
    @mark.parametrize(
        [
            "error_tolerance",
            "Estimator",
            "num_common_causes",
            "num_instruments",
            "num_effect_modifiers",
            "num_treatments",
            "treatment_is_binary",
            "outcome_is_binary",
            "identifier_method",
        ],
        [
            (
                0.1,
                GeneralizedLinearModelEstimator,
                [
                    0,
                ],
                [
                    0,
                ],
                [
                    0,
                ],
                [
                    1,
                ],
                [
                    False,
                ],
                [
                    True,
                ],
                "backdoor",
            ),
            (
                0.1,
                GeneralizedLinearModelEstimator,
                [
                    0,
                ],
                [
                    0,
                ],
                [
                    0,
                ],
                [
                    1,
                ],
                [
                    False,
                ],
                [
                    True,
                ],
                "general_adjustment",
            ),
        ],
    )
    def test_average_treatment_effect(
        self,
        error_tolerance,
        Estimator,
        num_common_causes,
        num_instruments,
        num_effect_modifiers,
        num_treatments,
        treatment_is_binary,
        outcome_is_binary,
        identifier_method,
    ):
        estimator_tester = SimpleEstimator(error_tolerance, Estimator, identifier_method)
        estimator_tester.average_treatment_effect_testsuite(
            num_common_causes=num_common_causes,
            num_instruments=num_instruments,
            num_effect_modifiers=num_effect_modifiers,
            num_treatments=num_treatments,
            treatment_is_binary=treatment_is_binary,
            outcome_is_binary=outcome_is_binary,
            confidence_intervals=[
                True,
            ],
            test_significance=[
                True,
            ],
            method_params={
                "num_simulations": 10,
                "num_null_simulations": 10,
                "glm_family": sm.families.Binomial(),
                "predict_score": True,
            },
        )

    def test_general_adjustment_estimation_on_example_graphs(self, example_graph: TestGraphObject):
        data = dowhy.datasets.linear_dataset_from_graph(
            example_graph.graph,
            example_graph.action_nodes,
            example_graph.outcome_node,
            treatments_are_binary=True,
            outcome_is_binary=True,
            num_samples=50000,
        )
        data["df"] = data["df"][example_graph.observed_nodes]
        estimator_tester = SimpleEstimator(0.1, GeneralizedLinearModelEstimator, identifier_method="general_adjustment")
        estimator_tester.custom_data_average_treatment_effect_test(
            data,
            method_params={
                "num_simulations": 10,
                "num_null_simulations": 10,
                "glm_family": sm.families.Binomial(),
                "predict_score": True,
            },
        )
