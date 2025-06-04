#!/usr/bin/env python3
"""
  main.py
  =======

  Description:           Entry point
  Author:                Michael De Pasquale
  Creation Date:         2025-05-13
  Modification Date:     2025-06-04

"""
# pylint: disable=c-extension-no-member,import-error

import logging
import signal
import sys
import time

import arguably
import libevdev
from PIL import Image
import pyinstrument
import torch
from ultralytics import YOLO

from aiming import Aiming
from input_manager import InputManager
from model import Detection, Model, ScreenCoord, TrackedDetection, Tracker
import overlay
from screen_mask import AbsAreaMaskRegion, MaskRegion, ScreenMask
from ui import Menu, UI
import windowcap


# Only look at a 640x640 box centred at the crosshair.
# Model expects 640x640 and will scale/pad input image to fit. Using a larger region
# means image is scaled down, and will degrade detection accuracy for distant players.
# This also improves performance and reduces spurious detections of cs2 player model and
# deathmatch scoreboard.
REGION_SIZE = ScreenCoord(640, 640)

SCREEN_MASK = ScreenMask(
    # Heuristics to avoid false positives.
    # Need to be fairly agressive here, otherwise our hand will be detected
    # as a person while reloading
    regions=[
        MaskRegion(
            ScreenCoord(870 / 1920, 700 / 1080),
            ScreenCoord(1440 / 1920, 860 / 1080),
            threshold=0.8,
        ),
        # Disregard detections that are too big relative to scan area
        # FIXME: This results in false negatives when players are very close...
        # Disabled for now.
        # AbsAreaMaskRegion(
        #     ScreenCoord((1920 / 2 - 640 / 2) / 1920, (1080 / 2 - 480 / 2) / 1080),
        #     ScreenCoord((1920 / 2 + 640 / 2) / 1920, (1080 / 2 + 480 / 2) / 1080),
        #     threshold=0.375,
        # ),
    ]
)


def sigintHandler(signal, frame) -> None:
    logging.getLogger().debug("Got SIGINT, cleaning up and exiting..")
    overlay.cleanup()

    sys.exit(0)


@arguably.command()
def main(
    windowId: str,
    *,
    sensitivity: float = 1,
    confidence: float = 0.4,
    triggerbox_scale: float = 0.8,
    interp_scale: float = 4,
    debug: bool = True,
) -> int:
    """Run the aimbot.

    Args:
        windowId: Target window ID. Get from xwininfo.
        sensitivity: How fast the aimbot moves the mouse. Larger values yield faster movement.
        confidence: Confidence threshold for player detection. Must be in range [0, 1]
        triggerbox_scale: How large triggerbot boxes are relative to bounding boxes. Must be in range [0, 1]
        interp_scale: Scaling factor for interpolation. Roughly the number of frames to look ahead when aiming.
        debug: Enable debug mode
    """
    windowId = int(windowId, base=0)
    assert 0 <= confidence <= 1
    assert 0 <= triggerbox_scale <= 1
    assert interp_scale > 0
    Detection._TRIGGERBOX_SCALE = triggerbox_scale
    TrackedDetection._INTERP_SCALE = interp_scale

    log = logging.getLogger()
    logging.basicConfig(level=logging.DEBUG)

    if not torch.cuda.is_available():
        log.warning("GPU acceleration not available!")

    signal.signal(signal.SIGINT, sigintHandler)

    inputMgr = InputManager(debug=debug)
    menu = Menu(inputMgr)
    menu.addItem(Menu.ToggleItem("Aimbot", libevdev.EV_KEY.KEY_F1))
    menu.addItem(Menu.ToggleItem("Triggerbot", libevdev.EV_KEY.KEY_F2))
    menu.addItem(
        Menu.CycleItem("Target", libevdev.EV_KEY.KEY_F3, ["chest", "head", "center"])
    )
    ui = UI(menu)
    aiming = Aiming(inputMgr, libevdev.EV_KEY.BTN_SIDE, sensitivity=sensitivity)

    log.info("======== Controls ========")
    log.info(f" * Activate: {aiming._aimKey} ")

    for item in menu.items:
        log.info(
            " * "
            + ("Toggle" if isinstance(item, Menu.ToggleItem) else "Cycle")
            + f" {item.name}: {item.button}"
        )

    log.info("==========================")

    overlay.init()
    screenWidth, screenHeight = overlay.setTargetWindow(windowId)
    log.debug("Initialised overlay")

    screenMid = ScreenCoord(screenWidth / 2, screenHeight / 2)
    regionTopLeft = screenMid - REGION_SIZE / 2
    region = tuple(
        map(int, (regionTopLeft.x, regionTopLeft.y, REGION_SIZE.x, REGION_SIZE.y))
    )

    assert not windowcap.selectWindow(windowId)
    log.debug("Initialised windowcap")

    model = Model("yolo11m.pt", debug=debug)
    tracker = Tracker(ScreenCoord(screenWidth, screenHeight))
    lastImage = None

    while True:
        regionWidth, regionHeight, data = windowcap.screenshot(region)
        image = Image.frombytes("RGB", (regionWidth, regionHeight), data)

        if image == lastImage:
            time.sleep(0)

            continue

        lastImage = image

        detections = model.processFrame(
            image, REGION_SIZE, offset=regionTopLeft, confidence=confidence
        )
        detections = SCREEN_MASK.filter((screenWidth, screenHeight), detections)
        tracker.update(detections)

        inputMgr.update()
        ui.draw(
            overlay,
            (screenWidth, screenHeight),
            region,
            tracker.tracked,
            aiming.run(
                screenMid,
                tracker.tracked,
                aimbot=menu["Aimbot"],
                triggerbot=menu["Triggerbot"],
                where=menu["Target"],
            ),
            SCREEN_MASK if debug else None,
            triggerBoxes=menu["Triggerbot"],
        )

        time.sleep(0)  # os.sched_yield() ?

    return 0


if __name__ == "__main__":
    sys.exit(arguably.run())
