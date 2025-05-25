/*
  windowcap.cpp
  =============

  Description:           Python interface.
                         Adapted from https://docs.python.org/3/extending/extending.html
  Creation Date:         2025-05-13
  Modification Date:     2025-05-25

*/

#define PY_SSIZE_T_CLEAN
#include <Python.h>

#include "windowcap_x11.hpp"

#define MODULE_NAME "windowcap"

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

// screenshot(region: Optional[tuple[int, int, int, int]] = None) -> Tuple[int, int, bytes]:
// Takes a screenshot of the previously selected window, or optionally a given
// region thereof, provided as (x, y, w, h) where (x, y) is the top-left corner
// and (w, h) are the width and height of the region.
// Returns a tuple containing the image width, height and pixels (bytes, RGB) respectively
static PyObject* windowcap_screenshot(PyObject* self, PyObject* args)
{
    int rX = -1, rY = -1, rW = -1, rH = -1;

    if (!PyArg_ParseTuple(args, "|(iiii)", &rX, &rY, &rW, &rH)) {
        PyErr_SetString(PyExc_TypeError, "Too many arguments or invalid region (4-tuple expected)");

        return NULL;
    }

    int size = 0, width = 0, height = 0;
    char* buf = screenshot(size, width, height, rX, rY, rW, rH);

    if (!buf || size <= 0) {
        PyErr_SetString(PyExc_RuntimeError, "Failed to take screenshot!");
        std::cerr << "buf: " << buf << ", size: " << size << std::endl;

        return NULL;
    }

    // Use PyTuple_New, since PyTuple_Pack increments reference counts.
    PyObject* result = PyTuple_New(3);
    PyTuple_SetItem(result, 0, PyLong_FromLong(width));
    PyTuple_SetItem(result, 1, PyLong_FromLong(height));
    PyTuple_SetItem(result, 2, PyBytes_FromStringAndSize(buf, size));
    delete buf;

    return result;
}
