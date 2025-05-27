#!/usr/bin/env python3
"""
  input.py
  ========

  Description:           Handles user input devices (keyboard, mouse)
  Author:                Michael De Pasquale
  Creation Date:         2025-05-26
  Modification Date:     2025-05-27

"""

from collections import defaultdict
import fcntl
import logging
import os
from pathlib import Path
from typing import Callable

import libevdev
from libevdev import InputEvent

from model import ScreenCoord

# NOTE: You likely won't have permission to read /dev/input/*, which will cause
# _getKeyboards() to fail. To fix this, add yourself to the 'input' group:
# >usermod -a -G input $USER_NAME
# Restart or use newgrp for this to take effect!


class InputManager:
    def __init__(self, debug: bool = False) -> None:
        self._log = logging.getLogger(
            self.__class__.__module__ + "." + self.__class__.__qualname__
        )

        self._debug = debug
        self._buttonState = defaultdict(lambda: False)
        self._buttonChangedCb = {}

        self._devices = self._getDevices()

        self._mouse = libevdev.Device()
        self._mouse.name = "Real Mouse"  # everyone back to the base, partner
        self._mouse.enable(libevdev.EV_REL.REL_X)
        self._mouse.enable(libevdev.EV_REL.REL_Y)
        self._mouse.enable(libevdev.EV_KEY.BTN_LEFT)
        self._mouse.enable(libevdev.EV_KEY.BTN_RIGHT)
        self._uinput = self._mouse.create_uinput_device()
        self._log.debug(
            f"Created virtual mouse: {self._uinput.devnode} ({self._uinput.syspath})"
        )

    def isPressed(self, key: libevdev.EV_KEY) -> bool:
        """Return True if key is pressed, False otherwise."""
        # Note that the state is only recorded for keys we have seen before. A new key
        # might incorrectly yield False until the key is released and pressed again.
        return self._buttonState[key]

    def addKeyChangeCallback(
        self, key: libevdev.EV_KEY, cb: Callable[[bool], None]
    ) -> None:
        """Register a callback to be run when the state of key changes. Callback accepts
        a bool which is True if the key was pressed and False if released."""
        assert key not in self._buttonChangedCb
        self._buttonChangedCb[key] = cb

        # This is a button we care about now
        # pylint: disable=pointless-statement
        self._buttonState[key]

    def mouseMove(self, delta: ScreenCoord) -> None:
        """Perform relative mouse movement."""
        self._uinput.send_events(
            [
                InputEvent(libevdev.EV_REL.REL_X, int(delta.x)),
                InputEvent(libevdev.EV_REL.REL_Y, int(delta.y)),
                InputEvent(libevdev.EV_SYN.SYN_REPORT, 0),
            ]
        )

    def mouseClick(self) -> None:
        """Left click the mouse."""
        self._uinput.send_events(
            [
                InputEvent(libevdev.EV_KEY.BTN_LEFT, 1),
                InputEvent(libevdev.EV_SYN.SYN_REPORT, 0),
                InputEvent(libevdev.EV_KEY.BTN_LEFT, 0),
                InputEvent(libevdev.EV_SYN.SYN_REPORT, 0),
            ]
        )

    def update(self) -> bool:
        """Process events from all keyboards, updating the recorded state for each of
        the keys we have seen before. Should be called once per loop. Does not block.
        """
        for device in self._devices:
            try:
                for event in device.events():
                    self._handleEvent(event)

            except libevdev.device.EventsDroppedException:
                self._log.exception("Events dropped! Processing dropped events...")

                for event in device.sync():
                    self._handleEvent(event)

    def _handleEvent(self, event: InputEvent) -> None:
        if event.code in self._buttonState:
            prev = self._buttonState[event.code]
            value = bool(event.value)
            self._buttonState[event.code] = value

            if value != prev and event.code in self._buttonChangedCb:
                self._log.debug(f"Button {event.code} changed to {value}")
                self._buttonChangedCb[event.code](value)

        if self._debug:
            if event.matches(libevdev.EV_SYN):
                self._log.debug(f"event {event.code.name}")

            else:
                self._log.debug(
                    f"event type {event.type.value:02x} {event.type.name}"
                    f" code {event.code.value:03x} {event.code.name} value {event.value:4d}"
                )

    def _getDevices(self) -> list[libevdev.Device]:
        """Open all input devices in non-blocking mode. Returns a list of Device."""
        result = []
        names = set()

        for path in Path("/dev/input/").glob("event*"):
            fd = open(path, "rb")
            fcntl.fcntl(fd, fcntl.F_SETFL, os.O_NONBLOCK)
            device = libevdev.Device(fd)

            if device.name in names:
                self._log.warning(f"Ignoring duplicate device '{device.name}'")
                fd.close()

                continue

            names.add(device.name)
            self._log.debug(f"Found device '{device.name}'")
            result.append(device)

        return result
