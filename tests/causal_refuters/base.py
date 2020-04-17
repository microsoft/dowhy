import dowhy.datasets
from dowhy import CausalModel
import logging

class TestRefuter(object):
    def __init__(self, error_tolerance, estimator_method, refuter_method,
            outcome_function=None, params = None, confounders_effect_on_t=None, 
            confounders_effect_on_y=None, effect_strength_on_t=None,
            effect_strength_on_y=None, **kwargs):
        self._error_tolerance = error_tolerance
        self.estimator_method = estimator_method
        self.refuter_method = refuter_method
        self.outcome_function = outcome_function
        self.params = params
        self.confounders_effect_on_t = confounders_effect_on_t
        self.confounders_effect_on_y = confounders_effect_on_y
        self.effect_strength_on_t = effect_strength_on_t
        self.effect_strength_on_y = effect_strength_on_y
        
        if 'logging_level' in kwargs:
            logging.basicConfig(level=kwargs['logging_level'])
        else:
            logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

        self.logger.debug(self._error_tolerance)

    def null_refutation_test(self, data=None, dataset="linear", beta=10,
            num_common_causes=1, num_instruments=1, num_samples=100000,
            treatment_is_binary=True):
        # Supports user-provided dataset object
        if data is None:
            data = dowhy.datasets.linear_dataset(beta=beta,
                                             num_common_causes=num_common_causes,
                                             num_instruments=num_instruments,
                                             num_samples=num_samples,
                                             treatment_is_binary=treatment_is_binary)

        print(data['df'])

        print("")
        model = CausalModel(
            data=data['df'],
            treatment=data["treatment_name"],
            outcome=data["outcome_name"],
            graph=data["gml_graph"],
            proceed_when_unidentifiable=True,
            test_significance=None
        )
        target_estimand = model.identify_effect()
        ate_estimate = model.estimate_effect(
            identified_estimand=target_estimand,
            method_name=self.estimator_method,
            test_significance=None
        )
        true_ate = data["ate"]
        self.logger.debug(true_ate)

        if self.refuter_method == "add_unobserved_common_cause":
        # To test if there are any exceptions
            ref = model.refute_estimate(target_estimand, ate_estimate,
                method_name=self.refuter_method,
                confounders_effect_on_treatment = self.confounders_effect_on_t,
                confounders_effect_on_outcome = self.confounders_effect_on_y,
                effect_strength_on_treatment =self.effect_strength_on_t,
                effect_strength_on_outcome=self.effect_strength_on_y)
            self.logger.debug(ref.new_effect)

            # To test if the estimate is identical if refutation parameters are zero
            refute = model.refute_estimate(target_estimand, ate_estimate,
                method_name=self.refuter_method,
                confounders_effect_on_treatment = self.confounders_effect_on_t,
                confounders_effect_on_outcome = self.confounders_effect_on_y,
                effect_strength_on_treatment = 0,
                effect_strength_on_outcome = 0)
            error = abs(refute.new_effect - ate_estimate.value)
            
            print("Error in refuted estimate = {0} with tolerance {1}%. Estimated={2},After Refutation={3}".format(
                error, self._error_tolerance * 100, ate_estimate.value, refute.new_effect)
            )
            res = True if (error < abs(ate_estimate.value) * self._error_tolerance) else False
            assert res

        elif self.refuter_method == "placebo_treatment_refuter":
            if treatment_is_binary is True:
                ref = model.refute_estimate(target_estimand, 
                                        ate_estimate,
                                        method_name=self.refuter_method,
                                        num_simulations=10
                                        )
            else:
                ref = model.refute_estimate(target_estimand, 
                                            ate_estimate,
                                            method_name=self.refuter_method
                                            )
            # This value is hardcoded to be zero as we are runnning this on a linear dataset.
            # Ordinarily, we should expect this value to be zero.
            EXPECTED_PLACEBO_VALUE = 0
            
            error =  abs(ref.new_effect - EXPECTED_PLACEBO_VALUE)

            print("Error in the refuted estimate = {0} with tolerence {1}%. Expected Value={2}, After Refutation={3}".format(
                error, self._error_tolerance * 100, EXPECTED_PLACEBO_VALUE, ref.new_effect)
            )

            print(ref)

            res = True if (error <  self._error_tolerance) else False
            assert res
            
        elif self.refuter_method == "data_subset_refuter":
            if treatment_is_binary is True:
                ref = model.refute_estimate(target_estimand, 
                                        ate_estimate,
                                        method_name=self.refuter_method,
                                        num_simulations=5
                                        )
            else:
                ref = model.refute_estimate(target_estimand, 
                                            ate_estimate,
                                            method_name=self.refuter_method
                                            )
            
            error =  abs(ref.new_effect - ate_estimate.value)

            print("Error in the refuted estimate = {0} with tolerence {1}%. Estimated={2}, After Refutation={3}".format(
                error, self._error_tolerance * 100, ate_estimate.value, ref.new_effect)
            )

            print(ref)

            res = True if (error <  abs(ate_estimate.value)*self._error_tolerance) else False
            assert res
        
        elif self.refuter_method == "bootstrap_refuter":
            if treatment_is_binary is True:
                ref = model.refute_estimate(target_estimand, 
                                        ate_estimate,
                                        method_name=self.refuter_method,
                                        num_simulations=5
                                        )
            else:
                ref = model.refute_estimate(target_estimand, 
                                            ate_estimate,
                                            method_name=self.refuter_method
                                            )
            
            error =  abs(ref.new_effect - ate_estimate.value)

            print("Error in the refuted estimate = {0} with tolerence {1}%. Estimated={2}, After Refutation={3}".format(
                error, self._error_tolerance * 100, ate_estimate.value, ref.new_effect)
            )

            print(ref)

            res = True if (error <  abs(ate_estimate.value)*self._error_tolerance) else False
            assert res

        elif self.refuter_method == "dummy_outcome_refuter":
            if self.outcome_function is None:
                ref = model.refute_estimate(target_estimand,
                                            ate_estimate,
                                            method_name=self.refuter_method,
                                            num_simulations = 2
                                            )
            elif callable(self.outcome_function):
                ref = model.refute_estimate(target_estimand,
                                            ate_estimate,
                                            method_name=self.refuter_method,
                                            outcome_function =self.outcome_function,
                                            num_simulations = 2
                                            )
            else:
                ref = model.refute_estimate(target_estimand,
                                            ate_estimate,
                                            method_name=self.refuter_method,
                                            outcome_function =self.outcome_function,
                                            params = self.params,
                                            num_simulations = 2
                                            )

                # This value is hardcoded to be zero as we are runnning this on a linear dataset.
                # Ordinarily, we should expect this value to be zero.
                EXPECTED_DUMMY_OUTCOME_VALUE = 0

                error = abs( ref.new_effect - EXPECTED_DUMMY_OUTCOME_VALUE)

                print("Error in the refuted estimate = {0} with tolerence {1}%. Expected Value={2}, After Refutation={3}".format(
                    error, self._error_tolerance * 100, EXPECTED_DUMMY_OUTCOME_VALUE, ref.new_effect)
                )

                print(ref)

                res = True if (error <  self._error_tolerance) else False
                # We don't test the accuracy of the string arguments, as they do not purely derive their value from the confounders
                if type(self.outcome_function) is not str: 
                    assert res
 
    def binary_treatment_testsuite(self, num_common_causes=1,tests_to_run="all"):
        self.null_refutation_test(num_common_causes=num_common_causes)
        if tests_to_run != "atleast-one-common-cause":
            self.null_refutation_test(num_common_causes=0)

    def continuous_treatment_testsuite(self, num_common_causes=1,tests_to_run="all"):
        self.null_refutation_test(
            num_common_causes=num_common_causes,
            treatment_is_binary=False)
        if tests_to_run != "atleast-one-common-cause":
            self.null_refutation_test(num_common_causes=0,
                    treatment_is_binary=False)
    
        

