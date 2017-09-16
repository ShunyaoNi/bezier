#!/bin/bash
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

set -ev

MB_COMMON_UTILS="https://raw.githubusercontent.com/matthew-brett/multibuild/master/common_utils.sh"
MB_OSX_UTILS="https://raw.githubusercontent.com/matthew-brett/multibuild/master/osx_utils.sh"

if [[ -z "${PY_VERSION}" ]]; then
  echo "PY_VERSION environment variable should be set by the caller."
  exit 1
fi

brew install gcc  # For `gfortran`
which gfortran

# No need to see the content being sourced.
set +v

# Get the "bare minimum" from `matthew-brett/multibuild`
wget ${MB_COMMON_UTILS}
source common_utils.sh
wget ${MB_OSX_UTILS}
source osx_utils.sh

set -v

# Use `multibuild` to install the given python.org version of CPython.
get_macpython_environment ${PY_VERSION}
echo ${PYTHON_EXE}
echo ${PIP_CMD}

# Make sure our installed CPython is set up for testing.
${PIP_CMD} install --ignore-installed virtualenv pip
${PIP_CMD} install --upgrade nox-automation

export PY_BIN_DIR=$(dirname "${PYTHON_EXE}")
echo ${PY_BIN_DIR}