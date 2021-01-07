# Information About Git Branches

There are two main development branches with distinct purposes. These are:

* `master`
* `aarch`

It should be noted that the fact that these two are separate is a point of [Technical Debt](technical_debt.md).

## The `master` branch

This branch is used for primary development. It contains code which runs on a developer's computer. If you are
developing this project, and wish to run the code in simulation (see
[Setting Up the Development Environment](dev_environment_setup.md) and
[Running the Development Environment](dev_environment_running.md))
then you should use this branch.

## The `aarch` branch

This branch contains code which should run on the Raspberry Pi in real deployment. There are a number of differences 
which make it difficult to use for development:

* The function used to retrieve images from the drone camera
* Absence of the preview window
* The pickled regressor at `assets/displacement_detection_models/regressor.pkl`
