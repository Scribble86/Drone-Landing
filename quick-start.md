# Quick Start: Precision Drone Landing

This guide gathers the project overview, dependencies, and setup steps into one page. The detailed guides are
still in [`docs/`](docs/). Where this page and those guides disagree, the "Gotchas" section below explains why.

## What it does

Precision Drone Landing is a Python program that lands a multirotor drone on a printed QR-code landing pad without a
human pilot. It reads frames from a downward-facing camera, estimates where the pad is relative to the drone, and sends
velocity commands to an ArduPilot flight controller over MAVLink until the drone is centered and low enough to land.

### The landing target

The pad is made of **three nested QR codes** (outer, middle and inner). Each code contains `<id>,<level>`, for example
`test,0`, `test,1` and `test,2`. The physical size of each level is listed in
[`config/qr_sizes.json`](config/qr_sizes.json). The outer code is 1 m, not counting its quiet zone. With nested codes the
drone can still see a whole code at every altitude: the outer code from high up, the inner one just before touchdown.

### Pipeline (one pass per frame, capped at `MAX_FRAMES_PER_SECOND`)

| Step | Module | What it does |
|---|---|---|
| Main loop | `precision_drone_landing/__main__.py` | An asyncio loop that calls `TargetFinder.loop_body()` once per frame |
| Camera | `camera_input.py` | Gets the `bottom_center` camera image from AirSim (simulation only) |
| QR detection | `recognizer.py` + `pyzbar79/` | Decodes QR codes with a vendored, patched PyZBar that keeps the corner order stable when a code rotates |
| Displacement | `displacement_estimator.py` | Turns the angles between corners into features and runs a pickled scikit-learn `MLPRegressor` (`assets/displacement_detection_models/regressor.pkl`) to estimate the X/Y/Z offset. It then rotates that offset into the drone's frame |
| Target tracking | `target_handler.py` | Holds the latest `LandingZone` for each level (thread-safe) |
| Screen-space check | `simple_guidance.py`, `point_sorter.py` | Uses Shapely polygons to measure how centered the pad is and how much of the frame it fills. This decides whether it is safe to land |
| Flight control | `drone_control.py`, `controller.py` | Averages recent estimates with more weight on newer ones (3 s window). Runs X/Y/Z PID controllers (`simple_pid`) and sends NED velocity commands through DroneKit/pymavlink. If the pad is lost it flies in a circle to search. It lands and disarms when centered |
| Preview | `preview_output.py` | An OpenCV window that shows detected codes, the estimated distance and the rotation |
| Logging | `log.py` | Writes `Drone_Control_Log.csv` and `Position_Estimate_Averages.csv` to the current directory |

### Flight sequence (simulation mode)

1. Connect to ArduPilot and wait until the vehicle is armable.
2. Switch to GUIDED, arm, and take off to `TAKEOFF_HEIGHT` (default 10 m). Then switch to RTL.
3. When the program sees RTL mode it takes control: GUIDED mode, hold position for 3 s to fill the estimate buffer, then
   track the pad.
4. Descend while tracking. Descent pauses until the drone is centered, then slows down for the final approach (inner
   code seen in more than 3 recent frames).
5. Land and disarm. The process exits with code `0` on success, or `1` if the miss limit was exceeded (safety abort).

### Supporting scripts

- `scripts/qr_generator.py`: generates the nested 3-level landing pad as a 4096×4096 PNG.
- `scripts/generate_displacement_model.py`: generates synthetic training data and trains the MLP regressor. This takes
  hours.

## Dependencies

### Runtime (Python, `requirements.txt`)

| Package | Purpose |
|---|---|
| `pymavlink`, `dronekit` | MAVLink link to ArduPilot / the flight controller |
| `airsim` | Camera frames from the Unreal Engine simulator |
| `scikit-learn==0.22.2.post1`, `numpy` | Loads and runs the pickled displacement regressor. The pin must match the version the pickle was built with |
| `opencv-python` | Preview window and image handling |
| `shapely` | Polygon and geometry maths |
| `simple_pid` | PID controllers |
| `Pillow` | Image support |

**Missing from `requirements.txt`, but the code needs them:**

- `matplotlib`: imported at module level by `simple_guidance.py`, so the program won't start without it.
- `qrcode`: needed by `scripts/qr_generator.py`.

### Model generation (`requirements_gen_model.txt`)

`scikit-learn`, `numpy`, `vg`

### Testing (`requirements-testing.txt`)

`pytest`, `coverage`

### System packages (`install-deps-ubuntu.sh`, must run as root)

`python3`, `python3-pip`, `python3-dev`, `python3-venv`, `python3-tk`, `gcc`, `libxml2-dev`, `libxslt-dev`, `libgeos-dev`
(for Shapely), `libzbar0` (for PyZBar).

### External tools

**For simulation (development):**

- **Unreal Engine 4**: the flight simulator. Needs 100 GB or more of disk and a discrete GPU (a GTX 1060 or better is
  known to work; integrated graphics are not enough).
- **Microsoft AirSim**: connects Unreal to the program. Use the "Blocks" environment and the settings in
  [`config/airsim_settings.json`](config/airsim_settings.json).
- **ArduPilot SITL**: takes the place of the PixHawk flight controller.

**For deployment:** a Raspberry Pi 4, OpenCV built from source, and a flight controller connected over USB or serial.

## Development setup (software-in-the-loop on Ubuntu)

Full guide: [docs/dev_environment_setup.md](docs/dev_environment_setup.md).

```bash
# 1. Install Unreal Engine 4, AirSim, and ArduPilot (see the links in docs/dev_environment_setup.md)

# 2. Copy the AirSim settings into place
cp config/airsim_settings.json ~/Documents/AirSim/settings.json

# 3. Install the project
git clone https://github.com/Scribble86/Drone-Landing.git
cd Drone-Landing
sudo sh install-deps-ubuntu.sh
python3 -m venv venv            # Python 3.8 is recommended, because scikit-learn 0.22 has no wheels for newer Pythons
source venv/bin/activate
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
pip install matplotlib qrcode   # missing from requirements.txt
pip install -r requirements-testing.txt   # optional
```

### Make a landing pad

Run this from the repository root:

```bash
python scripts/qr_generator.py 'test,0' 'test,1' 'test,2' -p test_qr_code.png
```

A ready-made pad is also at [`docs/test_qr_code.png`](docs/test_qr_code.png). To place it in the Unreal Blocks map:

1. Import the PNG as a texture and set **Mip Gen Settings** to **NoMipmaps**.
2. Apply the texture to a Plane near the player start.
3. Scale the Plane by `(25 + 2*2)/25 = 29/25` so the quiet zone is included.

### Run a simulation

Start the three parts in this order:

```bash
# 1. Unreal Editor → open AirSim/Unreal/Environments/Blocks → press "Play" (the editor will appear to freeze; this is expected)
UnrealEngine/Engine/Binaries/Linux/UE4Editor

# 2. ArduPilot SITL (from the ardupilot checkout)
python3 Tools/autotest/sim_vehicle.py -v ArduCopter -f airsim-copter --console

# 3. This software. Run it from inside the package directory (see Gotchas)
cd precision_drone_landing
python __main__.py
```

When a run ends, stop Unreal first. ArduPilot and this program must be restarted for every run.

### Configuration (environment variables, see `precision_drone_landing/config.py`)

| Variable | Default | Meaning |
|---|---|---|
| `MAX_FRAMES_PER_SECOND` | `15` | Upper limit on the processing rate |
| `HORIZONTAL_FIELD_OF_VIEW` | `85` | Camera horizontal FOV in degrees |
| `TAKEOFF_HEIGHT` | `10` | Takeoff altitude in metres (simulation mode) |
| `ARDUPILOT_CONNECTION` | `tcp:127.0.0.1:5762` | DroneKit connection string, for example `/dev/ttyACM0` (USB) or `/dev/ttyAMA0` (serial) |

### Tests and CI

`.gitlab-ci.yml` installs dependencies and runs `coverage run -m pytest tests/`. However, `tests/` is listed in
`.gitignore` and is not in the repository, so the CI job has nothing to run.

### Retraining the displacement model

```bash
pip install -r requirements_gen_model.txt
cd scripts                      # the script writes to ../assets/…, so run it from here
python generate_displacement_model.py [-e existing_regressor.pkl]
```

Pickles only work on the CPU architecture that created them. `master` holds the x86 pickle and `aarch` holds the
Raspberry Pi pickle.

## Deployment setup (Raspberry Pi 4 on a real drone)

Full guides: [docs/deployment_setup.md](docs/deployment_setup.md) and
[docs/deployment_running.md](docs/deployment_running.md).

1. Use the **`aarch`** branch. It has the Pi camera input, no preview window, and an ARM-built regressor pickle. See
   [docs/branch_information.md](docs/branch_information.md).
2. Install `build-essential`, `cmake`, and the SSL, readline and other build libraries. Then build **Python 3.8.5** (or
   3.9) from source with `--enable-optimizations`.
3. Install `numpy`, `scikit-learn`, and the lxml prerequisites (`libxslt1-dev`, `libxml2`, …).
4. Build and install **OpenCV from source**, because there is no pip wheel for ARM. The Pi that was delivered already
   has a build: run `sudo make -j4 install` in `opencv/build`.
5. Run `sudo sh install-deps-ubuntu.sh`, then `pip3 install -r requirements.txt` (plus `matplotlib`).
6. Generate the displacement model on the Pi (this takes a long time) and keep it at
   `assets/displacement_detection_models/regressor.pkl`.
7. Set `ARDUPILOT_CONNECTION` to the flight controller device. Use `/dev/ttyACM0`-style devices for USB and
   `/dev/ttyAMA0` for serial.
8. For better performance, turn off the OpenCV preview. The docs refer to specific line numbers in `target_finder.py`
   that may no longer be accurate, so remove the `PreviewOutput` calls instead.
9. Run it from the package directory: `cd precision_drone_landing && python3 __main__.py`.
10. Once it works, save an image of the SD card so you don't have to repeat this setup.

On a real drone, `DroneControl.startup()` (which does no takeoff) is meant to replace `startup_simulation()`. When the
pilot switches the drone to RTL, the program takes control and lands it.

## Gotchas found during review

- **Run from `precision_drone_landing/`.** `config.py` and `displacement_estimator.py` open `../config/...` and
  `../assets/...` relative to the *current working directory*. The command in `docs/deployment_running.md` is
  `python3 precision_drone_landing/__main__.py` from the repo root, and it fails with `FileNotFoundError`. For the same
  reason, `scripts/generate_displacement_model.py` must be run from `scripts/`, not from the root as
  `docs/generate_displacement_model.md` says.
- **The `HORIZONTAL_FIELD_OF_VIEW` setting is never used.** `TargetFinder` builds `DisplacementEstimator()` without
  passing the FOV, so the estimator always uses its default of 60°. The AirSim camera and the config are both set to 85°.
- **Undeclared dependencies:** `matplotlib` for runtime and `qrcode` for the QR script.
- **The scikit-learn pin (0.22.2.post1)** only has wheels for older Python versions (3.8 or earlier). The pickle must be
  loaded with the same scikit-learn version that created it.
- **The CI test directory is gitignored** (`tests/*`), so the GitLab pipeline has no tests to run.
- **The docs are out of date in places.** They point to GitLab URLs, have a placeholder `$REPOSITORY`, contain a `fixme`
  link, and refer to line numbers in `config.py` and `target_finder.py` that don't match the current code.
- **Safety:** simulation mode turns off the GPS (`AHRS_GPS_USE=0`) and the throttle failsafe (`FS_THR_ENABLE=0`). Check
  these settings before any real flight.
- **Known technical debt** is listed in [docs/technical_debt.md](docs/technical_debt.md): the vendored PyZBar fork, the
  choice of QR library, and the model pickle committed to git.
