#!/usr/bin/env sh

ROOT_UID="0"
if [ "$(id -u)" -ne "$ROOT_UID" ] ; then
    echo "This script must be executed as root."
    exit 1
fi

# Somewhere down the dependency graph, tzinfo gets installed.
# When this happens, it creates an interactive prompt.
# We don't want this to happen. Thus, DEBIAN_FRONTEND keeps the
# installer from querying the user.
export DEBIAN_FRONTEND=noninteractive

apt-get install --assume-yes \
    python3 \
    python3-pip \
    python3-dev \
    python3-venv \
    python3-tk \
    gcc \
    libxml2-dev \
    libxslt-dev \
    libgeos-dev \
    libzbar0

echo "Dependencies installed successfully!"
exit 0
