#!/usr/bin/env python3
"""
  aiming.py
  =========

  Description:           Handles aiming logic and keyboard/mouse
  Author:                Michael De Pasquale
  Creation Date:         2025-05-21
  Modification Date:     2025-05-26

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
        # FIXME: We get duplicates of each keyboard
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
                # FIXME: This happens fairly often?
                self._log.exception("Events dropped!")

        return False

    def _selectTarget(
        self, screenMid: ScreenCoord, detections: list[Detection]
    ) -> Union[Detection, None]:
        """Return the closest Detection to the crosshair, or None if targets is empty"""
        smallestDist = math.inf
        curTarget = None

        for target in detections:
            dist = screenMid.distanceTo(target.getPosition())

            if dist < smallestDist:
                curTarget = target
                smallestDist = dist

        return curTarget

    def _aimAt(self, screenMid: ScreenCoord, position: ScreenCoord) -> None:
        """Move mouse to position."""
        delta = (position - screenMid) / self._sensitivity
        self._uinput.send_events(
            [
                InputEvent(libevdev.EV_REL.REL_X, int(delta.x)),
                InputEvent(libevdev.EV_REL.REL_Y, int(delta.y)),
                InputEvent(libevdev.EV_SYN.SYN_REPORT, 0),
            ]
        )

    def _fire(self) -> None:
        """Left click the mouse."""
        self._uinput.send_events(
            [
                InputEvent(libevdev.EV_KEY.BTN_LEFT, 1),
                InputEvent(libevdev.EV_SYN.SYN_REPORT, 0),
                InputEvent(libevdev.EV_KEY.BTN_LEFT, 0),
                InputEvent(libevdev.EV_SYN.SYN_REPORT, 0),
            ]
        )

    def _isAimingAtPlayer(
        self, screenMid: ScreenCoord, detections: list[Detection]
    ) -> bool:
        """True if the crosshair falls within a detection, False otherwise."""
        for det in detections:
            if (
                det.xy1.x <= screenMid.x
                and det.xy2.x >= screenMid.x
                and det.xy1.y <= screenMid.y
                and det.xy2.y >= screenMid.y
            ):
                return True

        return False

    def run(
        self,
        screenMid: ScreenCoord,
        detections: list[Detection],
        aimbot: bool = True,
        triggerbot: bool = True,
    ) -> Union[Detection, None]:
        """Run aimbot and triggerbot. Returns current target, or None if no target was found/selected."""
        if not self._isAimKeyPressed():
            return None

        target = None

        if aimbot and (target := self._selectTarget(screenMid, detections)):
            self._aimAt(screenMid, target.getPosition())

        if triggerbot and self._isAimingAtPlayer(screenMid, detections):
            self._fire()

        return target
