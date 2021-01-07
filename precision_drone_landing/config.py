"""A module containing configuration constants."""
import json
import os

"""
This configuration file contains many global variables for this software package.
Important options follow.
The MAX_FRAMES_PER_SECOND variable which sets a limit for the number of updates
the software provides per second.
The HORIZONTAL_FIELD_OF_VIEW setting is an input for the distance estimation
regressor and adjusts position estimates accordingly. This should be set to match
the FOV of the camera that is being used.
The ARDUPILOT_CONNECTION setting connects to the drone. Note that the current default
IP address is set. This connection method may need to be updated when this software
is installed in a drone.
"""
import json
import os

MAX_FRAMES_PER_SECOND = float(os.environ.get('MAX_FRAMES_PER_SECOND') or 15)
SECONDS_PER_FRAME = 1 / MAX_FRAMES_PER_SECOND
HORIZONTAL_FIELD_OF_VIEW = float(os.environ.get('HORIZONTAL_FIELD_OF_VIEW') or 85)  # degrees
TAKEOFF_HEIGHT = float(os.environ.get('TAKEOFF_HEIGHT') or 10)  # meters
ARDUPILOT_CONNECTION: str = os.environ.get('ARDUPILOT_CONNECTION') or '127.0.0.1:14551'  #'/dev/ttyACM0' #USBI
with open('qr_sizes.json', 'r') as qr_sizes_file:
    QR_SIZES = json.load(qr_sizes_file)
