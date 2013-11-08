#!/usr/bin/env python
# coding: utf-8
"""
    writeup.builder
    ~~~~~~~~~~~~~~~

    Load configuration, source and build the site.

    :copyright: (c) 2013 by Hsiaoming Yang
"""

import os
import copy
from . import parser
from .cache import Cache


class Builder(object):
    def __init__(self, **kwargs):
        if 'config' in kwargs:
            filepath = kwargs.pop('config')
        else:
            filepath = '_config.yml'

        if not os.path.exists(filepath):
            raise RuntimeError('Config file is missing.')

        config = load_config(filepath)
        config.update(kwargs)

        self.source = os.path.abspath(config.get('source', '.'))
        self.cache = Cache(config.get('cachedir', None))
        self.config = config

        self.jinja = create_jinja(**config)

    def read_post(self, filepath):
        """Read and index a single post."""
        mtime = self.cache.mtime(filepath)
        if mtime and mtime > os.path.getmtime(filepath):
            # cache is fresh
            return

        post = parser.read(filepath, **self.config)
        self.cache.set(filepath, post)
        if self.cache._cachedir:
            post = CachedPost(self.cache, post)

        # create index
        cache = self.cache.get('_posts', {})
        cache[post.id] = post
        self.cache.set('_posts', cache)
        return post

    def load_posts(self):
        """Load and parse posts in post directory."""
        source = os.path.join(
            self.source, self.config.get('postsdir', '_posts')
        )

        for root, dirs, files in os.walk(source):
            for name in dirs:
                if name.startswith('.'):
                    dirs.remove(name)
                elif name.startswith('_'):
                    dirs.remove(name)

            for f in files:
                filepath = os.path.join(root, f)
                ext = os.path.splitext(f)
                if ext in ('.md', '.mkd', '.markdown'):
                    # this is a markdown post
                    self.read_post(filepath)
                else:
                    self.cache.add('_posts_files', filepath)

    def load_pages(self):
        includes = set(self.config.get('include', []))
        includes.remove(self.config.get('postsdir', '_posts'))
        includes.remove('_layouts')

        for root, dirs, files in os.walk(self.source):
            for name in dirs:
                if name.startswith('.'):
                    dirs.remove(name)
                elif name.startswith('_') and name not in includes:
                    dirs.remove(name)

            for f in files:
                filepath = os.path.join(root, f)

    def write_post(self, post):
        """Write a single post into HTML."""

    def build_posts(self):
        """Build posts to HTML."""

    def build_pages(self):
        """Build pages to HTML."""

    def render(self, template, params):
        tpl = self.jinja.get_template(template)
        return tpl.render(params)

    def write(self, content, dest):
        pass

    def build(self):
        pass


class CachedPost(object):
    def __init__(self, cache, post):
        post.body = None
        self.__post = post
        self.__cache = cache

    def __getattr__(self, key):
        try:
            return object.__getattribute__(self.__post, key)
        except AttributeError:
            self.__post = self.__cache.get(self.__post.filepath)
            return object.__getattribute__(self.__post, key)

    def __getstate__(self):
        return self.__dict__

    def __setstate__(self, d):
        self.__dict__.update(d)


def load_config(filepath='_config.yml'):
    """Load and parse configuration from a yaml file."""
    from yaml import load
    try:
        from yaml import CLoader as Loader
    except ImportError:
        from yaml import Loader

    with open(filepath, 'r') as f:
        config = load(f, Loader)

    config.setdefault('postsdir', '_posts')
    config.setdefault('permalink', '/:year/:filename.html')
    return config


def create_jinja(**kwargs):
    """Create jinja loader."""
    from jinja2 import Environment, FileSystemLoader

    source = kwargs.get('source')
    loaders = [os.path.join(source, '_layout')]
    includedir = os.path.join(source, '_includes')
    if os.path.exists(includedir):
        loaders.append(includedir)

    jinja = Environment(
        loader=FileSystemLoader(loaders),
        autoescape=False,
    )
    return jinja
