# external-aimbot

This is a generic external aimbot. It finds players in the game window using YOLO11 and moves the mouse to aim at them.

## Requirements

A linux distro running an X11 display server is required. Only tested on Ubuntu 24.04 with Gnome/Mutter.

## Installation

TODO: Dependency list

* Build windowcap module
  - Install required dependencies
  - Run ./make-windowcap.sh
* Build python interface for [X11Overlay](https://github.com/shaggyrogers/X11Overlay) and copy bin/overlay.so to project directory
* Download [YOLO11m model file](https://github.com/ultralytics/assets/releases/download/v8.3.0/yolo11m.pt) and copy to project directory

## Usage

* Start the target game and change to borderless windowed mode if necessary.
* See `run.sh`
