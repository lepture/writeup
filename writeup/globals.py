# coding: utf-8

import threading
from .utils import cached_property

_top = threading.local()


class _Proxy(object):
    def __init__(self, ident):
        self._ident = ident

    @cached_property
    def _obj(self):
        return object.__getattribute__(_top, self._ident)

    def __getattr__(self, name):
        if name == '__members__':
            return dir(self._obj)
        return object.__getattribute__(self._obj, name)

    def __setattr__(self, name, value):
        if name.startswith('_'):
            return super(_Proxy, self).__setattr__(name, value)
        return setattr(self._obj, name, value)

    def __delattr__(self, name):
        return delattr(self._obj, name)

    def __setitem__(self, key, value):
        self._obj[key] = value

    def __delitem__(self, key):
        del self._obj[key]

    __str__ = lambda x: str(x._obj)
    __repr__ = lambda x: repr(x._obj)
    __getitem__ = lambda x, i: x._obj[i]


current_app = _Proxy('app')
request = _Proxy('request')
