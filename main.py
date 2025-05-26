#!/usr/bin/env python3
"""
  main.py
  =======

  Description:           Entry point
  Author:                Michael De Pasquale
  Creation Date:         2025-05-13
  Modification Date:     2025-05-26

"""
# pylint: disable=c-extension-no-member,import-error

import logging
import signal
import sys
import time

from PIL import Image
import pyinstrument
import torch
from ultralytics import YOLO

import arguably
import windowcap
import overlay
from model import Model, ScreenCoord
from aiming import Aiming
from screen_mask import MaskRegion, ScreenMask


GAME_MASKS = {
    "cs2": ScreenMask(
        regions=[
            # TODO
            # The part of the local player model that intersects the scan area
            # MaskRegion(
            #     ScreenCoord(870 / 1920, 620 / 1080),
            #     ScreenCoord(1750 / 1920, 1080 / 1080),
            #     threshold=0.8,
            # ),
        ]
    )
}


class FrameCounter:
    """Reports average frames processed per second."""

    def __init__(self) -> None:
        self._count = 0
        self._lastFPS = 0
        self._lastPeriodEnd = time.monotonic()

    def increment(self) -> None:
        timeSince = time.monotonic() - self._lastPeriodEnd

        if timeSince >= 1:
            self._lastFPS = self._count
            self._lastPeriodEnd = time.monotonic()
            self._count = 0

        self._count += 1

    @property
    def fps(self) -> int:
        return int(self._lastFPS)


def sigintHandler(signal, frame) -> None:
    logging.getLogger().debug("Got SIGINT, cleaning up and exiting..")
    overlay.cleanup()

    sys.exit(0)


@arguably.command()
def main(windowId: str, *, sensitivity: float = 1, debug: bool = False) -> int:
    log = logging.getLogger()
    logging.basicConfig(level=logging.DEBUG)

    if not torch.cuda.is_available():
        log.warning(f"GPU acceleration not available!")

    signal.signal(signal.SIGINT, sigintHandler)
    windowId = int(windowId, base=0)

    overlay.init()
    screenWidth, screenHeight = overlay.setTargetWindow(windowId)
    log.debug("Initialised overlay")

    # Only look at 640x480 rectangle centred at the crosshair.
    # This is for performance reasons but also mostly avoids spurious detections of player
    # model and deathmatch scoreboard in cs2 (at least at 1920x1080)
    screenMid = ScreenCoord(screenWidth / 2, screenHeight / 2)
    regionTopLeft = screenMid - ScreenCoord(640 / 2, 480 / 2)
    region = tuple(map(int, (regionTopLeft.x, regionTopLeft.y, 640, 480)))

    assert not windowcap.selectWindow(windowId)
    log.debug("Initialised windowcap")

    aiming = Aiming(sensitivity=sensitivity)
    frameCounter = FrameCounter()

    model = Model("yolo11m.pt", debug=debug)
    screenMask = GAME_MASKS["cs2"]

    while True:
        regionWidth, regionHeight, data = windowcap.screenshot(region)
        image = Image.frombytes("RGB", (regionWidth, regionHeight), data)

        detections = model.processFrame(image, offset=regionTopLeft)
        detections = screenMask.filter((screenWidth, screenHeight), detections)

        target = aiming.run(screenMid, detections)
        frameCounter.increment()

        # Draw
        overlay.clear()
        overlay.addText(f"FPS: {frameCounter.fps}", 16, 16, 24, 1, 0, 0, 1, False)
        overlay.addRectangle(
            region[0],
            region[1],
            region[0] + region[2],
            region[1] + region[3],
            1,
            1,
            1,
            0.5,
            False,
            1,
        )

        if debug:
            for maskRegion in screenMask.regions:
                overlay.addRectangle(
                    maskRegion.xy1.x * screenWidth,
                    maskRegion.xy1.y * screenHeight,
                    maskRegion.xy2.x * screenWidth,
                    maskRegion.xy2.y * screenHeight,
                    0.1,
                    0.1,
                    0.7,
                    0.8,
                    False,
                    2,
                )

        for det in detections:
            isTarget = det is target
            overlay.addText(
                str(det.id), det.xy1.x, det.xy1.y, 24, 0.3, 0.9, 0.3, 1, False
            )
            overlay.addRectangle(
                det.xy1.x,
                det.xy1.y,
                det.xy2.x,
                det.xy2.y,
                0.1 if isTarget else 1,
                1 if isTarget else 0.1,
                0.1,
                0.8,
                False,
                2,
            )

        overlay.draw()
        time.sleep(0)  # os.sched_yield() ?

    return 0


if __name__ == "__main__":
    sys.exit(arguably.run())
