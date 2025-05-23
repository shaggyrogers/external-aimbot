#!/usr/bin/env python3
"""
  screen_mask.py
  ==============

  Description:           Filter out detections for certain parts of the screen.
  Author:                Michael De Pasquale
  Creation Date:         2025-05-22
  Modification Date:     2025-05-23

"""

from typing import Iterable

from model import Detection, ScreenCoord


class MaskRegion:
    def __init__(
        self, xy1: ScreenCoord, xy2: ScreenCoord, threshold: float = 0.9
    ) -> None:
        assert xy1 and xy2
        assert 0 <= threshold <= 1

        self._xy1 = xy1
        self._xy2 = xy2
        self._threshold = threshold

    @property
    def xy1(self) -> ScreenCoord:
        return self._xy1

    @property
    def xy2(self) -> ScreenCoord:
        return self._xy2

    def includes(self, screenSize: ScreenCoord, detection: Detection) -> bool:
        """Return True if the % area of detection falling within this region exceeds
        threshold.
        """
        fullArea = (detection.xy2 - detection.xy1).product()

        xy1 = self._xy1 * screenSize
        xy2 = self._xy2 * screenSize

        if (
            detection.xy1.x > xy2.x
            or detection.xy1.y > xy2.y
            or detection.xy2.x < xy1.x
            or detection.xy2.y < xy1.y
        ):
            # No intersection
            return False

        # Compute intersecting area
        xyInc1 = ScreenCoord(max(xy1.x, detection.xy1.x), max(xy1.y, detection.xy1.y))
        xyInc2 = ScreenCoord(min(xy2.x, detection.xy2.x), min(xy2.y, detection.xy2.y))
        incArea = (xyInc2 - xyInc1).product()

        if not (fullArea >= incArea >= 0):
            breakpoint()

        assert fullArea >= incArea >= 0

        return incArea / fullArea >= self._threshold


class ScreenMask:
    """Filter out detections that occur within a set of masked regions."""

    def __init__(self, regions: Iterable[MaskRegion]) -> None:
        self._regions = list(regions)

    @property
    def regions(self) -> object:
        return self._regions

    def filter(
        self, screenSize: tuple[int, int], detections: Iterable[Detection]
    ) -> list[Detection]:
        return list(self._filter(ScreenCoord(screenSize[0], screenSize[1]), detections))

    def _filter(
        self, screenSize: ScreenCoord, detections: Iterable[Detection]
    ) -> Iterable[Detection]:
        for d in detections:
            if any(map(lambda r: r.includes(screenSize, d), self._regions)):
                continue

            yield d
