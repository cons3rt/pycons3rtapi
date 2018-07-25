#!/bin/bash

# The purpose of this script is to install pycons3rtapi into your local
# python installation

echo "Installing pycons3rtapi..."

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd ${SCRIPT_DIR}/..
python ${SCRIPT_DIR}/../setup.py install
result=$?

echo "pycons3rtapi installation exited with code: ${result}"
exit ${result}
