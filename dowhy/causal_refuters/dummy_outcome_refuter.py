import copy
import math
import numpy as np
import pandas as pd
import logging

from collections import OrderedDict
from dowhy.causal_refuter import CausalRefutation
from dowhy.causal_refuter import CausalRefuter
from dowhy.causal_estimator import CausalEstimator,CausalEstimate

from sklearn.linear_model import LinearRegression
from sklearn.neighbors import KNeighborsRegressor
from sklearn.svm import SVR
from sklearn.ensemble import RandomForestRegressor
from sklearn.neural_network import MLPRegressor

class DummyOutcomeRefuter(CausalRefuter):
    """Refute an estimate by replacing the outcome with a randomly generated variable.
    
    This allows us to have a well defined effect of the treatment on the outcome.

    1. We find f(W) for a fixed value of t
    2. For all the other values of t. We obtain the value of dummy outcome as:
       ``y_dummy = h(t) + f(W)``
        
    ::

        If we originally started out with

               W
            /    \\
            t --->y
        
        On estimating,
        y_dummy = f(W)

               W
            /    \\
            t --|->y
        
        This ensures that we try to capture as much of W--->Y as possible

        On adding h(t)

               W
            /    \\
            t --->y
              h(t)
    
    Supports additional parameters that can be specified in the refute_estimate() method.

    Attributes:
        num_simulations (int, optional): The number of simulations to be run. 
            This defaults to ``CausalRefuter.DEFAULT_NUM_SIMULATIONS``

        transformation_list (list, optional): The transformation_list is a list of actions to be performed to obtain the outcome.
            ``DummyOutcomeRefuter.DEFAULT_TRANSFORMATION`` is the default transformation, in which the dummy outcome is white noise.
            
            Each of the actions within a transformation is one of the following types:

            * function argument: function ``pd.Dataframe -> np.ndarray``
              
              It takes in a function that takes the input data frame as the input and outputs the outcome
              variable. This allows us to create an output varable that only depends on the covariates and does not depend 
              on the treatment variable.

            * string argument

                * Currently it supports some common estimators like

                    1. Linear Regression
                    2. K Nearest Neighbours
                    3. Support Vector Machine
                    4. Neural Network
                    5. Random Forest
                
                * Or functions such as:

                    1. Permute
                      This permutes the rows of the outcome, disassociating any effect of the treatment on the outcome.
                    2. Noise
                      This adds white noise to the outcome with white noise, reducing any causal relationship with the treatment.
                    3. Zero
                      It replaces all the values in the outcome by zero
            
            Examples:

            The transformation_list is of the following form:

            * If the function ``pd.Dataframe -> np.ndarray`` is already defined.
              ``[(func,func_params),('permute', {'permute_fraction': val} ), ('noise', {'std_dev': val} )]``
            * If a function from the above list is used
              ``[('knn',{'n_neighbors':5}), ('permute', {'permute_fraction': val} ), ('noise', {'std_dev': val} )]``

        true_causal_effect (function): A function that is used used to get the True Causal Effect for the modelled dummy outcome. 
            It defaults to ``DummyOutcomeRefuter.DEFAULT_TRUE_CAUSAL_EFFECT``, which means that there is no relationship between the treatment and outcome in the
            dummy data.

            The equation for the dummy outcome is given by
            ``y_hat = h(t) + f(W)``
            
            where

            * ``y_hat`` is the dummy outcome 
            * ``h(t)`` is the function that gives the true causal effect 
            * ``f(W)`` is the best estimate of ``y`` obtained keeping ``t`` constant. This ensures that the variation in output of function ``f(w)`` is not caused by `t`.

            .. note:: The true causal effect should take an input of the same shape as the treatment and the output should match the shape of the outcome

        required_variables (int, list, bool) : The list of variables to be used as the input for ``y~f(W)``
            This is ``True`` by default, which in turn selects all variables leaving the treatment and the outcome

            1. An integer argument refers to how many variables will be used for estimating the value of the outcome
            2. A list explicitly refers to which variables will be used to estimate the outcome
               Furthermore, it gives the ability to explictly select or deselect the covariates present in the estimation of the 
               outcome. This is done by either adding or explicitly removing variables from the list as shown below: 
            
                For example:

                We need to pass required_variables = ``[W0,W1]`` if we want ``W0`` and ``W1``.
                
                We need to pass required_variables = ``[-W0,-W1]`` if we want all variables excluding ``W0`` and ``W1``.
            
            3. If the value is True, we wish to include all variables to estimate the value of the outcome.
               A False value is INVALID and will result in an error. 
            
            .. note:: These inputs are fed to the function for estimating the outcome variable. The same set of required_variables is used for each
                instance of an internal estimation function.

        bucket_size_scale_factor (float): For continuous data, the scale factor helps us scale the size of the bucket used on the data.
            The default scale factor is ``DummyOutcomeRefuter.DEFAULT_BUCKET_SCALE_FACTOR``
            ::

                The number of buckets is given by: 
                    (max value - min value)
                    ------------------------
                    (scale_factor * std_dev)

        min_data_point_threshold (int): The minimum number of data points for an estimator to run.
            This defaults to ``DummyOutcomeRefuter.MIN_DATA_POINT_THRESHOLD``. If the number of data points is too few
            for a certain category, we make use of the ``DummyOutcomeRefuter.DEFAULT_TRANSFORMATION`` for generaring the dummy outcome            
    
    """
    
    # The currently supported estimators
    SUPPORTED_ESTIMATORS = ["linear_regression", "knn", "svm", "random_forest", "neural_network"]
    # The default standard deviation for noise
    DEFAULT_STD_DEV = 0.1
    # The default scaling factor to determine the bucket size 
    DEFAULT_BUCKET_SCALE_FACTOR = 0.5
    # The minimum number of points for the estimator to run
    MIN_DATA_POINT_THRESHOLD = 30
    # The Default Transformation, when no arguments are given, or if the number of data points are insufficient for an estimator
    DEFAULT_TRANSFORMATION = [("zero",""),("noise", {'std_dev': 1} )]
    # The Default True Causal Effect, this is taken to be ZERO by default
    DEFAULT_TRUE_CAUSAL_EFFECT = lambda x: 0

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self._num_simulations = kwargs.pop("num_simulations", CausalRefuter.DEFAULT_NUM_SIMULATIONS)
        self._transformation_list = kwargs.pop("transformation_list", DummyOutcomeRefuter.DEFAULT_TRANSFORMATION)
        self._true_causal_effect = kwargs.pop("true_causal_effect", DummyOutcomeRefuter.DEFAULT_TRUE_CAUSAL_EFFECT)
        self._bucket_size_scale_factor = kwargs.pop("bucket_size_scale_factor", DummyOutcomeRefuter.DEFAULT_BUCKET_SCALE_FACTOR)
        self._min_data_point_threshold = kwargs.pop("min_data_point_threshold", DummyOutcomeRefuter.MIN_DATA_POINT_THRESHOLD)
        required_variables = kwargs.pop("required_variables", True)
        
        if required_variables is False:
            raise ValueError("The value of required_variables cannot be False")

        self._chosen_variables = self.choose_variables(required_variables)

        if 'logging_level' in kwargs:
            logging.basicConfig(level=kwargs['logging_level'])
        else:
            logging.basicConfig(level=logging.INFO)
        
        self.logger = logging.getLogger(__name__)

    def refute_estimate(self):

        # We need to change the identified estimand
        # We thus, make a copy. This is done as we don't want
        # to change the original DataFrame
        identified_estimand = copy.deepcopy(self._target_estimand)
        identified_estimand.outcome_variable = ["dummy_outcome"]

        self.logger.info("Refutation over {} simulated datasets".format(self._num_simulations) )
        self.logger.info("The transformation passed: {}".format(self._transformation_list) )

        simulation_results = []
        refute_list = []
        
        # We use collections.OrderedDict to maintain the order in which the data is stored
        causal_effect_map = OrderedDict()

        # Check if we are using an estimator in the transformation list 
        no_estimator = self.check_for_estimator()
        
        # The rationale behind ordering of the loops is the fact that we induce randomness everytime we create the 
        # Train and the Validation Datasets. Thus, we run the simulation loop followed by the training and the validation
        # loops. Thus, we can get different values everytime we get the estimator.
        for _ in range( self._num_simulations ):
            estimates = []
            
            if no_estimator:
                # We set X_train = 0 and outcome_train to be 0
                validation_df = self._data
                X_train = None
                outcome_train = None
                X_validation = validation_df[self._chosen_variables].values
                outcome_validation = validation_df['y'].values

                # Get the final outcome, after running through all the values in the transformation list
                outcome_validation = self.process_data(X_train, outcome_train, X_validation, outcome_validation, self._transformation_list)
                
                # Check if the value of true effect has been already stored
                # We use None as the key as we have no base category for this refutation
                if None not in causal_effect_map:
                    # As we currently support only one treatment
                    causal_effect_map[None] = self._true_causal_effect( validation_df[ self._treatment_name[0] ] )  
                
                outcome_validation += causal_effect_map[None]     
                new_data = validation_df.assign(dummy_outcome=outcome_validation)
                new_estimator = CausalEstimator.get_estimator_object(new_data, identified_estimand, self._estimate)
                new_effect = new_estimator.estimate_effect()
                estimates.append(new_effect.value)

            else:
                groups = self.preprocess_data_by_treatment()
                for key_train, _ in groups:
                    X_train = groups.get_group(key_train)[self._chosen_variables].values
                    outcome_train = groups.get_group(key_train)['y'].values
                    validation_df = []
                    transformation_list = self._transformation_list

                    for key_validation, _ in groups:
                        if key_validation != key_train:
                            validation_df.append(groups.get_group(key_validation))

                    validation_df = pd.concat(validation_df)
                    X_validation = validation_df[self._chosen_variables].values
                    outcome_validation = validation_df['y'].values

                    # If the number of data points is too few, run the default transformation: [("zero",""),("noise", {'std_dev':1} )]
                    if X_train.shape[0] <= self._min_data_point_threshold:
                        transformation_list = DummyOutcomeRefuter.DEFAULT_TRANSFORMATION

                    outcome_validation = self.process_data(X_train, outcome_train, X_validation, outcome_validation, transformation_list)

                    # Check if the value of true effect has been already stored
                    # This ensures that we calculate the causal effect only once.
                    # We use key_train as we map data with respect to the base category of the data
                    
                    if key_train not in causal_effect_map:
                        # As we currently support only one treatment
                        causal_effect_map[key_train] = self._true_causal_effect( validation_df[ self._treatment_name[0] ] )
                    
                    # Add h(t) to f(W) to get the dummy outcome
                    outcome_validation += causal_effect_map[key_train]      
                    new_data = validation_df.assign(dummy_outcome=outcome_validation)
                    new_estimator = CausalEstimator.get_estimator_object(new_data, identified_estimand, self._estimate)
                    new_effect = new_estimator.estimate_effect()
                    estimates.append(new_effect.value)

            simulation_results.append(estimates)

        # We convert to ndarray for ease in indexing
        # The data is of the form
        # sim1: cat1 cat2 ... catn
        # sim2: cat1 cat2 ... catn
        simulation_results = np.array(simulation_results)

        # Note: We would hardcode the estimate value to ZERO as we want to check if it falls in the distribution of the refuter
        # Ideally we should expect that ZERO should fall in the distribution of the effect estimates as we have severed any causal 
        # relationship between the treatment and the outcome.
        # On the other hand, if we define a causal effect h(t) then we would like to do the same, that is, find if it falls in the 
        # distribution of the refuter.

        if no_estimator:
            
            dummy_estimate = CausalEstimate(
                    estimate = causal_effect_map[None],
                    target_estimand =self._estimate.target_estimand,
                    realized_estimand_expr=self._estimate.realized_estimand_expr)
            
            refute = CausalRefutation(
                        dummy_estimate.value,
                        np.mean(simulation_results),
                        refutation_type="Refute: Use a Dummy Outcome"
                    )

            refute.add_significance_test_results(
                self.test_significance(dummy_estimate, simulation_results)
            )

            refute_list.append(refute)

        else:
            # True Causal Effect list
            causal_effect_list = list( causal_effect_map.values() )
            # Iterating through the refutation for each category
            for category in range(simulation_results.shape[1]):
                dummy_estimate = CausalEstimate(
                    estimate = causal_effect_list[category],
                    target_estimand =self._estimate.target_estimand,
                    realized_estimand_expr=self._estimate.realized_estimand_expr)
                
                refute = CausalRefutation(
                    dummy_estimate.value,
                    np.mean(simulation_results[:, category]),
                    refutation_type="Refute: Use a Dummy Outcome"
                )

                refute.add_significance_test_results(
                    self.test_significance(dummy_estimate, simulation_results[:, category])
                )

                refute_list.append(refute)

        return refute_list

    def process_data(self, X_train, outcome_train, X_validation, outcome_validation, transformation_list):
        """
        We process the data by first training the estimators in the transformation_list on X_train and outcome_train.
        We then apply the estimators on X_validation to get the value of the dummy outcome, which we store in outcome_validation.

        Args:
            X_train (np.ndarray): The data of the covariates which is used to train an estimator. It corresponds to the data of a single category of the treatment
            
            outcome_train (np.ndarray): This is used to hold the intermediate values of the outcome variable in the transformation list
            
            For Example:

            ``[ ('permute', {'permute_fraction': val} ), (func,func_params)]``
            
            The value obtained from permutation is used as an input for the custom estimator.
            
            X_validation (np.ndarray): The data of the covariates that is fed to a trained estimator to generate a dummy outcome
            
            outcome_validation (np.ndarray): This variable stores the dummy_outcome generated by the transformations
            
            transformation_list (np.ndarray): The list of transformations on the outcome data required to produce a dummy outcome 
        """
        for action, func_args in transformation_list:
            if callable(action):
                estimator = action(X_train, outcome_train, **func_args)
                outcome_train = estimator(X_train)
                outcome_validation = estimator(X_validation)
            elif action in DummyOutcomeRefuter.SUPPORTED_ESTIMATORS:
                estimator = self._estimate_dummy_outcome(action, X_train, outcome_train, **func_args)
                outcome_train = estimator(X_train)
                outcome_validation = estimator(X_validation)
            elif action == 'noise':
                if X_train is not None:
                    outcome_train = self._noise(outcome_train, **func_args)
                outcome_validation = self._noise(outcome_validation, **func_args)
            elif action == 'permute':
                if X_train is not None:
                    outcome_train = self._permute(outcome_train, **func_args)
                outcome_validation = self._permute(outcome_validation, **func_args)
            elif action =='zero':
                if X_train is not None:
                    outcome_train = np.zeros(outcome_train.shape)
                outcome_validation = np.zeros(outcome_validation.shape)

        return outcome_validation
            
    def check_for_estimator(self):
        """
        This function checks if there is an estimator in the transformation list.
        If there are no estimators, it allows us to optimize processing by skipping the 
        data preprocessing and running the transformations on the whole dataset.
        """
        for action,_ in self._transformation_list:
            if callable(action) or action in DummyOutcomeRefuter.SUPPORTED_ESTIMATORS:
                return False
            
        return True

    def preprocess_data_by_treatment(self):
        """
        This function groups data based on the data type of the treatment.
        
        Expected variable types supported for the treatment:

        * bool
        * pd.categorical
        * float
        * int
        
        :returns: ``pandas.core.groupby.generic.DataFrameGroupBy``
        """
        assert len(self._treatment_name) == 1, "At present, DoWhy supports a simgle treatment variable"
        
        treatment_variable_name = self._treatment_name[0] # As we only have a single treatment
        variable_type = self._data[treatment_variable_name].dtypes
        
        if bool == variable_type:
            groups = self._data.groupby(treatment_variable_name)
            return groups
        # We use string arguments to account for both 32 and 64 bit varaibles
        elif 'float' in variable_type.name or \
               'int' in variable_type.name:
            # action for continuous variables
            data =  self._data
            std_dev = data[treatment_variable_name].std()
            num_bins = ( data.max() - data.min() )/ (self._bucket_size_scale_factor * std_dev)
            data['bins'] = pd.cut(data[treatment_variable_name], num_bins)
            groups = data.groupby('bins')
            data.drop('bins', axis=1, inplace=True)
            return groups

        elif 'categorical' in variable_type.name:
            # Action for categorical variables
            groups = data.groupby(treatment_variable_name)
            groups = data.groupby('bins')
            return groups
        else:
            raise ValueError("Passed {}. Expected bool, float, int or categorical.".format(variable_type.name))

    def _estimate_dummy_outcome(self, action, X_train, outcome, **func_args):
        """
        A function that takes in any sklearn estimator and returns a trained estimator

        - 'action': str
        The sklearn estimator to be used.
        - 'X_train': np.ndarray
        The variable used to estimate the value of outcome.
        - 'outcome': np.ndarray
        The variable which we wish to estimate.
        - 'func_args': variable length keyworded argument
        The parameters passed to the estimator.
        """
        estimator = self._get_regressor_object(action, **func_args)
        X = X_train
        y = outcome
        estimator = estimator.fit(X, y)
        
        return estimator.predict
    
    def _get_regressor_object(self, action, **func_args):
        """
        Return a sklearn estimator object based on the estimator and corresponding parameters

        - 'action': str
        The sklearn estimator used.
        - 'func_args': variable length keyworded argument
        The parameters passed to the sklearn estimator.
        """
        if  action == "linear_regression":
            return LinearRegression(**func_args)
        elif action == "knn":
            return KNeighborsRegressor(**func_args)
        elif action == "svm":
            return SVR(**func_args)
        elif action == "random_forest":
            return RandomForestRegressor(**func_args)
        elif action == "neural_network":
            return MLPRegressor(**func_args)
        else:
            raise ValueError("The function: {} is not supported by dowhy at the moment.".format(action))

    def _permute(self, outcome, permute_fraction):
        '''
        If the permute_fraction is 1, we permute all the values in the outcome.
        Otherwise we make use of the Fisher Yates shuffle.
        Refer to https://en.wikipedia.org/wiki/Fisher%E2%80%93Yates_shuffle for more details.

        'outcome': np.ndarray
        The outcome variable to be permuted.
        'permute_fraction': float [0, 1]
        The fraction of rows permuted.
        '''
        if permute_fraction == 1:
            outcome = pd.DataFrame(outcome)
            outcome.columns = ['y']
            return outcome['y'].sample(frac=1).values
        elif permute_fraction < 1:
            permute_fraction /= 2 # We do this as every swap leads to two changes 
            changes = np.where( np.random.uniform(0,1,outcome.shape[0]) <= permute_fraction )[0] # As this is tuple containing a single element (array[...])
            num_rows = outcome.shape[0]
            for change in changes:
                if change + 1 < num_rows:
                    index = np.random.randint(change+1,num_rows)
                    temp = outcome[change]
                    outcome[change] = outcome[index]
                    outcome[index] = temp
            return outcome
        else:
            raise ValueError("The value of permute_fraction is {}. Which is greater than 1.".format(permute_fraction))

    def _noise(self, outcome, std_dev):
        """
        Add white noise with mean 0 and standard deviation = std_dev

        - 'outcome': np.ndarray
        The outcome variable, to which the white noise is added.
        - 'std_dev': float
        The standard deviation of the white noise.
        """
        return outcome + np.random.normal(scale=std_dev,size=outcome.shape[0])
