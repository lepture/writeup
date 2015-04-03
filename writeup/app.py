# coding: utf-8

import os
import threading
from .utils import cached_property

stack = threading.local()


class _Proxy(object):
    def __init__(self, ident):
        self._ident = ident

    @cached_property
    def _obj(self):
        return getattr(stack, self._ident)

    def __getattr__(self, name):
        if name == '__members__':
            return dir(self._obj)
        return getattr(self._obj, name)

    def __setitem__(self, key, value):
        self._obj[key] = value

    def __delitem__(self, key):
        del self._obj[key]

    __setattr__ = lambda x, n, v: setattr(x._obj, n, v)
    __delattr__ = lambda x, n: delattr(x._obj, n)
    __str__ = lambda x: str(x._obj)
    __repr__ = lambda x: repr(x._obj)
    __getitem__ = lambda x, i: x._obj[i]


current_app = _Proxy('app')
request = _Proxy('request')


class Application(object):
    def __init__(self, **kwargs):
        kwargs.setdefault('basedir', '.')
        kwargs.setdefault('postsdir', '_posts')
        kwargs.setdefault('sitedir', '_site')
        kwargs.setdefault('permalink', '/:dirname/:filename')

        self.config = kwargs

    @cached_property
    def basedir(self):
        return os.path.abspath(self.config.get('basedir'))

    @cached_property
    def postsdir(self):
        return os.path.abspath(self.config.get('postsdir'))

    @cached_property
    def sitedir(self):
        return os.path.abspath(self.config.get('sitedir'))

    def run(self):
        stack.app = self


class Request(object):
    def __init__(self, filename):
        self.filename = filename


class Builder(object):
    def __init__(self, app=None):
        if app is not None:
            self.app = app
        else:
            self.app = current_app

    @cached_property
    def jinja(self):
        # TODO
        return create_jinja()

    def iter_requests(self):
        raise NotImplementedError

    def build(self, req):
        raise NotImplementedError

    def run(self):
        for req in self.iter_requests():
            stack.request = req
            self.build(req)

        # clean request
        del stack.request


def create_jinja(layouts='_layouts', includes='_includes'):
    loaders = []

    if not os.path.exists(layouts):
        raise RuntimeError('%s directory is required.' % layouts)

    loaders.append(layouts)

    if os.path.exists(includes):
        loaders.append(includes)

    from jinja2 import Environment, FileSystemLoader
    jinja = Environment(
        loader=FileSystemLoader(loaders),
        trim_blocks=True,
        lstrip_blocks=True,
        autoescape=False,
        extensions=[
            'jinja2.ext.do',
            'jinja2.ext.loopcontrols',
            'jinja2.ext.with_',
        ]
    )

    from . import filters
    rv = {k: getattr(filters, k) for k in filters.__all__}
    jinja.filters.update(rv)

    jinja._last_updated = max((os.path.getmtime(d) for d in loaders))
    return jinja
