from dowhy.causal_refuter import CausalRefuter, CausalRefutation
from dowhy.causal_estimator import CausalEstimator
import numpy as np
import logging

class DataSubsetRefuter(CausalRefuter):
    """Refute an estimate by rerunning it on a random subset of the original data.

    Supports additional parameters that can be specified in the refute_estimate() method.

    - 'subset_fraction': float, 0.8 by default
    Fraction of the data to be used for re-estimation.
    - 'num_simulations': int, CausalRefuter.DEFAULT_NUM_SIMULATIONS by default
    The number of simulations to be run
    - random_state': int, RandomState, None by default
    The seed value to be added if we wish to repeat the same random behavior. If we with to repeat the
    same behavior we push the same seed in the psuedo-random generator
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._subset_fraction = kwargs.pop("subset_fraction", 0.8)
        self._num_simulations = kwargs.pop("num_simulations", CausalRefuter.DEFAULT_NUM_SIMULATIONS )
        self._random_state = kwargs.pop("random_state",None)

        if 'logging_level' in kwargs:
            logging.basicConfig(level=kwargs['logging_level'])
        else:
            logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    def refute_estimate(self):

        sample_estimates = np.zeros(self._num_simulations)
        self.logger.info("Refutation over {} simulated datasets of size {} each"
                         .format(self._subset_fraction
                         ,self._subset_fraction*len(self._data.index) )
                        )

        for index in range(self._num_simulations):
            if self._random_state is None:
                new_data = self._data.sample(frac=self._subset_fraction)
            else:
                new_data = self._data.sample(frac=self._subset_fraction,
                                            random_state=self._random_state)
                                            
            new_estimator = CausalEstimator.get_estimator_object(new_data, self._target_estimand, self._estimate)
            new_effect = new_estimator.estimate_effect()
            sample_estimates[index] = new_effect.value

        refute = CausalRefutation(
            self._estimate.value,
            np.mean(sample_estimates),
            refutation_type="Refute: Use a subset of data"
        )

        # We want to see if the estimate falls in the same distribution as the one generated by the refuter
        # Ideally that should be the case as choosing a subset should not have a significant effect on the ability
        # of the treatment to affect the outcome
        refute.add_significance_test_results(
            self.test_significance(self._estimate, sample_estimates)
        )

        return refute
