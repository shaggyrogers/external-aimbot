#!/usr/bin/env python3
"""
  aiming.py
  =========

  Description:           Handles aiming logic and keyboard/mouse
  Author:                Michael De Pasquale
  Creation Date:         2025-05-21
  Modification Date:     2025-05-23

"""

# NOTE: You likely won't have permission to read /dev/input/*, which will cause
# _getKeyboards() to fail. To fix this, add yourself to the 'input' group:
# >usermod -a -G input $USER_NAME
# Restart or use newgrp for this to take effect!

import fcntl
import logging
import os
import math
from pathlib import Path
from typing import Union

import libevdev
from libevdev import InputEvent

from model import Detection, ScreenCoord


# TODO: Should probably separate aiming logic from user input/output
# TODO: Add triggerbot functionality


class Aiming:
    def __init__(self, sensitivity: float = 1) -> None:
        self._log = logging.getLogger(
            self.__class__.__module__ + "." + self.__class__.__qualname__
        )

        # TODO: Option to change this?
        self._aimKey = libevdev.EV_KEY.KEY_CAPSLOCK
        self._sensitivity = sensitivity

        self._mouse = libevdev.Device()
        self._mouse.name = "Real Mouse"  # everyone back to the base, partner
        self._mouse.enable(libevdev.EV_REL.REL_X)
        self._mouse.enable(libevdev.EV_REL.REL_Y)
        self._mouse.enable(libevdev.EV_KEY.BTN_LEFT)
        self._mouse.enable(libevdev.EV_KEY.BTN_RIGHT)

        self._uinput = self._mouse.create_uinput_device()
        self._log.debug(
            f"Created virtual mouse: {self._uinput.devnode} ({self._uinput.syspath})"
        )

        self._keyboards = self._getKeyboards()

    def _getKeyboards(self) -> list[libevdev.Device]:
        """Open all keyboard devices in non-blocking mode. Returns a list of Device."""
        result = []

        for path in Path("/dev/input/by-path/").glob("*-kbd"):
            fd = open(path, "rb")
            fcntl.fcntl(fd, fcntl.F_SETFL, os.O_NONBLOCK)
            device = libevdev.Device(fd)
            assert device.has(libevdev.EV_KEY.KEY_A)

            self._log.debug(f"Found keyboard '{device.name}'")
            result.append(device)

        return result

    def _isAimKeyPressed(self) -> bool:
        """Return True if the aimbot key is pressed, False otherwise."""
        for device in self._keyboards:
            try:
                for event in device.events():
                    if event.matches(self._aimKey):

                        return True

            except libevdev.device.EventsDroppedException:
                self._log.exception("Events dropped!")

        return False

    def _selectTarget(
        self, screenSize: tuple[int, int], detections: list[Detection]
    ) -> Union[Detection, None]:
        """Return the closest Detection to the crosshair, or None if targets is empty"""
        smallestDist = math.inf
        screenMid = ScreenCoord(screenSize[0], screenSize[1]) / 2
        curTarget = None

        for target in detections:
            dist = screenMid.distanceTo(target.getPosition())

            if dist < smallestDist:
                curTarget = target
                smallestDist = dist

        return curTarget

    def _aimAt(self, screenSize: tuple[int, int], position: ScreenCoord) -> None:
        """Move mouse to position."""
        screenMid = ScreenCoord(screenSize[0], screenSize[1]) / 2
        delta = (position - screenMid) / self._sensitivity
        self._log.debug(f"Aiming delta: {repr(delta)}")

        self._uinput.send_events(
            [
                InputEvent(libevdev.EV_REL.REL_X, int(delta.x)),
                InputEvent(libevdev.EV_REL.REL_Y, int(delta.y)),
                InputEvent(libevdev.EV_SYN.SYN_REPORT, 0),
            ]
        )

    def run(
        self, screenSize: tuple[int, int], detections: list[Detection]
    ) -> Union[Detection, None]:
        """Run aimbot. Returns current target, or None if no target was found or aimbot is inactive."""
        if not self._isAimKeyPressed():
            return None

        target = self._selectTarget(screenSize, detections)

        if target:
            self._aimAt(screenSize, target.getPosition())

        return target
