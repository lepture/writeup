#!/usr/bin/env python
# coding: utf-8
"""
    writeup.parser
    ~~~~~~~~~~~~~~

    Parse a markdown file into a Post.

    :copyright: (c) 2013 by Hsiaoming Yang
"""

import os
import re
import unicodedata
import hoedown as m
from ._compat import to_unicode, to_datetime


def read(filepath, **kwargs):
    """Read a file and parse it to a post."""

    with open(filepath, 'r') as f:
        content = f.read()

    meta, body = parse(content)

    if 'status' in meta and meta['status'] == 'draft':
        return None

    meta['filepath'] = filepath
    return Post(body, meta, **kwargs)


def parse(text):
    """Parse a text and parse the meta data and content."""
    meta, body = re.split(r'\n---{3,}', text, 1)
    meta = parse_meta(to_unicode(text).strip())
    body = to_unicode(body).strip()
    return meta, body


def parse_meta(text):
    """Parse the meta part of an article.

    The meta part contains title, info, and description.
    """
    meta = {}
    html = m.html(text)
    titles = re.findall(r'^<h1>(.*)</h1>', html)
    if not titles:
        meta[u'title'] = None
    else:
        meta[u'title'] = titles[0]

    items = re.findall(r'<li>(.*?)</li>', html, re.S)
    for item in items:
        key, value = item.split(':', 1)
        meta[key.rstrip()] = value.lstrip()

    desc = re.findall(r'<p>(.*?)</p>', html, re.S)
    if desc:
        meta[u'description'] = '\n\n'.join(desc)

    return meta


def slugify(s):
    """Make clean slug."""
    rv = []
    for c in unicodedata.normalize('NFKC', to_unicode(s)):
        cat = unicodedata.category(c)[0]
        if cat in 'LN' or c in '-_~':
            rv.append(c)
        if cat == 'Z':
            rv.append(' ')
    new = ''.join(rv).strip()
    new = re.sub('[-\s]+', '-', new)
    return new.lower()


def permalink(post, style):
    """Generate permalink by the given style.

    A style is defined in _config.yml, an example::

        /:year/:filename.html
    """
    pattern = re.compile(r':\w+')
    keys = pattern.findall(style)
    for key in keys:
        try:
            repl = getattr(post, key[1:])
            style = style.replace(key, slugify(repl))
        except AttributeError:
            pass
    return style


class Post(object):
    def __init__(self, body, meta, **kwargs):
        if 'filepath' not in meta:
            raise ValueError('filepath is not in meta')

        self.body = body
        self.title = meta.pop('title', None)
        self.description = meta.pop('description', None)

        if 'date' in meta:
            self.date = to_datetime(meta.pop('date'))
            self.year = self.date.year
            self.month = self.date.month
            self.day = self.date.day
            self.type = 'post'
        else:
            self.type = 'page'

        self.meta = meta
        self._config = kwargs

    def __getattr__(self, key):
        try:
            object.__getattribute__(self, key)
        except AttributeError:
            value = self.meta.get(key)
            if not value:
                raise AttributeError('No such attribute: %s' % key)
            return value

    @property
    def id(self):
        return u'-'.join((self.dirname.replace('/', '-'), self.filename))

    @property
    def filename(self):
        if 'filename' not in self.meta:
            filepath = self.meta['filepath']
            basename = os.path.basename(filepath)
            self.meta['filename'] = os.path.splitext(basename)[0]
        return self.meta['filename']

    @property
    def dirname(self):
        source = self._config.get('source', '_posts')
        filepath = self.meta['filepath']
        relative = os.path.relpath(
            os.path.abspath(filepath),
            os.path.abspath(source),
        )
        if relative.startswith('..'):
            raise RuntimeError('Parse error for dirname.')
        return os.path.dirname(relative)

    @property
    def url(self):
        if 'url' not in self.meta:
            style = self._config.get(
                'permalink', '/:year/:filename.html'
            )
            self.meta['url'] = permalink(self, style)
        return self.meta['url']

    @property
    def tags(self):
        return self.meta.get('tags', '').split()
