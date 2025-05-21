/*
  windowcap_x11.cpp
  =================

  Description:           Takes a screenshot of a window.
                         Adapted from richard-to's example here:
                         https://gist.github.com/richard-to/10017943#file-x11_screen_grab-cpp-L68
  Author:                Michael De Pasquale
  Creation Date:         2025-05-13
  Modification Date:     2025-05-21

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

// Take a screenshot of a window whose title contains name.
// Returns a pointer to an array of size pixels (RGB) representing
// a width x height image
char* screenshot(int& size, int& width, int& height)
{
    if (!gWindowInfo.display || !gWindowInfo.target) {
        std::cerr << "selectWindow() either failed or was not called first!" << std::endl;

        return 0;
    }

    width = gWindowInfo.targetAttrs.width;
    height = gWindowInfo.targetAttrs.height;

    XImage* image = XGetImage(gWindowInfo.display, gWindowInfo.target, 0, 0, width, height, AllPlanes, ZPixmap);
    cv::Mat frame(height, width, CV_8UC4, image->data);
    cv::cvtColor(frame, frame, cv::COLOR_BGRA2RGB);

    XFree(image);

    return matToArray(frame, size);
}
