#!/bin/bash
set -euxo pipefail
cd /tmp || exit 1
rm -rf renv
renv osrf/rocker
