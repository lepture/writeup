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
from .utils import fwrite, fcopy, fwalk, is_ignore_file
from .utils import Paginator


class Builder(object):
    def __init__(self, **kwargs):
        if 'config' in kwargs:
            filepath = kwargs.pop('config')
        else:
            filepath = '_config.yml'

        if not os.path.exists(filepath):
            raise RuntimeError('Config file is missing.')

        config = default_config(filepath)
        config.update(kwargs)

        self.basedir = os.path.abspath(config.get('basedir'))
        self.postsdir = os.path.abspath(config.get('postsdir'))
        self.sitedir = os.path.abspath(config.get('sitedir'))
        self.config = config

        self.cache = Cache(config.get('cachedir', None))

        # initialize jinja environment
        jinja = create_jinja(**config)
        site = config.copy()

        site['posts'] = self.posts
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
            abspath = os.path.join(self.basedir, filepath)
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
            subdir = os.path.join(self.basedir, subdirectory)
            if is_page:
                fn = lambda o: is_subdir(o[0], subdir)
            else:
                subpostdir = os.path.join(self.postsdir, subdirectory)
                fn = lambda o: is_subdir(o[0], subdir) or \
                    is_subdir(o[0], subpostdir)

            items = filter(fn, items)

        items = sorted(items, key=lambda o: o[1], reverse=reverse)
        return items

    def posts(self, is_page=False, subdirectory=None, reverse=True,
              count=None):
        """Return an iterator for all posts."""
        items = self.cached_items(is_page, subdirectory, reverse)

        if count is not None:
            items = items[:count]

        for item in items:
            yield self.cache.get(item[0])

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
            if is_ignore_file(os.path.relpath(filepath, self.postsdir)):
                continue
            if is_markdown(filepath):
                self.read(filepath)
            else:
                self.cache.add('_post_files', filepath)

    def recursive_meta(self, filepath):
        """Merge configuration recursively."""
        key = '_meta_%s' % filepath
        config = self.cache.get(key, None)
        if config is None:
            names = filepath.split(os.path.sep)
            names.reverse()
            dest = self.basedir
            config = {}
            while names:
                name = names.pop()
                dest = os.path.join(dest, name)
                config_file = os.path.join(dest, '_meta.yml')
                if os.path.isfile(config_file):
                    config.update(load_config(config_file))
            self.cache.set(key, config)
        return config

    def load_pages(self):
        includes = set(self.config.get('includes', []))
        excludes = set(self.config.get('excludes', []))
        postsdir = self.config.get('postsdir', '_posts')
        if postsdir in includes:
            includes.remove(postsdir)
        if '_layouts' in includes:
            includes.remove('_layouts')

        for filepath in fwalk(self.basedir, includes, excludes):
            if is_markdown(filepath):
                self.read(filepath, 'page')
            else:
                self.cache.add('_page_files', filepath)

    def write(self, post, is_page=False):
        """Write a single post into HTML."""
        if is_page:
            dest = os.path.relpath(post.filepath, self.basedir)
            dest = os.path.splitext(dest)[0] + '.html'
        else:
            if post.url.endswith('/'):
                dest = post.url + 'index.html'
            elif post.url.endswith('.html'):
                dest = post.url
            else:
                dest = post.url + '.html'

        dest = os.path.join(self.sitedir, dest.lstrip('/'))

        if not post.nocache and not self.config.get('force')\
           and os.path.exists(dest):
            post_time = os.path.getmtime(post.filepath)
            dest_time = os.path.getmtime(dest)
            if max(self.jinja._last_updated, post_time) < dest_time:
                # this is an old post
                return

        # merge meta to post
        dirname = os.path.dirname(
            os.path.relpath(post.filepath, self.basedir)
        )
        config = self.recursive_meta(dirname)
        for key in config:
            if getattr(post, key) is None:
                setattr(post, key, config[key])

        params = {'page': post}
        template = post.template or 'post.html'
        tpl = self.jinja.get_template(template)
        content = tpl.render(params)
        fwrite(dest, content)

    def build_posts(self):
        """Build posts to HTML."""
        for post in self.posts():
            self.write(post)

    def build_pages(self):
        """Build pages to HTML."""
        for post in self.posts(is_page=True):
            self.write(post, is_page=True)

    def build_files(self):
        """Build rest files to site directory."""

        sitedir = self.sitedir

        for filepath in self.cache.get('_post_files') or ():
            name = os.path.relpath(filepath, self.postsdir)
            dest = os.path.join(sitedir, name)

            if filepath.endswith('/index.html'):
                self.build_paginator(filepath, dest)
            elif is_html(filepath):
                self.build_html(filepath, dest)
            else:
                fcopy(filepath, dest)

        for filepath in self.cache.get('_page_files') or ():
            name = os.path.relpath(filepath, self.basedir)
            if is_ignore_file(name):
                continue
            dest = os.path.join(sitedir, name)
            if is_html(filepath):
                self.build_html(filepath, dest)
            else:
                fcopy(filepath, dest)

    def build_html(self, filepath, dest):
        with open(filepath, 'r') as f:
            tpl = self.jinja.from_string(to_unicode(f.read()))
        content = tpl.render()
        fwrite(dest, content)

    def build_paginator(self, filepath, dest):
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
        return load(f, Loader)


def default_config(filepath='_config.yml'):
    """Create default configuration for writeup."""
    config = load_config(filepath)
    config.setdefault('basedir', os.path.abspath('.'))
    config.setdefault('postsdir', os.path.abspath('_posts'))
    config.setdefault('sitedir', os.path.abspath('_site'))
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
        linguist=filters.linguist,
    ))

    jinja._last_updated = max((os.path.getmtime(d) for d in loaders))
    return jinja
