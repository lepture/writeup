#!/usr/bin/env python
# coding: utf-8
"""
    writeup.builder
    ~~~~~~~~~~~~~~~

    Load configuration, source and build the site.

    :copyright: (c) 2013 by Hsiaoming Yang
"""

import os
from . import parser
from .cache import Cache
from .utils import is_markdown, is_subdir, is_html
from .utils import fwrite, fcopy


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
        self.postsdir = os.path.join(
            self.source, config.get('postsdir', '_posts')
        )
        self.config = config

        self.cache = Cache(config.get('cachedir', None))

        # initialize jinja environment
        jinja = create_jinja(**config)
        site = config.copy()
        site['posts'] = self.iters
        jinja.globals.update({'site': site})
        self.jinja = jinja

    def iters(self, is_page=False, subdirectory=None, count=None):
        """Return an iterator for all posts."""

        if is_page:
            key = '_pages'
        else:
            key = '_posts'
        index = self.cache.get(key) or {}
        items = index.items()

        if subdirectory:
            # filter subdirectory
            subdir = os.path.join(self.source, subdirectory)
            if is_page:
                fn = lambda o: is_subdir(o[0], subdir)
            else:
                subpostdir = os.path.join(self.postsdir, subdirectory)
                fn = lambda o: is_subdir(o[0], subdir) or \
                    is_subdir(o[0], subpostdir)

            items = filter(fn, items)

        items = sorted(items, key=lambda o: o[1], reverse=True)
        keys = [o[0] for o in items]
        item_count = len(keys)

        for i, k in enumerate(keys):

            if count is not None and i >= count:
                break

            post = self.cache.get(k)

            if not is_page:
                if i > 0:
                    post.previous = self.cache.get(keys[i-1])
                else:
                    post.previous = None

                if i < item_count - 1:
                    post.next = self.cache.get(keys[i+1])
                else:
                    post.next = None

            yield post

    def read(self, filepath, is_page=False):
        """Read and index a single post."""
        mtime = self.cache.mtime(filepath)
        if mtime and mtime > os.path.getmtime(filepath):
            # cache is fresh
            return

        post = parser.read(filepath, **self.config)
        self.cache.set(filepath, post)

        if is_page:
            key = '_pages'
        else:
            key = '_posts'
        index = self.cache.get(key) or {}
        index[filepath] = post.date
        self.cache.set(key, index)
        return post

    def load_posts(self):
        """Load and parse posts in post directory."""
        for root, dirs, files in os.walk(self.postsdir):
            for name in dirs:
                if name.startswith('.'):
                    dirs.remove(name)
                elif name.startswith('_'):
                    dirs.remove(name)

            for f in files:
                filepath = os.path.join(root, f)
                if is_markdown(f):
                    self.read(filepath)
                else:
                    self.cache.add('_post_files', filepath)

    def load_pages(self):
        includes = set(self.config.get('include', []))
        postsdir = self.config.get('postsdir', '_posts')
        if postsdir in includes:
            includes.remove(postsdir)
        if '_layouts' in includes:
            includes.remove('_layouts')

        for root, dirs, files in os.walk(self.source):
            for name in dirs:
                if name.startswith('.'):
                    dirs.remove(name)
                elif name.startswith('_') and name not in includes:
                    dirs.remove(name)

            for f in files:
                filepath = os.path.join(root, f)
                if is_markdown(f):
                    self.read(filepath, 'page')
                else:
                    self.cache.add('_page_files', filepath)

    def write(self, post, is_page=False):
        """Write a single post into HTML."""
        if is_page:
            dest = os.path.join(post.dirname, post.filename) + '.html'
        else:
            if post.url.endswith('/'):
                dest = post.url + 'index.html'
            elif post.url.endswith('.html'):
                dest = post.url
            else:
                dest = post.url + '.html'

        sitedir = self.config.get('sitedir', '_site')
        dest = os.path.join(sitedir, dest.lstrip('/'))

        if not self.config.get('force') and os.path.exists(dest):
            post_time = os.path.getmtime(post.filepath)
            dest_time = os.path.getmtime(dest)
            if max(self.jinja._last_updated, post_time) < dest_time:
                # this is an old post
                return

        params = {'page': post}
        template = post.template or 'post.html'
        tpl = self.jinja.get_template(template)
        content = tpl.render(params)
        fwrite(dest, content)

    def build_posts(self):
        """Build posts to HTML."""
        for post in self.iters():
            self.write(post)

    def build_pages(self):
        """Build pages to HTML."""
        for post in self.iters(is_page=True):
            self.write(post, is_page=True)

    def _build_paginator(self, filepath):
        pass

    def _build_html(self, filepath, dest):
        tpl = self.jinja.get_template(filepath)
        content = tpl.render()
        fwrite(dest, content)

    def build_files(self):
        """Build rest files to site directory."""

        sitedir = self.config.get('sitedir', '_site')

        for filepath in self.cache.get('_post_files') or ():
            if filepath.endswith('/index.html'):
                self._build_paginator(filepath)
            elif is_html(filepath):
                name = os.path.relpath(self.postsdir, filepath)
                self._build_html(filepath, os.path.join(sitedir, name))
            else:
                name = os.path.relpath(self.postsdir, filepath)
                fcopy(filepath, os.path.join(sitedir, name))

        for filepath in self.cache.get('_page_files') or ():
            if is_html(filepath):
                name = os.path.relpath(self.source, filepath)
                self._build_html(filepath, os.path.join(sitedir, name))
            else:
                name = os.path.relpath(self.source, filepath)
                fcopy(filepath, os.path.join(sitedir, name))

    def build(self):
        self.load_posts()
        self.load_pages()

        self.build_posts()
        self.build_pages()
        self.build_files()


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
    config.setdefault('sitedir', '_site')
    config.setdefault('permalink', '/:year/:filename.html')
    return config


def create_jinja(**kwargs):
    """Create jinja loader."""
    from jinja2 import Environment, FileSystemLoader
    from . import filters

    source = kwargs.get('source')
    loaders = []

    layoutsdir = os.path.join(source, '_layouts')
    if not os.path.exists(layoutsdir):
        raise RuntimeError('_layouts directory is required.')

    loaders.append(layoutsdir)

    includedir = os.path.join(source, '_includes')
    if os.path.exists(includedir):
        loaders.append(includedir)

    jinja = Environment(
        loader=FileSystemLoader(loaders),
        autoescape=False,
    )
    jinja.globals = {}

    jinja.filters.update(dict(
        markdown=filters.markdown,
    ))

    jinja._last_updated = max((os.path.getmtime(d) for d in loaders))
    return jinja
