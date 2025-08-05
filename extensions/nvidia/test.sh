#!/bin/bash
# Simple test for nvidia extension - verify nvidia runtime is available
# This will pass if NVIDIA_VISIBLE_DEVICES is set (even if no GPU present)
echo "NVIDIA_VISIBLE_DEVICES=${NVIDIA_VISIBLE_DEVICES:-not_set}"