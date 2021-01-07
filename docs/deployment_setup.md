# Setting up the software on the Raspberry Pi

This guide assumes that you are running Raspberry OS on a Raspberry Pi 4.

1. clone remote git repository:
git clone https://gitlab.eecs.wsu.edu/44353/precision-drone-landing.git --branch aarch

2. Install ssl and build-essentials:
 sudo apt install build-essential cmake
 sudo apt install checkinstall libreadline-gplv2-dev libssl-dev libsqlite3-dev tk-dev libgdbm-dev libc6-dev libbz2-dev libffi-dev

3. As of writing, the Debian (and thus Raspberry OS) repositories do not package a new enough version of Python to install
with `apt`. Thus, we have to download and compile Python manually. I recommend installing python 3.8.5 for maximum compatity.
Python 3.9 also works and is what is included on the existing pi. [The Python documentation has instructions for that here](https://docs.python.org/3/using/unix.html#building-python).
Don't use the altinstall option, but do use --enable-optimizations when configuring.

4. Install numpy: pip install wheel
pip install numpy

5. install sklearn: sudo pip3 install scikit-learn

6. install prereqs for lxml: sudo apt install libxslt1.1 libxslt1-dev python-libxslt1 python-lxml python3-lxml libxml2

7. The OpenCV library is packaged with its Python bindings on x86 architectures, and it is included in the Pip
install. This is not the case on ARM architectures like the Raspberry Pi. We must install OpenCV
manually. [We found this guide useful](https://www.pyimagesearch.com/2018/09/26/install-opencv-4-on-your-raspberry-pi/),
though we note that it is third-party.
A few notes about these instructions: You may skip step 1 instructions for the raspberry pi 4, since it ships with large
volume support enabled. It is also recommended to get the latest version of the source from the opencv and opencv_contrib
releases available from [the OpenCV github](https://github.com/opencv).
You should also skip the creation of a virtual environment during the above installation process, because other required
packages will be installed outside of it.
Note that the delivered Pi has a pre-built copy of opencv on it. You need to install the dependencies first, and then
you can run "sudo make -j4 install" from the opencv/build directory to install it. This will avoid the long compile times and the need to mess about
with cache sizes.

8. change directory to ~/home/precision-drone-landing and run
"install-deps-ubuntu.sh" as root.

9. install project requirements using pip3 install -r ./requirements.txt. This will take a while.

10. cd into repository scripts folder and generate the displacement model. This will also take a while.
cd ~/home/precision-drone-landing/scripts
python3 generate_displacement_model.py

11. move resulting regressor.pkl file from ~/home/precision-drone-landing/assets/displacement_detection_models/
to ~/home/precision-drone-landing/precision-drone-landing.

12. it is recommended to create an image of the raspberry pi after validating functionality so that this long setup can be
avoided in the future.

## Moving on

You can now continue to [Running the Deployment Environment](deployment_running.md).