#!/bin/bash
# Remove the renv directory and run renv with the specified argument
set -oux pipefail
rm -rf renv
renv osrf/rocker
