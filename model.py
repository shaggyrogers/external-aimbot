#!/usr/bin/env python3
"""
  model.py
  ========

  Description:           Wrapper for the object detection/tracking model.
  Author:                Michael De Pasquale
  Creation Date:         2025-05-21
  Modification Date:     2025-06-02

"""

from collections import deque
import logging
import math
import numbers
import time
from typing import Any, Iterable, Union

from ultralytics import YOLO, settings
from PIL import Image

# TODO: Compare YOLOv11 tracking with https://github.com/TrackingLaboratory/CAMELTrack


# TODO: Probably better to just use a numpy array..
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
        if isinstance(other, numbers.Number):
            return ScreenCoord(self.x - other, self.y - other)

        return ScreenCoord(self.x - other.x, self.y - other.y)

    def __truediv__(self, other: Union["ScreenCoord", numbers.Number]) -> "ScreenCoord":
        if isinstance(other, numbers.Number):
            return ScreenCoord(self.x / other, self.y / other)

        return ScreenCoord(self.x / other, self.y / other)

    def __mul__(self, other: Union["ScreenCoord", numbers.Number]) -> "ScreenCoord":
        if isinstance(other, numbers.Number):
            return ScreenCoord(self.x * other, self.y * other)

        return ScreenCoord(self.x * other.x, self.y * other.y)

    def __add__(self, other: Union["ScreenCoord", numbers.Number]) -> "ScreenCoord":
        if isinstance(other, numbers.Number):
            return ScreenCoord(self.x + other, self.y + other)

        return ScreenCoord(other.x + self.x, other.y + self.y)


class Detection:
    # Scaling factor for triggerbot boxes
    _TRIGGERBOX_SCALE = 0.8

    def __init__(
        self,
        id: Any,
        confidence: float,
        xy1: ScreenCoord,
        xy2: ScreenCoord,
    ) -> None:
        self.id = id
        self.confidence = confidence
        self.xy1 = xy1
        self.xy2 = xy2
        self.when = time.monotonic()

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
        # FIXME: Only covers around half of the head. Maybe return 2 boxes, body and head?
        # FIXME: Should probably add lower bounds to avoid box being too tiny
        center = self.getPosition()
        wHalf = self.width / 2 * self._TRIGGERBOX_SCALE
        hHalf = self.height / 2 * self._TRIGGERBOX_SCALE

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
            tracker="tracker.yaml",
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


class TrackedDetection:
    """Represents a tracked player. Records detections associated with the player and
    performs interpolation."""

    # Max age of recorded detections and this tracked player
    _DET_MAX_AGE = 0.4
    _INTERP_SCALE = 3

    def __init__(self, id: Any, initial: Detection) -> None:
        self._id = id
        self._detections = deque((initial,))  # TODO: Maybe good to have size limit
        self._lastUpdated = time.monotonic()

    @property
    def id(self) -> object:
        return self._id

    @property
    def lastUpdated(self) -> object:
        return self._lastUpdated

    @property
    def latest(self) -> Detection:
        return self._detections[-1]

    def update(self, detection: Detection) -> None:
        """Update current position and prune expired previously associated detections"""
        self._detections.append(detection)
        now = time.monotonic()

        while self._detections and (now - self._detections[0].when > self._DET_MAX_AGE):
            self._detections.popleft()

        self._lastUpdated = now

    def interpolate(self) -> Detection:
        """Predict where detection should be on the next frame"""
        current = self._detections[-1]

        if len(self._detections) == 1:
            return current

        # Keep it simple for now
        former = self._detections[-2]
        posDelta = former.getPosition() - current.getPosition()
        timeDelta = current.when - former.when
        newPos = current.getPosition() + posDelta * timeDelta * self._INTERP_SCALE

        return Detection(
            self.id,
            current.confidence,
            ScreenCoord(
                newPos.x - current.width / 2,
                newPos.y - current.height / 2,
            ),
            ScreenCoord(
                newPos.x + current.width / 2,
                newPos.y + current.height / 2,
            ),
        )


# Additional simple tracking layer, on top of the one we already have...
# Will hopefully make results more reliable
class Tracker:
    _TRACK_MAX_AGE = 0.2

    def __init__(self, screenSize: ScreenCoord) -> None:
        self._maxDist = math.sqrt(
            screenSize.x * screenSize.x + screenSize.y * screenSize.y
        )
        self._tracked = {}
        self._curId = 0

    @property
    def tracked(self) -> Iterable[TrackedDetection]:
        return self._tracked.values()

    def _score(self, tracked: TrackedDetection, candidate: Detection) -> float:
        """Returns a score in range [0, 1] reflecting how likely candidate is to belong
        to tracked.
        """
        # Only consider distance for now.
        result = 1 - (
            tracked.latest.getPosition().distanceTo(candidate.getPosition())
            / self._maxDist
        )
        assert 0 <= result <= 1

        return result

    def _findMatch(
        self, tracked: TrackedDetection, candidates: list[Detection]
    ) -> tuple[float, Detection, TrackedDetection]:
        bestScore = -1
        match = None

        for det in candidates:
            score = self._score(tracked, det)

            if score > bestScore:
                bestScore = score
                match = det

        return (bestScore, match, tracked)

    def update(self, detections: list[Detection]) -> None:
        # 1. Prune expired TrackedDetection instances
        now = time.monotonic()

        for key in [
            d.id
            for d in self._tracked.values()
            if now - d.lastUpdated > self._TRACK_MAX_AGE
        ]:
            del self._tracked[key]

        # 2. Update existing TrackedDetection instances
        # Loop, finding best match each time and removing corresponding detection and
        # TrackedDetection until we run out of either
        candidates = list(detections)
        tracked = list(self._tracked.values())

        while candidates and tracked:
            score, matchDet, matchTrack = sorted(
                [self._findMatch(t, candidates) for t in tracked],
                key=lambda tup: tup[0],
                reverse=True,
            )[0]
            candidates.remove(matchDet)
            tracked.remove(matchTrack)
            matchTrack.update(matchDet)

        # 3. Create new TrackedDetection for each remaining candidate
        for det in candidates:
            # TODO: Periodically reset IDs, otherwise will rise indefinitely
            self._tracked[self._curId] = TrackedDetection(self._curId, det)
            self._curId += 1
