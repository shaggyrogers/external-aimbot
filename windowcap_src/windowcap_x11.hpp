/*
  windowcap_x11.hpp
  =================

  Description:           Header for windowcap_x11.cpp
  Author:                Michael De Pasquale
  Creation Date:         2025-05-13
  Modification Date:     2025-05-25

*/

#ifndef __WINDOWCAP_X11_H__
#define __WINDOWCAP_X11_H__

#include <iostream>

#include <opencv2/imgproc/imgproc.hpp>

#include <X11/Xlib.h>
#include <X11/Xutil.h>

struct XWinInfo {
    Display* display;
    Window target;
    XWindowAttributes targetAttrs;
};
extern XWinInfo gWindowInfo;

int selectWindow(unsigned int id);
char* screenshot(int& size, int& width, int& height, int x = -1, int y = -1, int w = -1, int h = -1);

#endif // __WINDOWCAP_X11_H__
