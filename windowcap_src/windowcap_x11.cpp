/*
  windowcap_x11.cpp
  =================

  Description:           Takes a screenshot of a window.
                         Adapted from richard-to's example here:
                         https://gist.github.com/richard-to/10017943#file-x11_screen_grab-cpp-L68
  Author:                Michael De Pasquale
  Creation Date:         2025-05-13
  Modification Date:     2025-05-25

*/

#include "windowcap_x11.hpp"

XWinInfo gWindowInfo = {
    .display = NULL,
    .target = 0
};

int selectWindow(unsigned int id)
{
    gWindowInfo.display = XOpenDisplay(NULL);
    gWindowInfo.target = (Window)id;

    if (XGetWindowAttributes(gWindowInfo.display, gWindowInfo.target, &gWindowInfo.targetAttrs) == BadWindow) {
        // We never get here, crashes if XGetWindowAttributes fails
        std::cerr << "Bad window ID: " << id << std::endl;
        gWindowInfo.target = 0;
        gWindowInfo.display = 0;

        return 1;
    }

    std::cerr << "Found target " << id << ", size " << gWindowInfo.targetAttrs.width
              << "x" << gWindowInfo.targetAttrs.height << std::endl;

    return 0;
}

// Copies OpenCV matrix to array. Updates size and returns pointer.
char* matToArray(cv::Mat mat, int& size)
{
    size = mat.total() * mat.elemSize();
    char* buf = new char[size];
    std::memcpy(buf, mat.data, size);

    return buf;
}

// Take a screenshot of a window whose title contains name, optionally in
// a specified region (if all of x, y, w, h are not -1)
// Returns a pointer to an array of size pixels (RGB) representing
// a width x height image
char* screenshot(int& size, int& width, int& height, int x, int y, int w, int h)
{
    if (x == -1 || y == -1 || w == -1 || h == -1) {
        // No region specified
        x = 0;
        y = 0;
        w = gWindowInfo.targetAttrs.width;
        h = gWindowInfo.targetAttrs.height;
    }

    width = w;
    height = h;

    if (!gWindowInfo.display || !gWindowInfo.target) {
        std::cerr << "selectWindow() either failed or was not called first!" << std::endl;

        return 0;
    }

    // std::cerr << "Taking screenshot: (" << x << ", " << y << ", " << w << ", " << h << ")" << std::endl;

    XImage* image = XGetImage(gWindowInfo.display, gWindowInfo.target, x, y, w, h, AllPlanes, ZPixmap);
    cv::Mat frame(height, width, CV_8UC4, image->data);
    cv::cvtColor(frame, frame, cv::COLOR_BGRA2RGB);

    XDestroyImage(image);

    return matToArray(frame, size);
}
