# external-aimbot
Fully external aimbot (WIP)

## Requirements

Only X11 is supported.

## Usage

* Build windowcap module
  - Install required dependencies
  - Run ./make-windowcap.sh
* Build python interface for X11Overlay and copy bin/overlay.so to current directory
* Download correct YOLO model file (see script) and copy to current directory
* Run script
  - `uv run python main.py`
