#!/usr/bin/env python3
"""
  main.py
  =======

  Description:           Entry point
  Author:                Michael De Pasquale
  Creation Date:         2025-05-13
  Modification Date:     2025-05-22

"""
# pylint: disable=c-extension-no-member,import-error

import logging
import signal
import sys
import time

from PIL import Image
from ultralytics import YOLO

import arguably
import windowcap
import overlay
from model import Model
from aiming import Aiming


logging.basicConfig(level=logging.DEBUG)


def sigintHandler(signal, frame) -> None:
    logging.getLogger().debug("Got SIGINT, cleaning up and exiting..")
    overlay.cleanup()

    sys.exit(0)


@arguably.command()
def main(wId: str, sensitivity: float = 1) -> int:
    log = logging.getLogger()
    signal.signal(signal.SIGINT, sigintHandler)
    wId = int(wId[2:], base=16) if wId.startswith("0x") else int(wId)

    overlay.init()
    overlay.setTargetWindow(wId)
    log.debug("Initialised overlay")

    assert not windowcap.selectWindow(wId)
    log.debug("Initialised windowcap")

    aiming = Aiming(sensitivity=sensitivity)

    model = Model("yolo11s.pt")

    while True:
        width, height, data = windowcap.screenshot()
        detections = model.processFrame(Image.frombytes("RGB", (width, height), data))

        target = aiming.run((width, height), detections)

        overlay.clear()

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
                0.1 if not isTarget else 1,
                1 if not isTarget else 0.1,
                0.1,
                1,
                False,
                2,
            )

        overlay.draw()
        time.sleep(0)  # os.sched_yield() ?

    return 0


if __name__ == "__main__":
    sys.exit(arguably.run())
