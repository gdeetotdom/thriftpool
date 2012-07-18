import os


__all__ = ['set_exc_info']


cdef extern from "Python.h":
    struct PyObject:
        pass
    ctypedef PyObject* PyObjectPtr "PyObject*"
    void   Py_INCREF(PyObjectPtr)
    void   Py_DECREF(PyObjectPtr)
    void   Py_XDECREF(PyObjectPtr)
    int    Py_ReprEnter(PyObjectPtr)
    void   Py_ReprLeave(PyObjectPtr)
    int    PyCallable_Check(PyObjectPtr)


cdef extern from "frameobject.h":
    ctypedef struct PyThreadState:
        PyObjectPtr exc_type
        PyObjectPtr exc_value
        PyObjectPtr exc_traceback
    PyThreadState* PyThreadState_GET()


def set_exc_info(object type, object value):
    cdef PyThreadState* tstate = PyThreadState_GET()
    Py_XDECREF(tstate.exc_type)
    Py_XDECREF(tstate.exc_value)
    Py_XDECREF(tstate.exc_traceback)
    if type is None:
        tstate.exc_type = NULL
    else:
        Py_INCREF(<PyObjectPtr>type)
        tstate.exc_type = <PyObjectPtr>type
    if value is None:
        tstate.exc_value = NULL
    else:
        Py_INCREF(<PyObjectPtr>value)
        tstate.exc_value = <PyObjectPtr>value
    tstate.exc_traceback = NULL
