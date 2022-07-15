import pytest
from flaky import flaky
import numpy as np

from dowhy.causal_refuter import CausalRefuter
from dowhy.causal_identifier import IdentifiedEstimand
from dowhy.causal_estimator import CausalEstimate


class MockRefuter(CausalRefuter):
	pass


def test_causal_refuter_placeholder_method():
	refuter = MockRefuter(None, IdentifiedEstimand(None, None, None), None)
	with pytest.raises(NotImplementedError):
		refuter.refute_estimate()


@flaky(max_runs=3)
def test_causal_refuter_bootstrap_test():
	estimator = CausalEstimate(0, None, None, None, None)
	refuter = MockRefuter(None, IdentifiedEstimand(None, None, None), None)
	simulations = np.random.normal(0, 1, 5000)
	pvalue = refuter.perform_bootstrap_test(estimator, simulations)
	assert pvalue > .95
