import copy

import numpy as np
import pandas as pd
import logging
from joblib import Parallel, delayed


from dowhy.causal_refuter import CausalRefutation
from dowhy.causal_refuter import CausalRefuter
from dowhy.causal_estimator import CausalEstimator, CausalEstimate
from dowhy.utils.api import parse_state

class PlaceboTreatmentRefuter(CausalRefuter):
    """Refute an estimate by replacing treatment with a randomly-generated placebo variable.

    Supports additional parameters that can be specified in the refute_estimate() method. For joblib-related parameters (n_jobs, verbose, prefer, require), please refer to the joblib documentation for more details (https://joblib.readthedocs.io/en/latest/generated/joblib.Parallel.html).

    :param placebo_type: Default is to generate random values for the treatment. If placebo_type is "permute", then the original treatment values are permuted by row.
    :type placebo_type: str, optional

    :param num_simulations: The number of simulations to be run, which is ``CausalRefuter.DEFAULT_NUM_SIMULATIONS`` by default
    :type num_simulations: int, optional

    :param random_state: The seed value to be added if we wish to repeat the same random behavior. If we want to repeat the same behavior we push the same seed in the psuedo-random generator.
    :type random_state: int, RandomState, optional

    # now the joblib parameters are saved in base CausalRefuter class in its init method
    # but should their description still be here? CausalRefuter init method doesn't have a docstring
    :param n_jobs: The maximum number of concurrently running jobs. If -1 all CPUs are used. If 1 is given, no parallel computing code is used at all (this is the default).
    :type n_jobs: int, optional, default: None

    :param verbose: The verbosity level: if non zero, progress messages are printed. Above 50, the output is sent to stdout. The frequency of the messages increases with the verbosity level. If it more than 10, all iterations are reported. The default is 0.
    :type verbose: int, optional

    # are below two descriptions good enough, don't feel like I understand this fully but using wording from joblib docs again
    :param prefer: Soft hint to choose the default backend. The default process-based backend is 'loky' and the default thread-based backend is 'threading'.
    :type prefer: str in {'processes', 'threads'}, optional

    :param require: Soft hint to choose the default backend. The default process-based backend is 'loky' and the default thread-based backend is 'threading'.
    :type require: 'sharedmem' or None, optional
    """

    # Default value of the p value taken for the distribution
    DEFAULT_PROBABILITY_OF_BINOMIAL = 0.5
    # Number of Trials: Number of cointosses to understand if a sample gets the treatment
    DEFAULT_NUMBER_OF_TRIALS = 1
    # Mean of the Normal Distribution
    DEFAULT_MEAN_OF_NORMAL = 0
    # Standard Deviation of the Normal Distribution
    DEFAULT_STD_DEV_OF_NORMAL = 0

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._placebo_type = kwargs.pop("placebo_type",None)
        if self._placebo_type is None:
            self._placebo_type = "Random Data"
        self._num_simulations = kwargs.pop("num_simulations",CausalRefuter.DEFAULT_NUM_SIMULATIONS)
        self._random_state = kwargs.pop("random_state",None)

        self.logger = logging.getLogger(__name__)


    def refute_estimate(self):
        # only permute is supported for iv methods
        if self._target_estimand.identifier_method.startswith("iv"):
            if self._placebo_type != "permute":
                self.logger.error("Only placebo_type=''permute'' is supported for creating placebo for instrumental variable estimation methods")
                raise ValueError("Only placebo_type=''permute'' is supported for creating placebo for instrumental variable estimation methods.")

        # We need to change the identified estimand
        # We make a copy as a safety measure, we don't want to change the
        # original DataFrame
        identified_estimand = copy.deepcopy(self._target_estimand)
        identified_estimand.treatment_variable = ["placebo"]
        if self._target_estimand.identifier_method.startswith("iv"):
            identified_estimand.instrumental_variables = ["placebo_" + s for s in identified_estimand.instrumental_variables]
            # For IV methods, the estimating_instrument_names should also be
            # changed. So we change it inside the estimate and then restore it
            # back at the end of this method.
            if self._estimate.params["method_params"] is not None and "iv_instrument_name" in self._estimate.params["method_params"]:
                self._estimate.params["method_params"]["iv_instrument_name"] = \
                ["placebo_" + s for s in parse_state(self._estimate.params["method_params"]["iv_instrument_name"])]

        self.logger.info("Refutation over {} simulated datasets of {} treatment"
                        .format(self._num_simulations
                        ,self._placebo_type)
                        )

        num_rows = self._data.shape[0]
        treatment_name = self._treatment_name[0] # Extract the name of the treatment variable
        type_dict = dict( self._data.dtypes )

        def refute_once():
            if self._placebo_type == "permute":
                permuted_idx = None
                if self._random_state is None:
                    permuted_idx = np.random.choice(self._data.shape[0],
                            size=self._data.shape[0], replace=False)

                else:
                    permuted_idx = self._random_state.choice(self._data.shape[0],
                            size=self._data.shape[0], replace=False)
                new_treatment = self._data[self._treatment_name].iloc[permuted_idx].values
                if self._target_estimand.identifier_method.startswith("iv"):
                    new_instruments_values = self._data[self._estimate.estimator.estimating_instrument_names].iloc[permuted_idx].values
                    new_instruments_df = pd.DataFrame(new_instruments_values,
                            columns=["placebo_" + s for s in self._data[self._estimate.estimator.estimating_instrument_names].columns])
            else:
                if 'float' in type_dict[treatment_name].name :
                    self.logger.info("Using a Normal Distribution with Mean:{} and Variance:{}"
                                     .format(PlaceboTreatmentRefuter.DEFAULT_MEAN_OF_NORMAL
                                     ,PlaceboTreatmentRefuter.DEFAULT_STD_DEV_OF_NORMAL)
                                     )
                    new_treatment = np.random.randn(num_rows)*PlaceboTreatmentRefuter.DEFAULT_STD_DEV_OF_NORMAL + \
                                    PlaceboTreatmentRefuter.DEFAULT_MEAN_OF_NORMAL

                elif 'bool' in type_dict[treatment_name].name :
                    self.logger.info("Using a Binomial Distribution with {} trials and {} probability of success"
                                    .format(PlaceboTreatmentRefuter.DEFAULT_NUMBER_OF_TRIALS
                                    ,PlaceboTreatmentRefuter.DEFAULT_PROBABILITY_OF_BINOMIAL)
                                    )
                    new_treatment = np.random.binomial(PlaceboTreatmentRefuter.DEFAULT_NUMBER_OF_TRIALS,
                                                       PlaceboTreatmentRefuter.DEFAULT_PROBABILITY_OF_BINOMIAL,
                                                       num_rows).astype(bool)

                elif 'int' in type_dict[treatment_name].name :
                    self.logger.info("Using a Discrete Uniform Distribution lying between {} and {}"
                    .format(self._data[treatment_name].min()
                    ,self._data[treatment_name].max())
                    )
                    new_treatment = np.random.randint(low=self._data[treatment_name].min(),
                                                      high=self._data[treatment_name].max(),
                                                      size=num_rows)

                elif 'category' in type_dict[treatment_name].name :
                    categories = self._data[treatment_name].unique()
                    self.logger.info("Using a Discrete Uniform Distribution with the following categories:{}"
                    .format(categories))
                    sample = np.random.choice(categories, size=num_rows)
                    new_treatment = pd.Series(sample, index=self._data.index).astype('category')

            # Create a new column in the data by the name of placebo
            new_data = self._data.assign(placebo=new_treatment)
            if self._target_estimand.identifier_method.startswith("iv"):
                new_data = pd.concat((new_data, new_instruments_df), axis=1)
            # Sanity check the data
            self.logger.debug(new_data[0:10])
            new_estimator = CausalEstimator.get_estimator_object(new_data, identified_estimand, self._estimate)
            new_effect = new_estimator.estimate_effect()
            return new_effect.value

        # Run refutation in parallel
        sample_estimates = Parallel(
            n_jobs=self._n_jobs, 
            verbose=self._verbose,
            prefer=self._prefer,
            require=self._require
        )(delayed(refute_once)() for _ in range(self._num_simulations))
        sample_estimates = np.array(sample_estimates)

        # Restoring the value of iv_instrument_name
        if self._target_estimand.identifier_method.startswith("iv"):
            if self._estimate.params["method_params"] is not None and "iv_instrument_name" in self._estimate.params["method_params"]:
                self._estimate.params["method_params"]["iv_instrument_name"] = \
                [s.replace("placebo_","",1) for s in parse_state(self._estimate.params["method_params"]["iv_instrument_name"])]
        refute = CausalRefutation(self._estimate.value,
                                  np.mean(sample_estimates),
                                  refutation_type="Refute: Use a Placebo Treatment")

        # Note: We hardcode the estimate value to ZERO as we want to check if it falls in the distribution of the refuter
        # Ideally we should expect that ZERO should fall in the distribution of the effect estimates as we have severed any causal
        # relationship between the treatment and the outcome.
        dummy_estimator = CausalEstimate(
                estimate=0,
                control_value=self._estimate.control_value,
                treatment_value=self._estimate.treatment_value,
                target_estimand=self._estimate.target_estimand,
                realized_estimand_expr=self._estimate.realized_estimand_expr)

        refute.add_significance_test_results(
            self.test_significance(dummy_estimator, sample_estimates)
        )
        refute.add_refuter(self)
        return refute
