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

import logging
import os
import math
from pathlib import Path
from typing import Union

import libevdev
from libevdev import InputEvent

from model import Detection, ScreenCoord
from input_manager import InputManager


class Aiming:
    def __init__(self, inputMgr: InputManager, sensitivity: float = 1) -> None:
        self._log = logging.getLogger(
            self.__class__.__module__ + "." + self.__class__.__qualname__
        )

        self._inputMgr = inputMgr

        # TODO: Option to change this? should probably be the domain of InputManager
        # TODO: Also want aimbot/triggerbot/(body/head) toggles
        self._aimKey = libevdev.EV_KEY.KEY_LEFTALT  # KEY_CAPSLOCK
        self._sensitivity = sensitivity

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
        if not self._inputMgr.isPressed(self._aimKey):
            return None

        target = None

        if aimbot and (target := self._selectTarget(screenMid, detections)):
            self._inputMgr.mouseMove(
                (target.getPosition() - screenMid) / (1 / self._sensitivity)  # FIXME
            )

        if triggerbot and self._isAimingAtPlayer(screenMid, detections):
            self._inputMgr.mouseClick()

        return target
