from typing import Iterable, Sequence

import matplotlib.pyplot as plt
import shapely.geometry as geometry

from camera_input import CameraInput
from point_sorter import PointSorter
from pyzbar79.pyzbar.pyzbar import Decoded


class SimplePosition:
    """The Simple_Position class receives input from the camera after being processed by zbar.

    It uses the four points on the corners of the QR code (returned by zbar) to estimate
    the size (as a percentage of the screen space) and the position offset (using the centroid
    of the quadrilateral formed by those points) to estimate how much course correction should be made.
    variance of position is given by the x,y offset (in pixels) and the scale (as a percent of the frame)
    that the QR code fills.

    This class is not fully-featured enough to use for guidance of the drone. It would need to add the drone
    tilt angles as inputs to become useful for that.

    The class is used to determine when the drone is close enough to the landing target and is sufficiently
    centered to land. This class in part determines whether the drone will continue to hover or finalize
    the landing sequence.

    When initialized, must input the camera resolution and the camera object.
    """
    def __init__(self, horizontal_resolution, vertical_resolution, camera: CameraInput):
        """
        :param horizontal_resolution: The image's width in pixels
        :param vertical_resolution: The image's height in pixels
        :param camera: The camera from which to retrieve images
        """
        self.camera = camera
        self.vertical_res = vertical_resolution
        self.horizontal_res = horizontal_resolution
        self.center_x = self.horizontal_res / 2
        self.center_y = self.vertical_res / 2
        screen_line = [
            [0, 0],
            [self.horizontal_res, 0],
            [self.vertical_res, self.horizontal_res],
            [0, self.vertical_res]
        ]
        self.screen = geometry.Polygon(screen_line)
        self.pointSorter = PointSorter()
        self.shapes = [None, None, None]

    async def update_state(self, qrcodes: Iterable[Decoded]):
        """Update the object with new QR data

        :param qrcodes: A list of decoded QR objects"""
        for qrcode in qrcodes:
            contents = qrcode.data.split(b',', 2)
            layer = contents[1]
            layer = int(layer)
            if 0 <= layer <= 2:
                shape = self.generate_shape(qrcode.points)
                self.shapes[layer] = shape

    def get_scale_and_offset(self, targetLayer: int):
        """
        This function is the main function that is used in this class. It receives input from the camera
        and processes that input to return the x,y offset and scale (percent) of the qr code recognized.
        Note that it inputs a target layer (0,1,2) and returns the data about that layer if present.
        If the layer is not present, instead returns None, None, None.

        Future work might consider refactoring this function to instead take a collection of points
        as input. Currently, this function duplicates some work as it leads to the camera frame
        being retrieved and analyzed twice.
        """
        if self.shapes[targetLayer] is not None:
            shape = self.shapes[targetLayer]
            center = self.calc_center(shape)
            x_offset, y_offset = self.calc_offset(center)
            scale = self.calc_scale(shape)
            return x_offset, y_offset, scale
        return None, None, None

    def calc_offset(self, point):
        """
        Computes the x,y offset of the qr code in the frame,
        using the x,y center points of the frame as a basis.
        """
        x_coord = point.x
        y_coord = point.y
        x_offset = x_coord - self.center_x
        y_offset = y_coord - self.center_y
        return x_offset, y_offset

    def calc_scale(self, hull):
        """
        Computes the percent of the camera frame filled by the qr code shape.
        """
        shape_area = hull.area
        screen_area = self.screen.area
        ratio = shape_area / screen_area
        return ratio

    @staticmethod
    def valid_hull(hull: Sequence[Sequence]):
        """
        This function is used to filter out shape collections that might be
        returned by zbar that cannot correspond to a qr code. Returns true
        if the input is a four-element iterable with two-element iterables
        inside.
        """
        if len(hull) != 4:
            return False
        for each in hull:
            if len(each) < 2:
                return False
        return True

    def calc_center(self, hull):
        """
        This function is used by the get_scale_and_offset function.
        It returns the centroid of a shapely shape object.
        """
        return hull.centroid

    def generate_shape(self, pointarray):
        """
        This function creates a shapely shape object from a valid collection
        of points. Shapely shapes contain a good amount of metadata which
        makes it easier to calculate things like their center positions
        and size (area).
        """
        is_valid = self.valid_hull(pointarray)
        if is_valid:
            sorted_points = self.pointSorter.sort_points(pointarray)
            quad = geometry.Polygon(sorted_points)
            if quad.is_valid:
                return quad
            else:
                print('Unable to sort a valid Polygon')
                return None
        else:
            return None

    def display_graph(self, hull, center):
        """This is a debugging function used to visualize shapely shapes and point arrays.
        input the hull and the estimated center point to graph."""
        x, y = hull.exterior.xy
        fig, axes = plt.subplots()
        axes.plot(x, y)
        cx = center.x
        cy = center.y
        axes.scatter(cx, cy)
        axes.scatter(self.center_x, self.center_y, edgecolors="RED")
        plt.xlim(0, self.horizontal_res)
        plt.ylim(0, self.vertical_res)
        plt.show()
