from dowhy.causal_refuter import CausalRefuter, CausalRefutation
import numpy as np
import logging

class DataSubsetRefuter(CausalRefuter):
    """Refute an estimate by rerunning it on a random subset of the original data.

    Supports additional parameters that can be specified in the refute_estimate() method.

    - 'subset_fraction': float, None by default
    Fraction of the data to be used for re-estimation.
    - 'number_of_samples': int, None by default
    The number of samples to be constructed
    - random_state': int, RandomState, None by default
    The seed value to be added if we wish to repeat the same random behavior. If we with to repeat the
    same behavior we push the same seed in the psuedo-random generator
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._subset_fraction = kwargs.pop("subset_fraction", 0.8)
        self._number_of_samples = kwargs.pop("number_of_samples", 200)
        self._random_state = kwargs.pop("random_state",None)

        if 'logging_level' in kwargs:
            logging.basicConfig(level=kwargs['logging_level'])
        else:
            logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    def refute_estimate(self):

        sample_estimates = np.zeros(self._number_of_samples)
        self.logger.info("Subset Fraction:{}\nNumber of Samples:{}"
                         .format(self._subset_fraction
                         ,self._number_of_samples)
                        )

        for index in range( self._number_of_samples):
            if self._random_state is None:
                new_data = self._data.sample(frac=self._subset_fraction)
            else:
                new_data = self._data.sample(frac=self._subset_fraction,
                                            random_state=self._random_state)
                                            
            new_estimator = self.get_estimator_object(new_data, self._target_estimand, self._estimate)
            new_effect = new_estimator.estimate_effect()
            sample_estimates[index] = new_effect.value

        refute = CausalRefutation(
            self._estimate.value,
            np.mean(sample_estimates),
            refutation_type="Refute: Use a subset of data"
        )
        return refute
