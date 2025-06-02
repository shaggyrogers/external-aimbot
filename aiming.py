#!/usr/bin/env python3
"""
  aiming.py
  =========

  Description:           Implements the aimbot/triggerbot
  Author:                Michael De Pasquale
  Creation Date:         2025-05-21
  Modification Date:     2025-06-02

"""

import logging
import math
from typing import Union

import libevdev

from model import ScreenCoord, TrackedDetection
from input_manager import InputManager


class Aiming:
    def __init__(
        self, inputMgr: InputManager, aimKey: libevdev.EV_KEY, sensitivity: float = 1
    ) -> None:
        self._log = logging.getLogger(
            self.__class__.__module__ + "." + self.__class__.__qualname__
        )
        self._inputMgr = inputMgr
        self._aimKey = aimKey
        self._sensitivity = sensitivity

    def _selectTarget(
        self, screenMid: ScreenCoord, detections: list[TrackedDetection]
    ) -> Union[TrackedDetection, None]:
        """Return the closest Detection to the crosshair, or None if targets is empty"""
        smallestDist = math.inf
        curTarget = None

        for target in detections:
            dist = screenMid.distanceTo(target.latest.getPosition())

            if dist < smallestDist:
                curTarget = target
                smallestDist = dist

        return curTarget

    def _isAimingAtPlayer(
        self, screenMid: ScreenCoord, detections: list[TrackedDetection]
    ) -> bool:
        """True if the crosshair falls within a detection, False otherwise."""
        for det in detections:
            box = det.latest.getTriggerBox()

            if (
                box[0].x <= screenMid.x
                and box[1].x >= screenMid.x
                and box[0].y <= screenMid.y
                and box[1].y >= screenMid.y
            ):
                return True

        return False

    def run(
        self,
        screenMid: ScreenCoord,
        detections: list[TrackedDetection],
        aimbot: bool = True,
        triggerbot: bool = True,
        where: str = "center",
    ) -> Union[TrackedDetection, None]:
        """Run aimbot and triggerbot.
        Returns current target, or None if no target was found/selected.
        """
        if not self._inputMgr.isPressed(self._aimKey) or not (aimbot or triggerbot):
            return None

        target = None

        if aimbot and (target := self._selectTarget(screenMid, detections)):
            self._inputMgr.mouseMove(
                (target.interpolate().getPosition(where) - screenMid)
                * self._sensitivity
            )

        if triggerbot and self._isAimingAtPlayer(screenMid, detections):
            self._inputMgr.mouseClick()

        return target
