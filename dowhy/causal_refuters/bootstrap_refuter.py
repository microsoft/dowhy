from dowhy.causal_refuter import CausalRefuter, CausalRefutation
import numpy as np
from sklearn.utils import resample
import logging

class BootstrapRefuter(CausalRefuter):
    """
    Refute an estimate by running it on a random sample of the original data.
    It supports additional parameters that can be specified in the refute_estimate() method.
    - 'required_variables': int, list
    An integer argument means that
    - 'sample_size': int, Size of the original data by default
    The size of each bootstrap sample
    - 'random_state': int, RandomState, None by default
    The seed value to be added if we wish to repeat the same random behavior. For this purpose, 
    we repeat the same seed in the psuedo-random generator.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._num_simulations = kwargs.pop("required_variables", None)
        self._sample_size = kwargs.pop("sample_size",len(self._data))
        self._random_state = kwargs.pop("random_state",None)

        if 'logging_level' in kwargs:
            logging.basicConfig(level=kwargs['logging_level'])
        else:
            logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
    def refute_estimate(self, *args, **kwargs):
        if self._sample_size > len(self._data):
                self.logger.warning("The sample size is larger than the population size")

        sample_estimates = np.zeros(self._num_simulations)
        self.logger.info("Refutation over {} simulated datasets of size {} each"
                         .format(self._num_simulations
                         ,self._sample_size )
                        ) 
        
        for index in range(self._num_simulations):
            if self._random_state is None:
                new_data = resample(self._data, 
                                n_samples=self._sample_size )
            else:
                new_data = resample(self._data,
                                    n_samples=self._sample_size,
                                    random_state=self._random_state )

            new_estimator = self.get_estimator_object(new_data, self._target_estimand, self._estimate)
            new_effect = new_estimator.estimate_effect()
            sample_estimates[index] = new_effect.value

        refute = CausalRefutation(
            self._estimate.value,
            np.mean(sample_estimates),
            refutation_type="Refute: Bootstrap Sample Dataset"
        )

        # We want to see if the estimate falls in the same distribution as the one generated by the refuter
        # Ideally that should be the case as bootstrapping should not have a significant effect on the ability
        # of the treatment to affect the outcome
        refute.add_significance_test_results(
            self.test_significance(self._estimate, sample_estimates)
        )

        return refute

