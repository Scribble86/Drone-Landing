# Running the Deployment Environment

This guide assumes that you have followed [Setting up the software on the Raspberry Pi](deployment_setup.md).

The software is currently configured to run using a simulated drone on the local machine. This is possible using the
Raspberry Pi 4, but is not the recommended simulation environment. To reconfigure for use on a physical drone, first
open the `precision_drone_landing/config.py` file and edit line 24 to comment out the ip address and uncomment the device
reference. This is for use when attached via usb. When attached via serial connection, use `/dev/ttyAMA0` instead. Once
you have pointed the software package to connect to the drone in the correct location, open the
`precision_drone_landing/target_finder.py` file and follow the instructions on line 27-28 by commenting out lines 13, 29,
52, 55, 85, 99, and 101-103. This will improve performance by avoiding rendering the camera view on the screen.

To launch our software, use the following command from the root project folder:

```bash
source venv/bin/activate
python3 precision_drone_landing/__main__.py
```
