#!/usr/bin/env python3
"""
  main.py
  =======

  Description:           Entry point
  Author:                Michael De Pasquale
  Creation Date:         2025-05-13
  Modification Date:     2025-05-13

"""

import sys

from PIL import Image

import windowcap


def main(*args) -> int:
    width, height, data = windowcap.screenshot_window("nvim")

    img = Image.frombytes("RGB", (width, height), data)
    img.save("screencap.png")

    print("Saved result to screencap.png")

    return 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv))
