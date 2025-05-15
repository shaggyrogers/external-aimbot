/*
  windowcap.cpp
  =============

  Description:           Python interface.
                         Adapted from https://docs.python.org/3/extending/extending.html
  Creation Date:         2025-05-13
  Modification Date:     2025-05-15

*/

#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <iostream>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include "windowcap_x11.hpp"

#define MODULE_NAME "windowcap"

// TODO: avoid having to find window each time

static PyObject* windowcap_screenshot_window(PyObject* self, PyObject* args);

static PyMethodDef WindowcapMethods[] = {
    { "screenshot_window",
        windowcap_screenshot_window,
        METH_VARARGS,
        "Select window with title containing the given string." },
    { NULL, NULL, 0, NULL }
};

static struct PyModuleDef windowcapmodule = {
    PyModuleDef_HEAD_INIT,
    MODULE_NAME,
    "Captures window screenshots.",
    -1,
    WindowcapMethods
};

PyMODINIT_FUNC PyInit_windowcap(void)
{
    return PyModule_Create(&windowcapmodule);
}

// screenshot_window(name: str) -> Tuple[int, int, bytes]:
// Takes a screenshot of a window whose title contains name.
// Returns a tuple containing the image width, height and pixels (RGB)
// respectively
static PyObject* windowcap_screenshot_window(PyObject* self, PyObject* args)
{
    const char* name;

    if (!PyArg_ParseTuple(args, "s", &name)) {
        return NULL;
    }

    int size = 0, width = 0, height = 0;
    char* buf = screenshot((char*)name, size, width, height);

    if (!buf || size <= 0) {
        PyErr_SetString(PyExc_RuntimeError, "Failed to take screenshot!");

        return NULL;
    }

    PyObject* bytes = PyBytes_FromStringAndSize(buf, size);
    delete buf;

    return PyTuple_Pack(3, PyLong_FromLong(width), PyLong_FromLong(height), bytes);
}
