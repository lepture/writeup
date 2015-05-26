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
from .utils import _top
from .request import Request
from ._compat import to_unicode, to_bytes


logger = logging.getLogger('writeup')


class Builder(object):
    def __init__(self, app):
        self.app = app
        self.write_count = 0
        self.build_count = 0

    @contextmanager
    def create_context(self, req):
        _top.request = req
        yield
        del _top.request

    def write(self, content, dest):
        """Write given content to the destination."""
        self.write_count += 1

        # make sure the directory exists
        folder = os.path.split(dest)[0]
        if not os.path.isdir(folder):
            os.makedirs(folder)

        with open(dest, 'wb') as f:
            f.write(to_bytes(content))

    def log_build(self, func, filepath):
        try:
            func(filepath)
        except Exception as e:
            logger.error('BUILDING ERROR %r' % e)


class PostBuilder(Builder):
    def get_html_destination(self, url):
        if url.endswith('/'):
            url += 'index.html'
        elif not url.endswith('.html'):
            url += '.html'
        return os.path.join(self.app.sitedir, url.lstrip('/'))

    def get_destination(self, req):
        dest = self.get_html_destination(req.url)
        mtime = max(self.app.jinja._mtime, req.mtime)
        if os.path.isfile(dest) and os.path.getmtime(dest) > mtime:
            return None
        return dest

    def build_redirect(self, redirect_from, req):
        logger.debug('building [redirect]: %s -> %s' % (
            redirect_from, req.url))
        dest = self.get_html_destination(redirect_from)
        html = (
            '<html><head><title>%(title)s</title>'
            '<meta http-equiv="refresh" content="0; url=%(url)s">'
            '<link rel="canonical" href="%(url)s">'
            '<script>location.href="%(url)s"</script>'
            '</head></html>'
        ) % {'title': req.title, 'url': req.full_url}
        self.write(html, dest)

    def build(self, filepath):
        self.build_count += 1
        req = Request(filepath)
        logger.debug('building [%s]: %s' % (req.file_type, req.relpath))
        dest = self.get_destination(req)
        if not dest:
            return
        template = req.template or 'post.html'
        tpl = self.app.jinja.get_template(template)

        for redirect_from in req._data.get('redirect_from', []):
            self.build_redirect(redirect_from, req)

        with self.create_context(req):
            content = tpl.render({'page': req})
            self.write(content, dest)

    def run(self):
        logger.info('BUILDING POSTS')
        for filepath in self.app.post_indexer:
            self.log_build(self.build, filepath)
        logger.info('WRITTING %i/%i' % (self.write_count, self.build_count))


class PageBuilder(PostBuilder):
    def run(self):
        logger.info('BUILDING PAGES')
        for filepath in self.app.page_indexer:
            self.log_build(self.build, filepath)
        logger.info('WRITTING %i/%i' % (self.write_count, self.build_count))


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

        logger.info('BUILDING %s' % relpath)
        dest = os.path.join(self.app.sitedir, relpath)

        with open(filepath, 'rb') as f:
            source = to_unicode(f.read())
            if u'site.posts' not in source and os.path.isfile(dest):
                if os.path.getmtime(dest) > self.app.jinja._mtime:
                    # ignore building html file when it don't iter posts
                    return
            tpl = self.app.jinja.from_string(source)

        with self.create_context(Request(filepath)):
            content = tpl.render()
            self.write(content, dest)

    def build_paginator(self, filepath):
        with open(filepath, 'rb') as f:
            tpl = self.app.jinja.from_string(to_unicode(f.read()))

        name = os.path.relpath(filepath, self.app.postsdir)

        dirname = os.path.dirname(name) or None

        root = re.sub(r'index.html$', '', name)
        root = root.replace('\\', '/')
        if root == '.':
            root = '/'
        else:
            root = '/' + root

        if dirname:
            items = self.app.filter_post_files(dirname=dirname)
        else:
            items = self.app.post_indexer.keys()

        paginator = Paginator(items, 1, root=root)
        logger.info(
            'BUILDING %s [%i|%i]' % (name, paginator.pages, paginator.total)
        )
        paginator.per_page = self.app.config.get('paginate', 10)
        paginator.path = self.app.config.get('paginate_path', 'page/:num')

        with self.create_context(Request(filepath, url=paginator.url)):
            content = tpl.render({'paginator': paginator})
            self.write(content, paginator.create_dest(self.app.sitedir))

        if paginator.pages < 2:
            return

        for i in range(2, paginator.pages + 1):
            paginator.page = i
            with self.create_context(Request(filepath, url=paginator.url)):
                content = tpl.render({'paginator': paginator})
                self.write(content, paginator.create_dest(self.app.sitedir))

    def build_asset(self, filepath):
        if self.app.postsdir in filepath:
            # ignore assets in posts dir
            return

        if not os.path.exists(filepath):
            del self.app.file_indexer[filepath]
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
        logger.info('BUILDING FILES')
        for filepath in self.app.file_indexer:
            self.build(filepath)


class Paginator(object):
    """Paginator generator."""

    path = 'page-:num'
    per_page = 10

    def __init__(self, items, page, root='/'):
        self.items = items
        self.page = page
        self.root = root

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
            return self.root
        rv = self.path.replace(':num', str(num))
        return self.root + rv

    def create_dest(self, sitedir):
        dest = self.url.lstrip('/')
        if dest.endswith('/'):
            dest += 'index.html'
        elif not dest.endswith('.html'):
            dest += '.html'
        return os.path.join(sitedir, dest)

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
        for k in items:
            yield Request(k)
