import argparse
import os
import pickle
from datetime import datetime
from functools import partial
from typing import Optional

import numpy as np
import vg
from sklearn.metrics import r2_score
from sklearn.model_selection import GridSearchCV
from sklearn.neural_network import MLPRegressor

arg_parser = argparse.ArgumentParser(
    prog='generate_displacement_model.py'
)
arg_parser.add_argument(
    '-e',
    '--existing_model',
    type=argparse.FileType('r'),
    nargs=1,
    help='A pickle file containing a partially trained MLPRegressor'
)


side_length = 1
rng = np.random.default_rng()


def corners(length):
    """Get vectors from the center of the QR code to its corners.

    :param length: The length of one side of the QR code.
    :type length: float
    :returns: An array of shape (4,3) containing four x,y,z vectors.
    :rtype: np.ndarray"""
    return np.array([
        [length / 2, length / 2, 0],
        [length / 2, -length / 2, 0],
        [-length / 2, -length / 2, 0],
        [-length / 2, length / 2, 0]
    ])


def pairs(corner_list):
    """Get pairs of adjacent corner vectors.

    :param corner_list: An array of vectors from the center of the
        QR code to its edges.
    :type corner_list: np.ndarray
    :returns: A tuple of two arrays, each of size (4,3)
    :rtype: tuple[np.ndarray, np.ndarray]"""
    return (
        np.concatenate([corner_list, [corner_list[0]]], axis=0),
        np.concatenate([np.roll(corner_list, 1, axis=0), [corner_list[2]]], axis=0)
    )


def get_angle(v1, v2, vector, units='rad'):
    """Get the angle between two vectors given their displacements from the
    center vector.

    :param v1: An array of shape (3,) or (n, 3) containing vectors from the
        center of the QR code to its corners.
    :type v1: np.ndarray
    :param v2: An array of shape (3,) or (n, 3) containing vectors from the
        center of the QR code to its corners.
    :type v2: np.ndarray
    :param units: The angle units to return the result in. Either 'rad' or
        'deg'.
    :type units: str
    :param vector:
    :type vector: np.ndarray
    :returns: Either a single value if v1 and v2 have shape (3,), or an array
        of shape (n,), where v1 and v2 have shape (n, 3). 3-vectors from v1
        and v2 are compared pair-wise.
    :rtype: np.ndarray"""
    result = vg.angle(
        v1 + np.tile(vector, (v1.shape[0] if len(v1.shape) > 1 else 1, 1)),
        v2 + np.tile(vector, (v2.shape[0] if len(v2.shape) > 1 else 1, 1)),
        units=units
    )
    return result


def generate_learning_data(n, x_range, y_range, z_range):
    """Generate a numpy array of training/testing data.

    :param n: The number of training examples to generate.
    :type n: int
    :param x_range: A minimum and maximum for the x-value.
    :type x_range: tuple[float, float]
    :param y_range: A minimum and maximum for the y-value.
    :type y_range: tuple[float, float]
    :param z_range: A minimum and maximum for the z-value.
    :type z_range: tuple[float, float]
    :returns A tuple containing learning data. The first value is
        input, the second is correct output.
    :rtype: tuple[np.ndarray, np.ndarray]"""
    corner_pairs = pairs(corners(side_length))
    angle_func = partial(get_angle, *corner_pairs)
    vectors = np.apply_along_axis(
        func1d=lambda v: np.array([v[0] * v[2] / 5, v[1] * v[2] / 5, v[2]]),
        arr=rng.uniform(*zip(x_range, y_range, z_range), (n, 3)),
        axis=1
    )

    angles = np.apply_along_axis(func1d=angle_func, axis=1, arr=vectors)
    return angles, vectors


def generate_displacement_model(existing_model=None):
    """Train a regressor to recognize displacement from QR angles.

    This function will run continuously until cancelled by a KeyboardInterrupt.
    That is, the user must press Ctrl-C to exit.

    :param existing_model: The filepath of an optional model to start with
        rather than creating a new one.
    :type existing_model: str
    :returns: A regressor trained to take four angles as input and return
        (x,y,z) coordinates as output.
    :rtype: MLPRegressor"""
    xyz_range = (-2, 2), (-2, 2), (0.001, 20)
    n = 1000000
    num_rounds = 0
    if existing_model:
        with open(existing_model, 'rb') as model_file:
            regressor = pickle.load(model_file)
        print(f'Using existing model "{existing_model}"')
    else:
        regressor = MLPRegressor(
            hidden_layer_sizes=(16, 16, 16, 16),
            activation='tanh',
            warm_start=True
        )
        print('Generated new model')
    testing_input, testing_true_output = generate_learning_data(100000, *xyz_range)
    print('Starting training...')
    input_data, true_output = generate_learning_data(n, *xyz_range)
    print('Fitting regressor, this can take a while (as in hours)...')
    regressor.fit(X=input_data, y=true_output)
    num_rounds += 1

    predicted_output = regressor.predict(testing_input)
    score = r2_score(testing_true_output, predicted_output)
    print(
        f'[Round {num_rounds:4}][{datetime.now()}] {n * num_rounds:10} samples, '
        f'R² = {score:7.4f}'
    )
    return regressor


def go(n, xyz_range, *_):
    """Wrapper function for go, as Pool.imap requires that the function take an additional arg.

    :param n: The number of training samples to generate.
    :type n: int
    :param xyz_range: A tuple of the x, y, z minimum and maximum values.
    :type xyz_range: tuple[tuple[float, float], tuple[float, float], tuple[float, float]]
    :returns A tuple containing learning data. The first value is
        input, the second is correct output.
    :rtype: tuple[np.ndarray, np.ndarray]"""
    return _go(n, xyz_range)


def _go(n, xyz_range):
    """A function which generates one round worth of training data.

    Used by a multiprocessing pool to generate data in parallel.
    :param n: The number of training samples to generate.
    :type n: int
    :param xyz_range: A tuple of the x, y, z minimum and maximum values.
    :type xyz_range: tuple[tuple[float, float], tuple[float, float], tuple[float, float]]
    :returns A tuple containing learning data. The first value is
        input, the second is correct output.
    :rtype: tuple[np.ndarray, np.ndarray]"""
    pid = os.getpid()
    print(f'Process {pid} started!')
    training_data = generate_learning_data(n, *xyz_range)
    print(f'Training data ready on {pid}!')
    return training_data


if __name__ == '__main__':
    args = arg_parser.parse_args()
    model = generate_displacement_model(existing_model=args.existing_model)
    print('Saving regressor...')
    with open('../assets/displacement_detection_models/regressor.pkl', 'wb') as pickle_file:
        pickle.dump(model, pickle_file)
    print('Regressor saved!')
