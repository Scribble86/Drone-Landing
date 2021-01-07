import json
import math
import pickle
from pathlib import Path
from typing import Optional, Sequence, Mapping, Iterable

import numpy as np
from shapely.geometry import Point
from sklearn.neural_network import MLPRegressor

from angle_unit import AngleUnit
from util import cos_between_vectors


class DisplacementEstimator:
    """The DisplacementEstimator class makes an estimate on the distance between the drone and the target."""

    def __init__(
            self,
            regressor: Optional[MLPRegressor] = None,
            levels: Optional[Mapping] = None,
            fov: float = 60,
            units: AngleUnit = AngleUnit.DEGREES):
        """
        :param regressor: A regressor object. Each regressor is expected to provide the
            `regressor.predict` function. If None, init will instead search `assets/displacement_detection_models`
            for pickle files matching the filename `regressor.pkl`.
        :param levels: A dictionary-like object mapping from level names (e.g. "0") to scaling factors.
        :param fov: The horizontal field of view. Units are specified by the units argument.
        :param units: The units of the fov argument.
        """
        self.fov_unit = units
        self.horizontal_fov = fov
        if self.fov_unit == AngleUnit.DEGREES:
            rads_per_degree = 2 * math.pi / 360
            self.horizontal_fov *= rads_per_degree
        if regressor:
            self._regressor = regressor
        else:
            model_path = Path('../assets/displacement_detection_models/regressor.pkl')
            with open(model_path, 'rb') as model_file:
                try:
                    self._regressor = pickle.load(model_file)
                except pickle.UnpicklingError:
                    print(f'ALERT: File "{model_path}" is named like a pickled regressor but cannot be unpickled.')
                    raise
        if levels:
            self.levels = levels
        else:
            levels_path = Path('../config/qr_sizes.json')
            with open(levels_path, 'r') as levels_file:
                self.levels = json.load(levels_file)

    def get_hull_angles(
            self,
            hull: Iterable[Iterable[float]],
            image_height: int,
            image_width: int):
        """Calculate the hull angles given the four corners of the hull and some information about the image.

        This function uses the pinhole camera model to determine the angular diameter of the sides of the QR code.
        https://en.wikipedia.org/wiki/Pinhole_camera_model

        :param hull: An iterable of points. These points are the corners of the detected QR code.
            Each point is expected to have the `point.x` and `point.y` fields. They are expected to be
            in units of pixels.
        :param image_height: The height of the image in pixels.
        :param image_width: The width of the image in pixels.
        :returns: A list containing floats. Each float is the angular diameter of a side of the QR code.
        """
        # Instead of doing lots of error-prone trigonometric trickery, we simply imagine that the image
        # is projected on a screen 1 unit away. Since we know the locations of the points in the image,
        # we can construct vectors from the origin to these points. Then, we use the vector cosine
        # similarity formula to determine the angular diameter.
        virtual_distance = 1  # The distance between the origin and our imagined screen
        virtual_width = 2 * math.tan(self.horizontal_fov / (2 * virtual_distance))  # The width of the screen
        virtual_height = virtual_width * image_height / image_width  # The height of the screen
        # Notice that the screen may scale to the size required, but the aspect ratio does not change.

        centered_points = [
            Point(p.x - (image_width / 2), p.y - (image_height / 2))
            for p in hull
        ]
        # Our math assumes that the center of the screen is at (x, y) = (0, 0). Since computer image origins are in
        # the upper left, we have to shift the points.

        virtual_points = [
            Point(p.x * virtual_width / image_width, p.y * virtual_height / image_height)
            for p in centered_points
        ]
        # We project the points from the image to the screen

        return [[
            math.acos(cos_between_vectors(
                v1=np.array((p1.x, p1.y, virtual_distance)),
                v2=np.array((p2.x, p2.y, virtual_distance))
            ))
            for p1, p2 in self.pairs(virtual_points)
        ]]
        # Finally, we apply the cosine similarity formula to arrive at the list of angles

    @staticmethod
    def estimate_rotation(hull: Iterable[Iterable[int]]):
        """Estimate the rotation of the drone relative to the target.

        This is a heuristic based on the angle of a diagonal.
        This does not find the true angle, only an approximation.

        :param hull: An sequence of points. These points are the corners of the detected QR code.
            They are expected to be in units of pixels.
        :returns: An angle in radians. Positive angles indicate that the drone has to yaw left to
            align itself, negative angles indicate that the drone has to yaw right. Zero indicates
            that the drone's rotation is aligned with the target."""
        hull = np.array(hull)
        diagonal = hull[2] - hull[0]
        expected_angle = math.pi * 0.25
        actual_angle = math.atan2(diagonal[1], diagonal[0])
        delta = expected_angle - actual_angle
        # Make sure delta is in the range (-pi, pi)
        if abs(delta) > math.pi:
            delta -= math.copysign(2 * math.pi, delta)
        return delta

    def estimate_displacement(
            self,
            hull_angles: Iterable[Iterable[float]],
            level: str = '0'):
        """Calculate the displacement vector from the target to the camera.

        Retrieve a hull from the Recognizer.recognize(...).points attribute.

        If you have a hull, use the get_hull_angles method to get the hull angles.

        Note that this calculation results in an angle in target-space. You
        cannot use this vector directly for controlling the drone, since the
        drone controller operates in drone-space, not target-space. Use the
        target_to_drone_space method to transform the vector to drone-space.

        :param hull_angles: An iterable of four angles in radians. These should be the angular diameters
            of each side of the QR code.
        :param level: A string containing the level of the QR code. This is used to choose which regressor
            to use, as each size of code requires a different regressor.
        :returns: A 3-vector of x, y, z coordinates of the drone relative to the target, i.e. in target-space."""
        regressor = self._regressor
        level_factor = self.levels.get(level)

        result: Optional[np.ndarray]
        if level_factor:
            result = np.multiply(level_factor, np.reshape(regressor.predict(hull_angles), (3,)))
        else:
            result = None  # Unknown QR code, we have no idea what size it is
        return result

    @staticmethod
    def target_to_drone_space(
            vector: Sequence[float],
            rotation: float):
        """Transform a vector in target-space to a displacement in drone-space.
        
        This transformation rotates the input vector about the z-axis by the angle specified.
        Currently, the best way to get the rotation angle is the estimate_rotation method.

        :param vector: A 3-vector containing x, y, z coordinates in target-space.
        :param rotation: A scalar rotation value in radians. The z-rotation of the drone relative to the target.
        :returns: The same vector transformed from target-space to drone-space."""

        # Rotation about the z axis
        transform_matrix = np.array([
            [math.cos(rotation), -math.sin(rotation), 0],
            [math.sin(rotation),  math.cos(rotation), 0],
            [0,                   0,                  1]
        ])
        return np.dot(vector, transform_matrix)

    @staticmethod
    def pairs(lst: Sequence):
        """Return pairs of items in the list in a specific order

        The first four elements of the result are the adjacent pairs
        of the list. The fifth is a diagonal pair of the first and third
        elements of the input list. This is sufficient information to
        characterize a quadrilateral by its line lengths.

        >>> pairs([1, 2, 3, 4])
        [(1, 2), (2, 3), (3, 4), (4, 1), (1, 3)]
        >>> pairs([15, 22, 13, 6])
        [(15, 22), (22, 13), (13, 6), (6, 15), (15, 13)]
        """
        return [
            (lst[0], lst[1]),
            (lst[1], lst[2]),
            (lst[2], lst[3]),
            (lst[3], lst[0]),
            (lst[0], lst[2])
        ]
