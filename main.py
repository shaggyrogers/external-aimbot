#!/usr/bin/env python3
"""
  main.py
  =======

  Description:           Entry point
  Author:                Michael De Pasquale
  Creation Date:         2025-05-13
  Modification Date:     2025-05-19

"""

import logging
import signal
import sys
import time

from PIL import Image
from ultralytics import YOLO

import arguably
import windowcap
import overlay

# pylint: disable=c-extension-no-member

logging.basicConfig(level=logging.DEBUG)


def sigintHandler(signal, frame) -> None:
    logging.getLogger().debug("Got SIGINT, cleaning up and exiting..")
    overlay.cleanup()

    sys.exit(0)


@arguably.command()
def main(windowId: str) -> int:
    log = logging.getLogger()
    signal.signal(signal.SIGINT, sigintHandler)

    if windowId.startswith("0x"):
        windowId = int(windowId[2:], base=16)

    else:
        windowId = int(windowId)

    model = YOLO("yolo11s.pt")
    log.debug("Instantiated model")

    overlay.init()
    overlayWidth, overlayHeight = overlay.getWidth(), overlay.getHeight()
    log.debug("Initialised overlay")

    print(f"selectWindow returned {windowcap.selectWindow(windowId)}")

    while True:
        width, height, data = windowcap.screenshot()
        img = Image.frombytes("RGB", (width, height), data)

        results = model.predict(img)  # , device="cuda:0"

        # Draw
        overlay.clear()

        for result in results:
            for box in result.boxes:
                name = result.names[int(box.cls[0])]

                if name != "person":
                    continue

                xyxy = tuple(map(lambda v: v.item(), box.xyxy[0].numpy()))

                overlay.addText(name, xyxy[0], xyxy[1], 24, 0.3, 0.9, 0.3, 1, False)
                overlay.addRectangle(
                    xyxy[0], xyxy[1], xyxy[2], xyxy[3], 0.1, 1, 0.1, 1, False, 2
                )

        overlay.draw()
        time.sleep(0)  # os.sched_yield() ?

    return 0


if __name__ == "__main__":
    sys.exit(arguably.run())
