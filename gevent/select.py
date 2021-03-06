# Copyright (c) 2009-2011 Denis Bilenko. See LICENSE for details.
from __future__ import absolute_import
from gevent.event import Event
from gevent.hub import get_hub
from gevent.hub import integer_types
from gevent.hub import PY3

__implements__ = ['select']
__all__ = ['error'] + __implements__

import select as __select__
error = __select__.error


def get_fileno(obj):
    try:
        fileno_f = obj.fileno
    except AttributeError as ex:
        if PY3:
            ex.__traceback__ = None
        if not isinstance(obj, integer_types):
            raise TypeError('argument must be an int, or have a fileno() method: %r' % (obj, ))
        return obj
    else:
        return fileno_f()


class SelectResult(object):

    __slots__ = ['read', 'write', 'event']

    def __init__(self):
        self.read = []
        self.write = []
        self.event = Event()

    def add_read(self, socket):
        self.read.append(socket)
        self.event.set()

    def add_write(self, socket):
        self.write.append(socket)
        self.event.set()


def select(rlist, wlist, xlist, timeout=None):
    """An implementation of :meth:`select.select` that blocks only the current greenlet.

    Note: *xlist* is ignored.
    """
    watchers = []
    loop = get_hub().loop
    io = loop.io
    MAXPRI = loop.MAXPRI
    result = SelectResult()
    try:
        try:
            for readfd in rlist:
                watcher = io(get_fileno(readfd), 1)
                watcher.priority = MAXPRI
                watcher.start(result.add_read, readfd)
                watchers.append(watcher)
            for writefd in wlist:
                watcher = io(get_fileno(writefd), 2)
                watcher.priority = MAXPRI
                watcher.start(result.add_write, writefd)
                watchers.append(watcher)
        except IOError as ex:
            raise error(*ex.args)
        result.event.wait(timeout=timeout)
        return result.read, result.write, []
    finally:
        for watcher in watchers:
            watcher.stop()
