import mlflow
import warnings

# Python 2/3 compatibility to avoid deprecated inspect.getargspec
try:
    from inspect import getfullargspec as arg_spec
except ImportError:
    from inspect import getargspec as arg_spec


def try_mlflow_log(fn, *args, **kwargs):
    """
    Catch exceptions and log a warning to avoid autolog throwing.
    """
    try:
        fn(*args, **kwargs)
    except Exception as e:  # pylint: disable=broad-except
        warnings.warn("Logging to MLflow failed: " + str(e), stacklevel=2)


def get_unspecified_default_args(user_args, user_kwargs, all_param_names, all_default_values):
    """
    Determine which default values are used in a call, given args and kwargs that are passed in.

    :param user_args: list of arguments passed in by the user
    :param user_kwargs: dictionary of kwargs passed in by the user
    :param all_param_names: names of all of the parameters of the function
    :param all_default_values: values of all default parameters
    :return: a dictionary mapping arguments not specified by the user -> default value
    """
    num_args_without_default_value = len(all_param_names) - len(all_default_values)

    # all_default_values correspond to the last len(all_default_values) elements of the arguments
    default_param_names = all_param_names[num_args_without_default_value:]

    default_args = dict(zip(default_param_names, all_default_values))

    # The set of keyword arguments that should not be logged with default values
    user_specified_arg_names = set(user_kwargs.keys())

    num_user_args = len(user_args)

    # This checks if the user passed values for arguments with default values
    if num_user_args > num_args_without_default_value:
        num_default_args_passed_as_positional = num_user_args - num_args_without_default_value
        # Adding the set of positional arguments that should not be logged with default values
        names_to_exclude = default_param_names[:num_default_args_passed_as_positional]
        user_specified_arg_names.update(names_to_exclude)

    return {name: value for name, value in default_args.items()
            if name not in user_specified_arg_names}


def log_fn_args_as_params(fn, args, kwargs, unlogged=[]):  # pylint: disable=W0102
    """
    Log parameters explicitly passed to a function.
    :param fn: function whose parameters are to be logged
    :param args: arguments explicitly passed into fn
    :param kwargs: kwargs explicitly passed into fn
    :param unlogged: parameters not to be logged
    :return: None
    """
    # all_default_values has length n, corresponding to values of the
    # last n elements in all_param_names
    all_param_names, _, _, all_default_values = arg_spec(fn)  # pylint: disable=W1505

    # Checking if default values are present for logging.
    # Are there situations in which getfullargspec() won't return an argspec?
    if all_default_values is not None and len(all_default_values) > 0:
        # Logging the default arguments not passed by the user
        defaults = get_unspecified_default_args(args, kwargs, all_param_names, all_default_values)

        for name in [name for name in defaults.keys() if name in unlogged]:
            del defaults[name]
        try_mlflow_log(mlflow.log_params, defaults)

    # Logging the arguments passed by the user
    args_dict = dict((param_name, param_val) for param_name, param_val
                     in zip(all_param_names[:len(args)], args)
                     if param_name not in unlogged)
    if len(args_dict.keys()) > 0:
        try_mlflow_log(mlflow.log_params, args_dict)

    # Logging the kwargs passed by the user
    for param_name in kwargs:
        if param_name not in unlogged:
            try_mlflow_log(mlflow.log_param, param_name, kwargs[param_name])
