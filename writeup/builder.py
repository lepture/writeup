#!/usr/bin/env python
# coding: utf-8
"""
    writeup.builder
    ~~~~~~~~~~~~~~~

    Load configuration, source and build the site.

    :copyright: (c) 2013 by Hsiaoming Yang
"""

import os
import re
import pytz
import hashlib
import datetime
from . import parser
from .cache import Cache
from ._compat import to_unicode
from .utils import is_markdown, is_subdir, is_html
from .utils import fwrite, fcopy, fwalk


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
        self.sitedir = os.path.join(
            self.source, config.get('sitedir', '_site')
        )
        self.config = config

        self.cache = Cache(config.get('cachedir', None))

        # initialize jinja environment
        jinja = create_jinja(**config)
        site = config.copy()

        site['posts'] = self.iters
        site['tags'] = lambda: self.cache.get('_tags', {})

        tz = pytz.timezone(config.get('timezone', 'Asia/Chongqing'))
        site['now'] = tz.localize(datetime.datetime.now())

        jinja.globals.update({
            'site': site,
            'static_url': self.static_url,
        })
        self.jinja = jinja

    def static_url(self, filepath, url=None):
        """Generate static url."""
        if not url:
            url = '/' + filepath

        key = '_static_%s' % filepath
        value = self.cache.get(key)

        if not value:
            abspath = os.path.join(self.source, filepath)
            with open(abspath, 'r') as f:
                content = f.read()
            value = hashlib.md5(content).hexdigest()[:5]
            self.cache.set(key, value)
        return '%s?v=%s' % (url, value)

    def cached_items(self, is_page=False, subdirectory=None, reverse=True):
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

        items = sorted(items, key=lambda o: o[1], reverse=reverse)
        return items

    def iters(self, is_page=False, subdirectory=None, reverse=True,
              count=None):
        """Return an iterator for all posts."""
        items = self.cached_items(is_page, subdirectory, reverse)

        if count is not None:
            items = items[:count]

        keys = [o[0] for o in items]
        item_count = len(keys)

        for i, k in enumerate(keys):
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
        if is_page:
            type = 'page'
        else:
            type = 'post'
        post = parser.read(filepath, type=type, **self.config)
        if not post:
            return
        self.cache.set(filepath, post)
        if post.meta.get('status', 'publish') == 'draft':
            return post
        if not is_page and not post.date:
            # TODO: logging
            return
        # record tags
        tags = self.cache.get('_tags', {})
        if post.tags:
            for tag in post.tags:
                if tag in tags:
                    tags[tag] += 1
                else:
                    tags[tag] = 1
        self.cache.set('_tags', tags)

        key = '_%ss' % type
        index = self.cache.get(key) or {}
        index[filepath] = post.date
        self.cache.set(key, index)
        return post

    def load_posts(self):
        """Load and parse posts in post directory."""
        for filepath in fwalk(self.postsdir):
            if is_markdown(filepath):
                self.read(filepath)
            else:
                self.cache.add('_post_files', filepath)

    def load_pages(self):
        includes = set(self.config.get('includes', []))
        excludes = set(self.config.get('excludes', []))
        postsdir = self.config.get('postsdir', '_posts')
        if postsdir in includes:
            includes.remove(postsdir)
        if '_layouts' in includes:
            includes.remove('_layouts')

        for filepath in fwalk(self.source, includes, excludes):
            if is_markdown(filepath):
                self.read(filepath, 'page')
            else:
                self.cache.add('_page_files', filepath)

    def write(self, post, is_page=False):
        """Write a single post into HTML."""
        if is_page:
            dest = os.path.relpath(post.filepath, self.source)
            dest = os.path.splitext(dest)[0] + '.html'
        else:
            if post.url.endswith('/'):
                dest = post.url + 'index.html'
            elif post.url.endswith('.html'):
                dest = post.url
            else:
                dest = post.url + '.html'

        dest = os.path.join(self.sitedir, dest.lstrip('/'))

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

    def build_files(self):
        """Build rest files to site directory."""

        sitedir = self.sitedir

        def build_html(filepath, dest):
            with open(filepath, 'r') as f:
                tpl = self.jinja.from_string(to_unicode(f.read()))
            content = tpl.render()
            fwrite(dest, content)

        def build_paginator(filepath, dest):
            with open(filepath, 'r') as f:
                tpl = self.jinja.from_string(to_unicode(f.read()))

            relpath = os.path.relpath(filepath, self.postsdir)
            dirname = os.path.dirname(relpath) or None

            root = os.path.relpath(dest, self.sitedir)
            root = re.sub(r'index.html$', '', root)
            root = root.replace('\\', '/')
            if root == '.':
                root = '/'
            else:
                root = '/' + root

            items = self.cached_items(subdirectory=dirname)
            paginator = Paginator(items, 1)
            paginator.per_page = self.config.get('per_page', 100)
            paginator._style = self.config.get(
                'paginator_style', 'page-:num'
            )
            paginator._root = root
            paginator._cache = self.cache

            # write current paginator
            content = tpl.render({'paginator': paginator})
            fwrite(dest, content)

            if paginator.pages > 1:
                for i in range(2, paginator.pages + 1):
                    paginator.page = i
                    url = paginator._style.replace(':num', str(i))
                    if url.endswith('/'):
                        url += 'index.html'
                    elif not url.endswith('.html'):
                        url += '.html'
                    new_dest = re.sub(r'index.html$', url, dest)
                    content = tpl.render({'paginator': paginator})
                    fwrite(new_dest, content)

        for filepath in self.cache.get('_post_files') or ():
            name = os.path.relpath(filepath, self.postsdir)
            dest = os.path.join(sitedir, name)

            if filepath.endswith('/index.html'):
                build_paginator(filepath, dest)
            elif is_html(filepath):
                build_html(filepath, dest)
            else:
                fcopy(filepath, dest)

        for filepath in self.cache.get('_page_files') or ():
            name = os.path.relpath(filepath, self.source)
            dest = os.path.join(sitedir, name)
            if is_html(filepath):
                build_html(filepath, dest)
            else:
                fcopy(filepath, dest)

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
    config.setdefault('excludes', [filepath])
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
        trim_blocks=True,
        lstrip_blocks=True,
        autoescape=False,
        extensions=[
            'jinja2.ext.do',
            'jinja2.ext.loopcontrols',
            'jinja2.ext.with_',
        ]
    )
    jinja.filters.update(dict(
        markdown=filters.markdown,
        xmldatetime=filters.xmldatetime,
        wordcount=filters.wordcount,
    ))

    jinja._last_updated = max((os.path.getmtime(d) for d in loaders))
    return jinja


class Paginator(object):
    """Paginator generator."""

    _cache = None
    _style = 'page-:num'
    _root = '/'

    per_page = 100

    def __init__(self, items, page):
        self.items = items
        self.page = page

    @property
    def total(self):
        return len(self.items)

    @property
    def pages(self):
        return int((self.total - 1) / self.per_page) + 1

    @property
    def has_prev(self):
        return self.page > 1

    @property
    def prev_num(self):
        return self.page - 1

    @property
    def prev_url(self):
        if self.prev_num == 1:
            return self._root
        ret = self._style.replace(':num', str(self.prev_num))
        return self._root + ret

    @property
    def has_next(self):
        return self.page < self.pages

    @property
    def next_num(self):
        return self.page + 1

    @property
    def next_url(self):
        ret = self._style.replace(':num', str(self.next_num))
        return self._root + ret

    @property
    def posts(self):
        start = (self.page - 1) * self.per_page
        end = self.page * self.per_page
        items = self.items[start:end]
        for k, _ in items:
            yield self._cache.get(k)
