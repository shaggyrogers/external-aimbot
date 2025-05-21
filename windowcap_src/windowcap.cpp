/*
  windowcap.cpp
  =============

  Description:           Python interface.
                         Adapted from https://docs.python.org/3/extending/extending.html
  Creation Date:         2025-05-13
  Modification Date:     2025-05-19

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

static PyObject* windowcap_select_window(PyObject* self, PyObject* args);
static PyObject* windowcap_screenshot(PyObject* self, PyObject* args);

static PyMethodDef WindowcapMethods[] = {
    { "selectWindow",
        windowcap_select_window,
        METH_VARARGS,
        "Initialise and select target window with the given ID." },
    { "screenshot",
        windowcap_screenshot,
        METH_VARARGS,
        "Takes a screenshot of the target window." },
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

// selectWindow(int id) -> int:
// Initialise and select the target window. Get ID from xwininfo.
// Returns 0 if successful, or a non-zero value otherwise.
static PyObject* windowcap_select_window(PyObject* self, PyObject* args)
{
    unsigned int id;

    if (!PyArg_ParseTuple(args, "I", &id)) {
        PyErr_SetString(PyExc_TypeError, "Unable to parse arguments");

        return NULL;
    }

    return PyLong_FromLong(selectWindow(id));
}

// screenshot() -> Tuple[int, int, bytes]:
// Takes a screenshot of the previously selected window.
// Returns a tuple containing the image width, height and pixels (bytes, RGB) respectively
static PyObject* windowcap_screenshot(PyObject* self, PyObject* args)
{
    if (!PyArg_ParseTuple(args, "")) {
        PyErr_SetString(PyExc_TypeError, "Unexpected argument(s)");

        return NULL;
    }

    int size = 0, width = 0, height = 0;
    char* buf = screenshot(size, width, height);

    if (!buf || size <= 0) {
        PyErr_SetString(PyExc_RuntimeError, "Failed to take screenshot!");

        return NULL;
    }

    PyObject* bytes = PyBytes_FromStringAndSize(buf, size);
    delete buf;

    return PyTuple_Pack(3, PyLong_FromLong(width), PyLong_FromLong(height), bytes);
}
