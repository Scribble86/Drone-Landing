from typing import Optional

import airsim
import numpy as np


class CameraInput:
    """
    This class is tied to our virtual simulation environment. It gets the drone
    view perspective from the Unreal Engine via Airsim and then converts it to
    the format that OpenCV requires for processing.
    """
    def __init__(self):
        self._drone = airsim.MultirotorClient()

    def get_frame(self) -> Optional[np.ndarray]:
        """Retrieves a single frame from the drone's camera in simulation.

        Each call to this function will return the newest frame. Thus, if this
        function is called slower than the camera's frame rate, some frames
        will not be returned. If it is called faster, the function may return the same frame multiple times.

        :returns: The frame as a numpy array of shape (height, width, 3). The innermost dimension is the RGB values.
            If the drone does not have a valid frame, returns None instead."""
        images = self._drone.simGetImages(
            [airsim.ImageRequest("bottom_center", airsim.ImageType.Scene, False, False)]
        )
        frame = images[0]
        img1d = np.fromstring(frame.image_data_uint8, dtype=np.uint8)
        if frame.width < 1 or frame.height < 1:
            return None
        img_rgb = img1d.reshape([frame.height, frame.width, 3])
        frame = np.array(img_rgb)
        return frame
