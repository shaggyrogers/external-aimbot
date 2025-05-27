#!/usr/bin/env python3
"""
  ui.py
  =====

  Description:           Draws the overlay
  Author:                Michael De Pasquale
  Creation Date:         2025-05-27
  Modification Date:     2025-05-27

"""

import time
from typing import Iterable, Union

from input_manager import InputManager
from model import Detection, ScreenCoord
from screen_mask import ScreenMask


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


class Menu:
    class ToggleItem:
        def __init__(
            self, name: str, button: "libevdev.EV_KEY", enabled: bool = True
        ) -> None:
            self.name = name
            self.button = button
            self.enabled = enabled

    def __init__(self, inputMgr: InputManager) -> None:
        self._items = {}
        self._inputMgr = inputMgr

    def __getitem__(self, name: str) -> bool:
        """Check if a menu item is enabled by name"""
        return self._items[name].enabled

    def addItem(self, *args, **kwargs) -> None:
        """Add toggle menu item"""
        item = self.ToggleItem(*args, **kwargs)
        self._items[item.name] = item

        def _update_item(state: bool) -> None:
            if state:
                item.enabled = not item.enabled

        self._inputMgr.addKeyChangeCallback(item.button, _update_item)

    @property
    def items(self) -> Iterable["Menu.ToggleItem"]:
        return self._items.values()


class UI:
    def __init__(self, menu: Menu) -> None:
        self._menu = menu
        self._frameCounter = FrameCounter()

    def _drawMenuItems(self, overlay: object) -> None:
        pos = ScreenCoord(128, 16)

        # TODO: Make these look nice
        for item in self._menu.items:
            overlay.addText(
                f"{item.name} {'On' if item.enabled else 'Off'}",
                pos.x,
                pos.y,
                24,
                1,
                0.2,
                0.3,
                1 if item.enabled else 0.75,
                False,
            )
            pos = ScreenCoord(pos.x + 160, pos.y)

    def draw(
        self,
        overlay: object,
        screenSize: tuple[int, int],
        region: tuple[int, int, int, int],
        detections: list[Detection],
        target: Union[Detection, None],
        screenMask: Union[ScreenMask, None] = None,
        triggerBoxes: bool = False,
    ) -> None:
        # CHECK: Can probably just import overlay instead of passing as argument?
        overlay.clear()
        overlay.addText(f"FPS: {self._frameCounter.fps}", 16, 16, 24, 1, 0, 0, 1, False)
        self._drawMenuItems(overlay)

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

        if screenMask:
            for maskRegion in screenMask.regions:
                overlay.addRectangle(
                    maskRegion.xy1.x * screenSize[0],
                    maskRegion.xy1.y * screenSize[1],
                    maskRegion.xy2.x * screenSize[0],
                    maskRegion.xy2.y * screenSize[1],
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

            if triggerBoxes:
                triggerBox = det.getTriggerBox()
                overlay.addRectangle(
                    triggerBox[0].x,
                    triggerBox[0].y,
                    triggerBox[1].x,
                    triggerBox[1].y,
                    1,
                    0,
                    0,
                    0.2,
                    True,
                    1,
                )

        overlay.draw()
        self._frameCounter.increment()
