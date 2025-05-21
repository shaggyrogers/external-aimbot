#!/usr/bin/env python3
"""
  model.py
  ========

  Description:           Wrapper for the object detection/tracking model.
  Author:                Michael De Pasquale
  Creation Date:         2025-05-21
  Modification Date:     2025-05-21

"""

import logging
from collections import namedtuple
from typing import Iterable

from ultralytics import YOLO
from PIL import Image

# TODO: Compare YOLOv11 tracking with https://github.com/TrackingLaboratory/CAMELTrack

ScreenCoord = namedtuple(
    "ScreenCoord",
    [
        "x",
        "y",
    ],
)
Detection = namedtuple(
    "Detection",
    [
        "id",  # locally unique identifier for target
        "confidence",  # confidence value, between 0 and 1
        "xy1",
        "xy2",
    ],
)


class Model:
    def __init__(self, filename: str) -> None:
        self._log = logging.getLogger(
            self.__class__.__module__ + "." + self.__class__.__qualname__
        )
        self._model = YOLO(filename)
        self._log.info("Initialised model")

    def processFrame(self, img: Image) -> Iterable[Detection]:
        """Process frame, detecting/tracking targets. Yields Detection instances."""
        for result in self._model.track(img):  # , device="cuda:0"
            for box in filter(
                lambda b: result.names[int(b.cls[0])] == "person", result.boxes
            ):
                xyxy = tuple(map(lambda v: v.item(), box.xyxy[0].numpy()))

                yield Detection(
                    box.id,
                    box.conf.item(),
                    ScreenCoord(xyxy[0], xyxy[1]),
                    ScreenCoord(xyxy[2], xyxy[3]),
                )
