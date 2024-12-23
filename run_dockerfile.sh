#!/bin/bash
# This file was autogenerated by rockerc
docker run \
  --rm \
  -it \
  -v \
  /etc/gitconfig:/etc/gitconfig:ro \
  -v \
  /home/ags/.gitconfig:/home/ags/.gitconfig:ro \
  --gpus \
  all \
  -e \
  DISPLAY \
  -e \
  TERM \
  -e \
  QT_X11_NO_MITSHM=1 \
  -e \
  XAUTHORITY=/tmp/.dockerdpwfsrd3.xauth \
  -v \
  /tmp/.dockerdpwfsrd3.xauth:/tmp/.dockerdpwfsrd3.xauth \
  -v \
  /tmp/.X11-unix:/tmp/.X11-unix \
  -v \
  /etc/localtime:/etc/localtime:ro \
  2c0fa894c048