#!/usr/bin/env python3
"""
  model.py
  ========

  Description:           Wrapper for the object detection/tracking model.
  Author:                Michael De Pasquale
  Creation Date:         2025-05-21
  Modification Date:     2025-05-30

"""

import logging
import math
from typing import Any, Union

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

    def __add__(self, other: "ScreenCoord") -> "ScreenCoord":
        """Elementwise addition"""
        return ScreenCoord(other.x + self.x, other.y + self.y)


class Detection:
    _triggerboxScale = 0.8

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

    @property
    def width(self) -> float:
        return self.xy2.x - self.xy1.x

    @property
    def height(self) -> float:
        return self.xy2.y - self.xy1.y

    def getPosition(self, where: str = "center") -> ScreenCoord:
        """Get position, optionally applying an offset to the result.
        where can be 'center', 'head' or 'chest'
        """
        if where == "center":
            return ScreenCoord(
                (self.xy1.x + self.xy2.x) / 2,
                (self.xy1.y + self.xy2.y) / 2,
            )

        # Use the shape of the bounding box to guess where the head/chest should be
        assert where in ("head", "chest")
        ratioPc = (max(1, min(2.465, self.height / self.width)) - 1) / 1.465
        yOffPc = ratioPc * (0.08 if where == "head" else 0.38) + (1 - ratioPc) * 0.5

        return ScreenCoord(
            (self.xy1.x + self.xy2.x) / 2, (self.xy1.y + self.height * yOffPc)
        )

    def getTriggerBox(self) -> tuple[ScreenCoord, ScreenCoord]:
        """Return a smaller box to be used by the triggerbot"""
        # FIXME: Should probably add lower bounds to avoid box being too tiny
        center = self.getPosition()
        wHalf = self.width / 2 * self._triggerboxScale
        hHalf = self.height / 2 * self._triggerboxScale

        return (
            ScreenCoord(center.x - wHalf, center.y - hHalf),
            ScreenCoord(center.x + wHalf, center.y + hHalf),
        )


class Model:
    def __init__(self, filename: str, debug: bool = False) -> None:
        self._log = logging.getLogger(
            self.__class__.__module__ + "." + self.__class__.__qualname__
        )
        self._model = YOLO(filename)
        self._debug = debug
        self._log.info("Initialised model")

    def processFrame(
        self,
        img: Image,
        imgSize: ScreenCoord,
        offset: ScreenCoord,
        confidence: float = 0.25,
    ) -> list[Detection]:
        """Process frame, detecting/tracking targets. Yields Detection instances.
        Offset is added to the positions of all detections
        """
        results = []

        for result in self._model.track(
            img,
            verbose=self._debug,
            classes=[0],
            conf=confidence,
            rect=True,
            imgsz=(imgSize.x, imgSize.y),
        ):
            for box in result.boxes:
                xyxy = tuple(map(lambda v: v.item(), box.xyxy[0].cpu().numpy()))

                # Skip if no associated tracking ID
                if box.id is None:
                    continue

                results.append(
                    Detection(
                        int(box.id.item()),
                        box.conf.item(),
                        ScreenCoord(xyxy[0] + offset.x, xyxy[1] + offset.y),
                        ScreenCoord(xyxy[2] + offset.x, xyxy[3] + offset.y),
                    )
                )

        return results
