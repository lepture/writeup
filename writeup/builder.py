# coding: utf-8

"""
    writeup.builder
    ~~~~~~~~~~~~~~~

    Load configuration, source and build the site.

    :copyright: (c) 2013 - 2015 by Hsiaoming Yang
"""

import os
import logging
from .request import Request
from ._compat import to_unicode


logger = logging.getLogger('writeup')


class Builder(object):
    def __init__(self, app):
        self.app = app

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

    @staticmethod
    def write(content, dest):
        # TODO
        return


class PostBuilder(Builder):
    def build(self, filepath):
        req = Request(filepath)
        dest = self.get_destination(req)
        if not dest:
            return
        template = req.template or 'post.html'
        tpl = self.app.jinja.get_template(template)
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
    def get_destination(self, filepath):
        if self.app.postsdir in filepath:
            dest = os.path.relpath(filepath, self.app.postsdir)
        else:
            dest = os.path.relpath(filepath, self.app.basedir)
        return os.path.join(self.app.sitedir, dest)

    def build_html(self, filepath):
        dest = self.get_destination(filepath)
        with open(filepath, 'rb') as f:
            tpl = self.app.jinja.from_string(to_unicode(f.read()))
        content = tpl.render()
        self.write(content, dest)

    def run(self):
        for filepath in self.app.file_indexer.keys():
            if filepath.endswith('/index.html'):
                self.build_paginator(filepath)
            elif filepath.endswith('.html') or filepath.endswith('.xml'):
                self.build_html(filepath)
            else:
                self.build_asset(filepath)
