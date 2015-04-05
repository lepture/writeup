# coding: utf-8

import os
from contextlib import contextmanager
from .globals import _top
from .utils import cached_property


class Application(object):
    def __init__(self, config=None, **kwargs):
        kwargs.setdefault('basedir', '.')
        kwargs.setdefault('postsdir', '_posts')
        kwargs.setdefault('sitedir', '_site')
        kwargs.setdefault('cachedir', '.cache')
        kwargs.setdefault('permalink', '/:dirname/:filename.html')

        if config is not None:
            kwargs.update(load_config(config))

        self.config = kwargs

    @cached_property
    def permalink(self):
        return self.config.get('permalink')

    @cached_property
    def basedir(self):
        return os.path.abspath(self.config.get('basedir'))

    @cached_property
    def postsdir(self):
        return os.path.abspath(self.config.get('postsdir'))

    @cached_property
    def sitedir(self):
        return os.path.abspath(self.config.get('sitedir'))

    @cached_property
    def cachedir(self):
        return os.path.abspath(self.config.get('sitedir'))

    @cached_property
    def jinja(self):
        # TODO: name
        layouts = self.config.get('layouts', '_layouts')
        includes = self.config.get('includes', '_includes')
        return create_jinja(layouts, includes)

    @contextmanager
    def create_context(self):
        _top.app = self
        yield
        del _top.app


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


def load_config(filepath='_config.yml'):
    """Load and parse configuration from a yaml file."""
    from yaml import load
    try:
        from yaml import CLoader as Loader
    except ImportError:
        from yaml import Loader

    with open(filepath, 'r') as f:
        return load(f, Loader)
