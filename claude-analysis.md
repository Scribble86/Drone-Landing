# Code Analysis: Bugs, Optimization Targets, and Improvements

This review of `precision_drone_landing/` and `scripts/` goes further than the "Gotchas" section of
[quick-start.md](quick-start.md). Every finding points to a file and line. Findings marked **(verified)** were
reproduced by running the code in isolation. The rest come from reading the code and are marked with how confident I am.

Severity levels:

- **Critical**: can cause a crash in flight, a landing in the wrong place, or unsafe vehicle behaviour.
- **High**: consistently wrong results.
- **Medium**: wrong in edge cases.
- **Low**: cosmetic or latent.

---

## 1. Bugs

### 1.1 Critical

#### B1. Width and height are swapped for every frame
`target_finder.py:46`: `width, height, _ = frame.shape`

`CameraInput.get_frame()` returns an array of shape `(height, width, 3)` (`camera_input.py:32`), so the two values are
swapped. With the 1280×1024 camera in `config/airsim_settings.json`, this causes:
- `get_hull_angles(image_height=height, image_width=width)` centers the points on (512, 640) instead of (640, 512).
  Every displacement estimate is therefore offset by about 128 px on each axis, and the x/y pixel-to-angle scaling is
  off by 1.25×.
- `SimplePosition(width, height, ...)` has its "frame center" in the same wrong place. `should_land()` then treats the
  pad as centered when it is actually about 128 px off-center.

**Fix:** `height, width, _ = frame.shape`.

#### B2. `PointSorter` reorders the QR corner list in place, which undoes the PyZBar patch
`point_sorter.py:39` and `simple_guidance.py:60` **(verified)**

`sort_points()` sorts the list it is given in place and returns the same object. `SimplePosition.update_state()` passes
it `qrcode.points` directly, and this runs *before* the displacement and rotation estimates in `target_finder.py`. As a
result:
- The corner order that the vendored `pyzbar79` fork exists to keep stable (see `docs/technical_debt.md`) is replaced by
  an order based on angle from the top-most point.
- `estimate_rotation()` uses `points[0]` and `points[2]`, so it can only return values in a limited range and does not
  track the pad's real rotation.
- The edge order fed to the regressor changes from frame to frame as the drone rotates. The preview's corner labels
  change too, so the visual check described in the technical-debt doc cannot catch the problem.

**Fix:** sort a copy (`sorted_points = self._insertion_sort(p0, list(points))`). The sort may not be needed at all,
because zbar already returns the corners in order around the quadrilateral.

#### B3. Any unexpected QR code crashes the program
- `target_finder.py:116-120` **(verified)**: `code, layer = data.split(b',', 2)` raises `ValueError` both when there is
  no comma (`b'hello'`) and when there is more than one (`b'a,b,0'`). The handler only catches `IndexError`.
- `simple_guidance.py:55-57`: `contents[1]` raises `IndexError` and `int(layer)` raises `ValueError` for the same kinds
  of input. This runs earlier in the frame than `process_code`.
- `target_finder.py:73` and `displacement_estimator.py:148-151`: an unknown level makes `estimate_displacement` return
  `None`. `np.mean(displacement_estimates)` and `target_to_drone_space(None)` then fail on line 82 and the lines after.
- `qr_code.data.decode('utf-8')` raises on bytes that are not valid UTF-8.

Any QR code in view that isn't part of the pad (a poster, a package label, or a pad with a typo) kills the control loop
in mid-air.

**Fix:** write one `parse_code(data) -> Optional[(code, level)]` function that validates with the documented regex
`^.{,4},[012]$`, use it everywhere, and drop codes that don't match before any other processing.

#### B4. Velocity commands are sent in the world frame, but they are computed in the camera frame
`drone_control.py:500`: `MAV_FRAME_LOCAL_NED`

The X/Y errors come from the camera image, which is fixed to the drone's body. They are sent as North/East velocities.
This only works when the drone is pointing north, which happens to be the SITL default. With any other heading, the
corrections point the wrong way and the drone spirals or drifts away. The rotation estimate (see B2) and
`condition_yaw()` (line 509) are never used to correct for this.

**Fix:** use `MAV_FRAME_BODY_NED` (or `MAV_FRAME_BODY_OFFSET_NED`), or rotate the vector by `vehicle.heading` before
sending it. The mapping from camera axes to body axes also needs to be written down, because it depends on how the
camera is mounted.

#### B5. Safety-abort landings are reported as successful
`drone_control.py:544` and `drone_control.py:476`

`should_land()` forces a landing when `missCount > 200`. The exit-status check afterwards compares against
`missLimit = 1000` (line 178). Any abort with a `missCount` between 201 and 1000 prints "Successfully Landed!" and exits
with `0`. This makes the simulation accuracy logs unreliable.

**Fix:** use one constant, or record the reason for landing when the decision is made.

#### B6. The `startup()` path for real drones changes flight-controller settings permanently
`drone_control.py:284-297` (and the same code in the simulation path at lines 244-262)

`startup()`:
- sets `vehicle.armed = True` on a real vehicle without any checks
- sets `FS_THR_ENABLE = 0`, which turns off the throttle/RC-loss failsafe
- sets `AHRS_GPS_USE = 0`, which stops using GPS

ArduPilot saves parameters set over MAVLink, so these changes are still in effect after the program exits and after
reboots. The simulation path also sets each of them twice.

**Fix:** don't change failsafe parameters from the landing program. If a parameter change is really needed, save the
original value and restore it in a `finally` block. Don't arm from `startup()`.

### 1.2 High

#### B7. The configured field of view is ignored
`target_finder.py:28`

`DisplacementEstimator()` is created without `fov=`, so it uses its default of 60°. The config and the AirSim camera
are both 85°. Because `tan(42.5°)/tan(30°) ≈ 1.59`, every angle fed to the regressor is too small by about that factor,
and the distance estimates are wrong by a large amount.

**Fix:** `DisplacementEstimator(fov=HORIZONTAL_FIELD_OF_VIEW)`.

#### B8. Old position data is not fully removed
`drone_control.py:145-147` **(verified)**

`_clear_position_data` removes items from the list while looping over it, so the item after each removed one is skipped
and old estimates stay in the buffer. The "3-second window" is longer than intended, which slows the reaction to
movement.

**Fix:** `targets[:] = [t for t in targets if now - t.time <= 3]`, or use a `collections.deque` and remove items from
the left.

#### B9. `SimplePosition.shapes` is never cleared
`simple_guidance.py:54-60`

A layer's shape is replaced only when that layer is seen again. It is never reset to `None`. `should_land()` can
therefore decide to land using an inner-code position and size from any earlier frame. The `finalApproach` check limits
this but does not remove it.

**Fix:** reset `self.shapes = [None, None, None]` at the start of `update_state()`.

#### B10. The screen polygon has the wrong shape
`simple_guidance.py:43`: `[self.vertical_res, self.horizontal_res]` should be
`[self.horizontal_res, self.vertical_res]`.

The "screen" is not a rectangle, so its area is wrong, and so is every `scale` ratio used by the landing checks. A
simpler fix is `screen_area = horizontal_res * vertical_res`.

#### B11. The descent logic can divide by zero
`drone_control.py:540`: `math.atan(a/b)` is evaluated with `b = z_vector` when `z_vector < 1` (line 441). This includes
`0` and negative values.

**Fix:** use `math.atan2(a, b)`.

`drone_control.py:369` has a similar problem: `time.time() % limit` with
`limit = math.ceil(lastHeight)` is `0` if the last height was exactly 0.

#### B12. The drone is disarmed on a fixed 2-second timer after switching to LAND
`drone_control.py:468-471`

`should_land()` fires when the inner code fills 10-20% of the frame, which may still be above the ground. The code calls
the blocking `time.sleep(2)` inside the async loop and then `disarm()`. ArduCopter usually refuses to disarm in flight,
and the result isn't checked. If a forced disarm is ever added, the drone would drop.

**Fix:** let LAND mode disarm automatically on touchdown. Wait for `vehicle.armed == False` or a landed state, with a
timeout, and without blocking the event loop.

### 1.3 Medium

#### B13. About half of the control updates are likely skipped
`drone_control.py:416`

`poll_delay` is exactly the frame period (`1 / MAX_FRAMES_PER_SECOND`). `previousTime` is sampled at a slightly
different point in each frame, so small timing variations make `time_dif < poll_delay` true on many frames. When that
happens, `update_velocity` returns without sending a command, so the effective control rate may be close to half the
configured rate. (Likely, but not measured.)

**Fix:** remove the check, because the main loop already limits the rate, or compare against something like
`0.8 * poll_delay`.

#### B14. `missCount` does not count what its name says
`drone_control.py:113-127`

It is reset to 0 whenever *any* layer is found, and then increased by 1 for each layer that was *not* found in the same
loop. The result depends on the order of the layers: seeing only layer 0 gives 2, while seeing only layer 2 gives 0. It
is also increased again in `circle()` (line 373). The thresholds `> 10` and `> 200` therefore don't correspond to a
clear number of frames or seconds.

**Fix:** count consecutive frames in which no layer was seen, or use elapsed time.

#### B15. The PID controllers are never reset between modes, and circle commands go through the tracking PID
`drone_control.py:453-455`

In Circle mode, `x_vector, y_vector = cos, sin` is multiplied by 3 and fed to the same PIDs as a position error. The
search pattern is therefore negated and filtered, and its integral term carries over into Tracking mode.
`Controller.reset()` exists but is never called.

**Fix:** send search commands directly instead of through the PIDs, and call `reset()` whenever the mode changes.

#### B16. The `-e/--existing_model` option of `generate_displacement_model.py` is broken
`scripts/generate_displacement_model.py:17-22, 128`

`type=argparse.FileType('r')` with `nargs=1` produces a *list* containing a *text-mode* file object. It is then passed
to `open(existing_model, 'rb')`, which raises `TypeError`.

**Fix:** use `type=str` without `nargs`.

The docstring on line 115 also says the function "will run continuously until cancelled", but it trains for one round.
`go` and `_go` (lines 154-176) are multiprocessing helpers that are never called.

#### B17. The inner code's QR version is not fixed, so its printed size depends on its content
`scripts/qr_generator.py` (the `innerQR` call)

The outer and middle codes use `version=2`, but the inner code does not set a version. `config/qr_sizes.json` (0.09513)
is only correct when the inner code comes out as version 1 (21 modules). Longer inner data selects a larger version and
makes that value wrong without any warning. The inner code also uses error correction level `M` instead of `H`, which is
undocumented.

**Fix:** set `version=1` (or 2), and calculate `qr_sizes.json` from the same values the generator uses.

#### B18. The training data doesn't cover the whole camera view
`scripts/generate_displacement_model.py:103`

Horizontal offsets are sampled as `(-2..2) * z / 5`, which covers about ±0.4·z. An 85° camera sees about ±0.92·z. Any
pad in the outer ~55% of the frame is outside the training data, so estimates there are extrapolated. The corner order
used in training (`pairs()`, line 45, starting with the edge from c0 to c3) is also not documented against the order the
runtime uses (`displacement_estimator.pairs`, starting with the edge from p0 to p1). Add a round-trip test to confirm the
two match.

### 1.4 Low

| # | Location | Issue |
|---|---|---|
| B19 | `target_handler.py:49` | `LandingZone.print()` prints the class attributes (`self.Layer`, `self.X`, …), which are always `None`, instead of `_Layer`, `_X`, and so on |
| B20 | `camera_input.py:29` | `np.fromstring` is deprecated. Use `np.frombuffer`. The width/height check happens *after* converting the data, and line 33 makes an unneeded copy |
| B21 | `log.py:10` | Opens the file with mode `'w'` and never flushes it, so each run overwrites the last run's logs, and buffered rows are lost on a crash. `writeline` prints a message instead of raising an error on a column-count mismatch |
| B22 | `drone_control.py:478,481` | `sys.exit()` inside the control coroutine skips cleanup: `vehicle.close()` is never called and the CSV loggers depend on `__del__` |
| B23 | `config.py:16` | `MAX_FRAMES_PER_SECOND=0` causes `ZeroDivisionError` when the module is imported. No config values are validated |
| B24 | `displacement_estimator.py:76` | `2 * tan(fov / (2 * d))` should be `2 * d * tan(fov / 2)`. It gives the same result only because `d = 1` |
| B25 | `displacement_estimator.py:184` | The `pairs` doctest calls a bare `pairs(...)`, which fails under `python -m doctest` |
| B26 | `drone_control.py:509` | `condition_yaw()` is never called. `simple_guidance.display_graph()` is debug-only, but it makes `matplotlib` a required runtime dependency |

---

## 2. Safety concerns (outside the individual bugs above)

1. **Exceptions don't trigger a failsafe.** Any exception in `loop_body`, such as B3, ends the process while the vehicle
   is in GUIDED mode. Wrap the main loop in `try/finally`, and in the `finally` switch to LOITER, LAND, or RTL and close
   the vehicle connection.
2. **Nothing is monitored.** There is no check for a lost MAVLink link, camera timeouts, low battery, or a minimum
   altitude during the search pattern.
3. **The landing checks use pixel thresholds.** The 250/200/150 px limits (`drone_control.py:556-561`) only suit a
   1280×1024 camera. Express them as a fraction of the frame size or as an angle.
4. **Tilt is ignored when estimating position.** The regressor assumes the camera points straight down. At a 0.2 rad
   tilt (the limit used for landing), the error at 10 m is about 2 m. Correct for `vehicle.attitude` roll and pitch
   before estimating, or use a gimbal.
5. **The pickled model is loaded with `pickle.load`.** Anyone who can write to `assets/` can run code on the drone.
   This matters little for a repository you control, but it is a reason to move away from pickle (see I1).

---

## 3. Optimization targets

The frame loop runs one step at a time, and QR decoding is, according to the project's own docs, the most expensive
step.

| # | Where | What | Expected gain |
|---|---|---|---|
| O1 | `recognizer.py` / `pyzbar79/pyzbar/pyzbar.py` | PyZBar decodes the **full-resolution** frame, uses only the first colour channel (`image[:, :, 0]`, which is blue in BGR data), and copies the slice. Convert to grayscale once with `cv2.cvtColor`. When a code has been seen recently, decode only a crop around its last position. At high altitude, decode a downscaled image | The biggest possible win: several times faster per frame |
| O2 | `target_finder.py:42` | A new `ThreadPoolExecutor` is created and shut down **every frame**. Create one in `__init__` and reuse it | Removes the cost of starting threads each frame |
| O3 | `target_finder.py:53-78` | Tiny tasks (hull-angle calculation and a single-sample `predict`) are sent to threads one at a time, and one of them uses the default executor (`None`, line 56). The thread overhead is larger than the work. Compute the angles with NumPy, then call `regressor.predict` **once** on all codes together | Fewer thread hops and one sklearn call per frame |
| O4 | `displacement_estimator.py:80-99` | Uses Shapely `Point` objects for plain arithmetic, in a Python loop. Replace with a single vectorised NumPy expression over an `(N, 2)` array | Minor, but it simplifies the code |
| O5 | `camera_input.py` | Each AirSim request transfers an uncompressed 1280×1024×3 image (about 3.9 MB) over RPC and then copies it. Lower the capture resolution if accuracy allows, and use `frombuffer` without extra copies | Lower latency per frame in simulation |
| O6 | `drone_control.py:145` | Removing old entries from a list is O(n²). Use a `deque` and remove from the left while the oldest entry is stale | Minor |
| O7 | `__main__.py:23`, `target_finder.py:95` | Prints every frame. On a Pi's serial console this measurably slows the loop. Use `logging` with levels | Minor |
| O8 | `preview_output.py:52` | `np.copy` of the full frame, plus the overlay drawing, runs even when there is no display. Put the preview behind a `HEADLESS` config flag instead of editing code (see I3) | Worthwhile on the Pi |
| O9 | `scripts/generate_displacement_model.py:102-108` | Generates 1 million training samples with `np.apply_along_axis`, which runs a Python function once per row, twice. The corner and angle maths can be done with NumPy on the whole `(n, 3)` array at once | Data generation becomes roughly 100× faster; training still dominates |
| O10 | Training | `MLPRegressor` trains on one CPU core for hours. Add `early_stopping=True` and `n_iter_no_change`, use fewer samples, or use a framework that can use several cores or a GPU. I1 removes the need for training altogether | Hours saved |

---

## 4. Areas of improvement

### I1. Replace the regressor with an analytic pose solver (recommended)
The corners of a square of known size, together with the camera intrinsics, are exactly what `cv2.solvePnP` (for
example with `SOLVEPNP_IPPE_SQUARE`) needs. It returns the full 6-DOF pose (position *and* yaw) in closed form. This
would:
- remove the pickled model, the multi-hour training, the conflict between `master` and `aarch` pickles, the pickle
  security concern, and the pinned scikit-learn version
- give a real yaw estimate, fixing the rotation problem in B2 and B4
- correct properly for camera tilt when combined with the vehicle's attitude

OpenCV is already a dependency.

### I2. Packaging and paths
- Resolve file paths from `Path(__file__).resolve().parent` so the program works from any directory (the "Gotcha" in
  quick-start).
- Add a `pyproject.toml`, use package-relative imports, and run with `python -m precision_drone_landing`.
- Publish the patched PyZBar as its own package, or check whether upstream `pyzbar` now includes PR #78, instead of
  keeping a copy in the source tree. This is already listed in `docs/technical_debt.md`.

### I3. Merge the `master` and `aarch` branches using configuration
Make the camera source (AirSim or Pi camera), the preview (on or off), and the startup mode (simulation or real) into
config or command-line options, each backed by a small interface such as `FrameSource.get_frame()`. With I1, the
difference in pickles disappears, and there is no longer any reason to keep two branches.

### I4. Configuration
- Move the magic numbers into `config.py` with environment overrides: PID gains, the 15 m outlier cutoff, miss
  thresholds, landing pixel thresholds, the 3 s window, and the 0.2 rad tilt limit.
- Validate values when the program starts.
- Load `qr_sizes.json` once. It is currently read in both `config.py:21` and `displacement_estimator.py:50`.

### I5. Testing and CI
- Commit a `tests/` directory. It is currently in `.gitignore`, so CI runs nothing.
- Add unit tests for the pure logic: QR payload parsing (B3), `PointSorter` not changing its input (B2),
  `_clear_position_data` (B8), `estimate_rotation`, `target_to_drone_space`, `should_land` thresholds, and an end-to-end
  check that a synthetic projected square gives the expected displacement (B1, B7, B18).
- Run the existing doctests with `pytest --doctest-modules`.
- Add a linter such as `ruff` and a type checker such as `mypy`. The code already has partial type hints.
- The repository is now on GitHub, but CI is still GitLab-only (`.gitlab-ci.yml`). Add a GitHub Actions workflow.

### I6. Dependencies
- Declare `matplotlib` (or make it optional, see B26) and `qrcode`.
- Pin versions with a lock file or constraints file so installs can be reproduced.
- Use `opencv-python-headless` on the Pi.
- `dronekit` is effectively unmaintained and is known to fail on Python 3.10+ (it uses `collections.MutableMapping`).
  Consider using `pymavlink` directly or MAVSDK-Python.
- Microsoft's AirSim repository is archived. Colosseum, a community fork, or ArduPilot's Gazebo SITL integration are
  maintained alternatives.

### I7. Code quality and structure
- Naming is inconsistent: `getPosition` and `targetZero` (camelCase) sit next to `get_target` and `update_velocity`
  (snake_case). Follow PEP 8 everywhere.
- `DroneControl` (about 400 lines) mixes connection setup, mode logic, estimation, and landing decisions. Split it into
  a vehicle adapter, an estimator, and a small explicit state machine
  (`WAIT → SEARCH → TRACK → FINAL → LAND`). This makes the mode behaviour in B14 and B15 testable.
- `LandingZone` uses a lock to protect data that never changes. A frozen `dataclass` or `NamedTuple` is enough, and the
  unused class attributes can go.
- `Controller.update(input)` uses the name of a built-in function as a parameter.
- `simple_guidance.update_state` is `async` but never awaits anything.
- Replace `print` with the `logging` module. Write telemetry CSVs to a per-run directory with a timestamp, and flush
  them regularly.

### I8. Documentation
- Fix the out-of-date instructions listed in quick-start: the run directory, line-number references, `$REPOSITORY`, the
  `fixme` link, and the GitLab URLs.
- Document the coordinate frames: image, camera, body, and NED axes and their signs. Several bugs above (B4, B18, the
  sign convention in `target_to_drone_space`) come from these never being written down.

---

## 5. Suggested order of work

1. **Before any real flight:** B6 (failsafe parameters and arming), B3 (crashes on stray QR codes), B4 (velocity
   frame), the failsafe wrapper from Safety item 1, and B12 (disarm).
2. **Correctness of estimates:** B1, B2, B7, B9, B10, then re-measure landing accuracy in simulation (and fix B5 first
   so the measurements can be trusted).
3. **Control-loop behaviour:** B8, B13, B14, B15, B11.
4. **Tests and CI (I5)**, so the fixes above stay fixed.
5. **Structural changes:** I1 (solvePnP), then I3 (a single branch) and I2 (packaging).
6. **Performance:** O1 and O2 first; the rest as needed.
