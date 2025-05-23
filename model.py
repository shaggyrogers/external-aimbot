#!/usr/bin/env python3
"""
  model.py
  ========

  Description:           Wrapper for the object detection/tracking model.
  Author:                Michael De Pasquale
  Creation Date:         2025-05-21
  Modification Date:     2025-05-23

"""

import logging
import math
from typing import Any

from ultralytics import YOLO, settings
from PIL import Image

# TODO: Compare YOLOv11 tracking with https://github.com/TrackingLaboratory/CAMELTrack


class ScreenCoord:
    __slots__ = ("_x", "_y")

    def __init__(self, x: float, y: float) -> None:
        self._x = x
        self._y = y

    @property
    def x(self) -> float:
        return self._x

    @property
    def y(self) -> float:
        return self._y

    def distanceTo(self, other: "ScreenCoord") -> float:
        """Returns the euclidian distance between this and another ScreenCoord."""
        return math.sqrt(pow(self.x - other.x, 2) + pow(self.y - other.y, 2))

    def product(self) -> float:
        """Returns x multiplied by y"""
        return self.x * self.y

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(x={self.x}, y={self.y})"

    def __sub__(self, other: "ScreenCoord") -> "ScreenCoord":
        """Elementwise subtraction"""
        return ScreenCoord(self.x - other.x, self.y - other.y)

    def __truediv__(self, scalar: float) -> "ScreenCoord":
        """Scalar division"""
        return ScreenCoord(self.x / scalar, self.y / scalar)

    def __mul__(self, other: "ScreenCoord") -> "ScreenCoord":
        """Elementwise multiplication"""
        return ScreenCoord(self.x * other.x, self.y * other.y)


class Detection:
    def __init__(
        self, id: Any, confidence: float, xy1: ScreenCoord, xy2: ScreenCoord
    ) -> None:
        self.id = id
        self.confidence = confidence
        self.xy1 = xy1
        self.xy2 = xy2

        assert 0 <= confidence <= 1
        assert xy1.x <= xy2.x
        assert xy1.y <= xy2.y

    def getPosition(self) -> ScreenCoord:
        # For now, just use the center of the bounding box.
        # TODO: Use offsets for center of chest / head?
        return ScreenCoord(
            (self.xy1.x + self.xy2.x) / 2,
            (self.xy1.y + self.xy2.y) / 2,
        )


class Model:
    def __init__(self, filename: str, debug: bool = False) -> None:
        self._log = logging.getLogger(
            self.__class__.__module__ + "." + self.__class__.__qualname__
        )
        self._model = YOLO(filename)
        self._debug = debug
        self._log.info("Initialised model")

    def processFrame(self, img: Image) -> list[Detection]:
        """Process frame, detecting/tracking targets. Yields Detection instances."""
        results = []

        for result in self._model.track(img, verbose=self._debug, device="cuda:0"):
            for box in filter(
                lambda b: result.names[int(b.cls[0])] == "person", result.boxes
            ):
                xyxy = tuple(map(lambda v: v.item(), box.xyxy[0].cpu().numpy()))

                # Skip if no associated tracking ID
                if box.id is None:
                    continue

                results.append(
                    Detection(
                        int(box.id.item()),
                        box.conf.item(),
                        ScreenCoord(xyxy[0], xyxy[1]),
                        ScreenCoord(xyxy[2], xyxy[3]),
                    )
                )

        return results
