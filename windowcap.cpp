/*
  windowcap.cpp
  =============

  Description:           Python interface.
                         Adapted from https://docs.python.org/3/extending/extending.html
  Creation Date:         2025-05-13
  Modification Date:     2025-05-14

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

static PyObject* windowcap_screenshot_window(PyObject* self, PyObject* args)
{
    const char* name;
    int sts;

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

int main(int argc, char* argv[])
{
    PyStatus status;
    PyConfig config;
    PyConfig_InitPythonConfig(&config);
    PyObject* pmodule;

    // Add our module as a built-in, before Py_Initialize
    if (PyImport_AppendInittab(MODULE_NAME, PyInit_windowcap) == -1) {
        std::cerr << "Error: could not extend in-built modules table" << std::endl;

        return 1;
    }

    // Pass argv[0] to the Python interpreter
    status = PyConfig_SetBytesString(&config, &config.program_name, argv[0]);

    if (PyStatus_Exception(status)) {
        goto exception;
    }

    // Initialize the Python interpreter.
    status = Py_InitializeFromConfig(&config);

    if (PyStatus_Exception(status)) {
        goto exception;
    }

    PyConfig_Clear(&config);

    // Import the module
    pmodule = PyImport_ImportModule(MODULE_NAME);

    if (!pmodule) {
        PyErr_Print();
        std::cerr << "Error: could not import module '" << MODULE_NAME << "'"
                  << std::endl;
    }

    return 0;

exception:
    PyConfig_Clear(&config);
    Py_ExitStatusException(status);
}
