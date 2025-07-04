#!/bin/bash

# Exit script on any error
set -e

echo "--- Vercel Build Script Starting ---"

# Vercel runs on Debian, so we use apt-get
# Update package lists and install system dependencies for lxml and other common libraries
echo "--- Installing System Dependencies (for lxml, etc.) ---"
apt-get update -y
apt-get install -y build-essential libxml2-dev libxslt-dev

# Now, install Python dependencies into the location Vercel expects
echo "--- Installing Python Dependencies from api/requirements.txt ---"
pip install --disable-pip-version-check --target . --upgrade -r api/requirements.txt

echo "--- Build Script Finished ---"