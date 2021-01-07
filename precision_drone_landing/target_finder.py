"""The body of the program. Seeks the target."""
import asyncio
from functools import partial
from numbers import Real
from typing import List

import numpy as np

from camera_input import CameraInput
from config import HORIZONTAL_FIELD_OF_VIEW, TAKEOFF_HEIGHT, MAX_FRAMES_PER_SECOND, QR_SIZES
from displacement_estimator import DisplacementEstimator
from drone_control import DroneControl
from preview_output import PreviewOutput
from pyzbar79.pyzbar.pyzbar import Decoded
from recognizer import Recognizer
from target_handler import LandingZone, TargetHandler
from simple_guidance import SimplePosition
import concurrent.futures


class TargetFinder:
    """TargetFinder calls all other modules and passes data between them."""
    def __init__(self):
        self.recognizer = Recognizer()
        self.handler = TargetHandler()
        self.camera_input = CameraInput()
        self.preview_output = PreviewOutput()
        self.displacement_estimator = DisplacementEstimator()
        self.horizontal_field_of_view = HORIZONTAL_FIELD_OF_VIEW
        self.drone_control = DroneControl(self.handler)
        self.drone_control.startup_simulation(TAKEOFF_HEIGHT, MAX_FRAMES_PER_SECOND)
        self.simple_guidance = None

    async def loop_body(self):
        """
        The main loop body of the program.
        This function handles the routing between all of the different modules.
        It also enables multi-threading, which allows for some heavy functions
        (such as image processing) to be offloaded onto different threads.
        """
        loop = asyncio.get_running_loop()
        with concurrent.futures.ThreadPoolExecutor() as pool:
            frame = await loop.run_in_executor(pool, self.camera_input.get_frame)
            if frame is None:
                return
            width, height, _ = frame.shape
            if not self.simple_guidance:
                self.simple_guidance = SimplePosition(width, height, self.camera_input)
            self.drone_control.init_simple_position(self.simple_guidance)
            self.preview_output.set_image(frame)
            qr_codes: List[Decoded] = await loop.run_in_executor(pool, partial(self.recognizer.recognize, image=frame))
            await self.simple_guidance.update_state(qr_codes)
            self.preview_output.set_qr_data(qr_codes)
            hull_angle_coroutines = [
                loop.run_in_executor(
                    None,
                    partial(
                        self.displacement_estimator.get_hull_angles,
                        hull=qr_code.points,
                        image_height=height,
                        image_width=width
                    )
                )
                for qr_code in qr_codes
            ]
            hull_angles_list = await asyncio.gather(*hull_angle_coroutines)
            displacement_estimate_coroutines = [
                loop.run_in_executor(
                    pool,
                    partial(
                        self.displacement_estimator.estimate_displacement,
                        hull_angles=hull_angles,
                        level=qr_code.data.decode('utf-8').split(',')[-1]
                    )
                )
                for hull_angles, qr_code in zip(hull_angles_list, qr_codes)
            ]
            displacement_estimates = await asyncio.gather(*displacement_estimate_coroutines)
            targets = [None, None, None]
            if displacement_estimates:
                rotation_estimate = self.displacement_estimator.estimate_rotation(qr_codes[0].points)
                average_displacement = np.mean(displacement_estimates, axis=0)
                self.preview_output.set_estimated_distance(average_displacement)
                for code, displacement in zip(qr_codes, displacement_estimates):
                    drone_space_displacement = self.displacement_estimator.target_to_drone_space(
                        vector=displacement,
                        rotation=rotation_estimate
                    )
                    target = self.process_code(code.data, *drone_space_displacement)
                    if target is not None:
                        properties = target.getLayer()
                        targets[properties] = target
            else:
                rotation_estimate = 0
                print('No codes found')
                self.preview_output.set_estimated_distance(np.zeros(3))
            self.handler.update(targets)
            self.preview_output.set_estimated_rotation(rotation_estimate)
            self.preview_output.prepare_output()
            self.preview_output.display_image()
            await self.drone_control.update_velocity()

    @staticmethod
    def process_code(
            data: bytes,
            X: Real,
            Y: Real,
            Z: Real):
        """
        This function takes input from the zbar and distance estimation algorithms.
        It creates a new LandingZone object that contains the position estimation data,
        enumerates the layer the code comes from, and stores the contents of the
        code message.
        """
        try:
            code, layer = data.split(b',', 2)
            code = code.decode('utf-8')
            layer = layer.decode('utf-8')
        except IndexError:
            return None

        if layer in QR_SIZES.keys():
            return LandingZone(int(layer), code, X, Y, Z)
        return None
