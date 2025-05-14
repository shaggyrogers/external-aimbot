/*
  windowcap_x11.cpp
  =================

  Description:           Takes a screenshot of a window.
                         Taken from here with modifications:
                         https://gist.github.com/richard-to/10017943#file-x11_screen_grab-cpp-L68

*/

#include <iostream>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include <opencv2/imgproc/imgproc.hpp>

#include <X11/Xlib.h>
#include <X11/Xutil.h>

bool findTargetWindow(Display* display, Window& window, std::string name)
{
    bool found = false;
    Window rootWindow = RootWindow(display, DefaultScreen(display));
    Atom atom = XInternAtom(display, "_NET_CLIENT_LIST", true);
    Atom actualType;
    int format;
    unsigned long numItems;
    unsigned long bytesAfter;

    unsigned char* data = (unsigned char*)'\0';
    Window* list;
    char* windowName;

    int status = XGetWindowProperty(display, rootWindow, atom, 0L, ~0L, false,
        AnyPropertyType, &actualType, &format,
        &numItems, &bytesAfter, &data);
    list = (Window*)data;

    if (status >= Success && numItems) {
        for (int i = 0; i < numItems; ++i) {
            if (XFetchName(display, list[i], &windowName) > 0) {
                std::string windowNameStr(windowName);

                if (windowNameStr.find(name) == 0) {
                    window = list[i];
                    found = true;

                    break;
                }
            }
        }
    }

    XFree(windowName);
    XFree(data);

    return found;
}

// Converts
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
char* screenshot(char* name, int& size, int& width, int& height)
{
    Display* display = XOpenDisplay(NULL);
    Window rootWindow = RootWindow(display, DefaultScreen(display));
    Window targetWindow;

    XWindowAttributes targetWindowAttributes;

    if (findTargetWindow(display, targetWindow, name) == false) {
        std::cerr << "Error: Cannot find target window." << std::endl;

        return NULL;
    }

    XGetWindowAttributes(display, targetWindow, &targetWindowAttributes);

    width = targetWindowAttributes.width;
    height = targetWindowAttributes.height;

    XImage* image = XGetImage(display, targetWindow, 0, 0, width, height, AllPlanes, ZPixmap);
    cv::Mat frame(height, width, CV_8UC4, image->data);
    cv::cvtColor(frame, frame, cv::COLOR_BGRA2RGB);

    XFree(image);

    return matToArray(frame, size);
}
