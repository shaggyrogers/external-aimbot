#!/usr/bin/env python3
"""
  main.py
  =======

  Description:           Entry point
  Author:                Michael De Pasquale
  Creation Date:         2025-05-13
  Modification Date:     2025-05-28

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
from model import Model, ScreenCoord
import overlay
from screen_mask import AbsAreaMaskRegion, MaskRegion, ScreenMask
from ui import Menu, UI
import windowcap


SCREEN_MASK = ScreenMask(
    # Heuristics to avoid false positives.
    # Need to be fairly agressive here, otherwise our hand will be detected
    # as a person while reloading
    regions=[
        # Ignore anything that encroaches too much into a long rectangle along
        # the bottom of the scan area
        MaskRegion(
            ScreenCoord(640 / 1920, 633 / 1080),
            ScreenCoord(1280 / 1920, 780 / 1080),
            threshold=0.8,
        ),
        # Disregard detections that are too big relative to scan area
        AbsAreaMaskRegion(
            ScreenCoord((1920 / 2 - 640 / 2) / 1920, (1080 / 2 - 480 / 2) / 1080),
            ScreenCoord((1920 / 2 + 640 / 2) / 1920, (1080 / 2 + 480 / 2) / 1080),
            threshold=0.375,
        ),
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
    threshold: float = 0.4,
    debug: bool = False,
) -> int:
    log = logging.getLogger()
    logging.basicConfig(level=logging.DEBUG)

    if not torch.cuda.is_available():
        log.warning("GPU acceleration not available!")

    signal.signal(signal.SIGINT, sigintHandler)
    windowId = int(windowId, base=0)
    assert 0 <= threshold <= 1

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

    # Only look at 640x480 rectangle centred at the crosshair.
    # This is for performance reasons but also mostly avoids spurious detections of player
    # model and deathmatch scoreboard in cs2 (at least at 1920x1080)
    screenMid = ScreenCoord(screenWidth / 2, screenHeight / 2)
    regionTopLeft = screenMid - ScreenCoord(640 / 2, 480 / 2)
    region = tuple(map(int, (regionTopLeft.x, regionTopLeft.y, 640, 480)))

    assert not windowcap.selectWindow(windowId)
    log.debug("Initialised windowcap")

    # FIXME: If game FPS too low, we will get the same frame twice in a row and
    # consequently move the mouse too fast. Need to detect if game window has changed
    model = Model("yolo11m.pt", debug=debug)

    while True:
        regionWidth, regionHeight, data = windowcap.screenshot(region)
        image = Image.frombytes("RGB", (regionWidth, regionHeight), data)

        detections = model.processFrame(image, offset=regionTopLeft)
        detections = SCREEN_MASK.filter(
            (screenWidth, screenHeight),
            filter(lambda d: d.confidence >= threshold, detections),
        )

        inputMgr.update()
        ui.draw(
            overlay,
            (screenWidth, screenHeight),
            region,
            detections,
            aiming.run(
                screenMid,
                detections,
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
