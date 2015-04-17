# coding: utf-8

"""
    writeup.builder
    ~~~~~~~~~~~~~~~

    Load configuration, source and build the site.

    :copyright: (c) 2013 - 2015 by Hsiaoming Yang
"""

import os
import re
import shutil
import logging
from contextlib import contextmanager
from .globals import _top
from .request import Request
from ._compat import to_unicode, to_bytes


logger = logging.getLogger('writeup')


class Builder(object):
    def __init__(self, app):
        self.app = app

    @contextmanager
    def create_context(self, req):
        _top.request = req
        yield
        del _top.request

    @staticmethod
    def write(content, dest):
        """Write given content to the destination."""
        # make sure the directory exists
        folder = os.path.split(dest)[0]
        if not os.path.isdir(folder):
            os.makedirs(folder)

        with open(dest, 'wb') as f:
            f.write(to_bytes(content))


class PostBuilder(Builder):
    def get_destination(self, req):
        dest = req.url
        if dest.endswith('/'):
            dest += 'index.html'
        elif not dest.endswith('.html'):
            dest += '.html'

        dest = os.path.join(self.app.sitedir, dest.lstrip('/'))
        if os.path.isfile(dest) and os.path.getmtime(dest) > req.mtime:
            return None
        return dest

    def build(self, filepath):
        req = Request(filepath)
        logger.debug('building [%s]: %s' % (req.post_type, req.relpath))
        dest = self.get_destination(req)
        if not dest:
            return
        template = req.template or 'post.html'
        tpl = self.app.jinja.get_template(template)

        with self.create_context(req):
            content = tpl.render({'page': req})
            self.write(content, dest)

    def run(self):
        for filepath in self.app.post_indexer.keys():
            self.build(filepath)


class PageBuilder(PostBuilder):
    def run(self):
        for filepath in self.app.page_indexer.keys():
            self.build(filepath)


class FileBuilder(Builder):
    def should_build_paginator(self, filepath):
        if self.app.postsdir not in filepath:
            return False
        return filepath.endswith('/index.html')

    def build_html(self, filepath):
        if self.app.postsdir in filepath:
            relpath = os.path.relpath(filepath, self.app.postsdir)
        else:
            relpath = os.path.relpath(filepath, self.app.basedir)

        logger.debug('building [html]: %s' % relpath)
        dest = os.path.join(self.app.sitedir, relpath)

        with open(filepath, 'rb') as f:
            tpl = self.app.jinja.from_string(to_unicode(f.read()))

        with self.create_context(Request(filepath)):
            content = tpl.render()
            self.write(content, dest)

    def build_paginator(self, filepath):
        with open(filepath, 'rb') as f:
            tpl = self.app.jinja.from_string(to_unicode(f.read()))

        name = os.path.relpath(filepath, self.app.postsdir)
        logger.debug('building [paginator]: %s' % name)

        dirname = os.path.dirname(name) or None

        dest = os.path.join(self.app.sitedir, name)
        root = re.sub(r'index.html$', '', name)
        root = root.replace('\\', '/')
        if root == '.':
            root = '/'
        else:
            root = '/' + root

        if dirname:
            items = list(self.app.post_indexer.filter(
                lambda o: o['dirname'] == dirname
            ))
        else:
            items = self.app.post_indexer.keys()

        paginator = Paginator(items, 1)
        paginator.per_page = self.app.config.get('perpage', 100)
        paginator._style = self.app.config.get('paginator_style', 'page-:num')
        paginator._root = root

        with self.create_context(Request(filepath, url=paginator.url)):
            content = tpl.render({'paginator': paginator})
            self.write(content, dest)

        if paginator.pages < 2:
            return

        for i in range(2, paginator.pages + 1):
            paginator.page = i
            url = paginator._style.replace(':num', str(i))
            if url.endswith('/'):
                url += 'index.html'
            elif not url.endswith('.html'):
                url += '.html'

            new_dest = re.sub(r'index.html$', url, dest)
            with self.create_context(Request(filepath, url=paginator.url)):
                content = tpl.render({'paginator': paginator})
                self.write(content, new_dest)

    def build_asset(self, filepath):
        if self.app.postsdir in filepath:
            # ignore assets in posts dir
            return
        name = os.path.relpath(filepath, self.app.basedir)
        dest = os.path.join(self.app.sitedir, name)

        source_time = os.path.getmtime(filepath)
        if os.path.exists(dest) and source_time <= os.path.getmtime(dest):
            return

        logger.debug('building [assets]: %s' % name)
        folder = os.path.split(dest)[0]
        if not os.path.isdir(folder):
            os.makedirs(folder)
        shutil.copy(filepath, dest)

    def build(self, filepath):
        if self.should_build_paginator(filepath):
            self.build_paginator(filepath)
        elif filepath.endswith('.html') or filepath.endswith('.xml'):
            self.build_html(filepath)
        else:
            self.build_asset(filepath)

    def run(self):
        for filepath in self.app.file_indexer.keys():
            self.build(filepath)


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

    def create_url(self, num):
        if num == 1:
            return self._root
        rv = self._style.replace(':num', str(num))
        return self._root + rv

    @property
    def url(self):
        return self.create_url(self.page)

    @property
    def prev_url(self):
        return self.create_url(self.prev_num)

    @property
    def has_next(self):
        return self.page < self.pages

    @property
    def next_num(self):
        return self.page + 1

    @property
    def next_url(self):
        return self.create_url(self.next_num)

    @property
    def posts(self):
        start = (self.page - 1) * self.per_page
        end = self.page * self.per_page
        items = self.items[start:end]
        for k, _ in items:
            yield Request(k)
