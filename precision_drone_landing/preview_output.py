from numbers import Real
from typing import Iterable, Sequence, List

import cv2
import numpy as np

from pyzbar79.pyzbar.pyzbar import Decoded
from util import adjacent_pairs, calc_center


class PreviewOutput:
    """Display the drone's downwards camera for debugging purposes.

    Only operates in simulation, since the drone itself is headless."""

    def __init__(self):
        self.image = None
        self.output = None
        self.qr_data: List[Decoded] = []
        self.estimated_distance = np.zeros(3)
        self.estimated_rotation = 0

    def display_image(self, window_title: str = 'Drone Camera'):
        """Display the image in a window.

        MUST BE RUN ON THE MAIN THREAD.
        Run prepare_output() before this function to renew the overlay information."""
        cv2.imshow(window_title, self.output)
        cv2.waitKey(1)

    def set_image(self, image: np.ndarray):
        """Set the current image."""
        self.image = image

    def set_qr_data(self, qr_data: Sequence[Decoded]):
        """Set the current QR data."""
        self.qr_data = qr_data

    def set_estimated_distance(self, estimated_distance: Sequence[Real]):
        """Set the current estimated distance."""
        if len(estimated_distance) == 3:
            self.estimated_distance = estimated_distance
        else:
            self.estimated_distance = np.zeros(3)

    def set_estimated_rotation(self, estimated_rotation: Real):
        """Set the current estimated rotation."""
        self.estimated_rotation = estimated_rotation

    def prepare_output(self):
        """Write the overlay information to the output image."""
        self.output = np.copy(self.image)
        self._highlight_qr_codes()
        self._write_overlay_info()

    def _highlight_qr_codes(self):
        """Draw lines around each QR code."""
        for code in self.qr_data:
            # Draw a line around the QR code hull
            for p1, p2 in adjacent_pairs(code.points):
                cv2.line(self.output, p1, p2, (255, 0, 0))

            # Draw a point in the apparent center of the code
            center = calc_center(code.points)
            cv2.circle(self.output, (int(center.x), int(center.y)), 3, (255, 0, 0))

            # Label each vertex in the hull with a number.
            # If pyzbar returns consistent orderings, these should
            # never appear to change.
            for index, point in enumerate(code.points, start=1):
                cv2.putText(
                    img=self.output,
                    text=str(index),
                    org=point,
                    fontFace=cv2.FONT_HERSHEY_SIMPLEX,
                    color=(0, 0, 255),
                    fontScale=0.5
                )

    def _write_overlay_info(self):
        """Write the estimated position and rotation on the screen."""
        cv2.putText(
            img=self.output,
            text=f'X: {float(self.estimated_distance[0]):6.2f} m',
            org=(25, 25),
            fontFace=cv2.FONT_HERSHEY_SIMPLEX,
            color=(0, 0, 255),
            fontScale=0.5
        )
        cv2.putText(
            img=self.output,
            text=f'Y: {float(self.estimated_distance[1]):6.2f} m',
            org=(25, 50),
            fontFace=cv2.FONT_HERSHEY_SIMPLEX,
            color=(0, 0, 255),
            fontScale=0.5
        )
        cv2.putText(
            img=self.output,
            text=f'Z: {float(self.estimated_distance[2]):6.2f} m',
            org=(25, 75),
            fontFace=cv2.FONT_HERSHEY_SIMPLEX,
            color=(0, 0, 255),
            fontScale=0.5
        )
        cv2.putText(
            img=self.output,
            text=f'Rotation: {float(self.estimated_rotation):6.2f} rad',
            org=(25, 100),
            fontFace=cv2.FONT_HERSHEY_SIMPLEX,
            color=(0, 0, 255),
            fontScale=0.5
        )

if __name__ == '__main__':
    import camera_input as cam
    camera = cam.CameraInput()
    display = PreviewOutput()
    while True:
        frame = camera.get_frame()
        display.set_image(frame)
        display.output = display.image
        display.display_image()