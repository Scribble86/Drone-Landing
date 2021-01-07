# Setting Up the Development Environment

This guide contains instructions for setup of a software-in-the-loop dev environment. The procedure for a drone
deployment is similar, but has some important differences. See [this guide](fixme) for instructions on drone deployment.

The development environment *requires* a workstation with a moderately powerful discrete GPU. An Nvidia GTX 1060 has
been confirmed to work appreciably well, though a less powerful graphics card may also be acceptable. However,
integrated graphics has proven multiple times to be insufficient for these purposes. A desktop form factor is highly
recommended, as nearly all laptops fail this requirement.

Furthermore, these instructions are tailored for an Ubuntu operating system or derivative. While another Linux
distribution may provide the necessary libraries, we have repeatedly hit problems when using other distributions and
thus you should consider any such use at your own risk. In addition, MacOS may be usable, but Mac laptops tend to have
integrated GPUs, and are thus not usable due to the above requirement. We have not tested it, but Windows may work.
Again, attempt at your own risk.

Unreal Engine requires at least 100 GB of disk space.

## Install Unreal Engine

Unreal Engine is used here as a flight simulator.

[See install instructions here.](https://docs.unrealengine.com/en-US/SharingAndReleasing/Linux/BeginnerLinuxDeveloper/SettingUpAnUnrealWorkflow/index.html)

## Install AirSim

Airsim is the way we can get our software talking to Unreal Engine. It comes with a preinstalled "Blocks" environment
which we have found sufficient for testing.

[See build instructions here.](https://microsoft.github.io/AirSim/build_linux/#build-airsim)

Additionally, AirSim requires a configuration file. On Ubuntu, it typically resides at `~/Documents/settings.json`.
However, if this is inconvenient for your use case, you can
[specify a custom location](https://microsoft.github.io/AirSim/settings/#where-are-settings-stored).

We have included a copy of our `settings.json` file [here](../config/airsim_settings.json), which we recommend you use
instead of writing your own. `settings.json` contains relevant configuration such as camera resolution, camera FOV, and
vehicle type.

## Install Ardupilot

Ardupilot takes the place of the PixHawk in the simulation environment.

[See install instructions here.](https://ardupilot.org/dev/docs/building-setup-linux.html)

## Installing this software

Remember to replace `$REPOSITORY` below with the actual repository location. It is not known at time of writing.
However, the branch suited for development is `master`, which should get pulled down automatically by Git.

```bash
git clone $REPOSITORY precision_drone_landing
cd precision_drone_landing
sudo install-deps-ubuntu.sh
python3 -m venv venv
source ./venv/bin/activate
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

Whenever you wish to run this software again from a new shell session, you must run `source venv/bin/activate`, but the
other changes are persistent.

## Configuring the Environment

See [Configuring the Environment](environment_configuration.md)

## Moving On

You are now ready to continue to [Running the Development Environment](dev_environment_running.md).