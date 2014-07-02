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
import pytz
import yaml
import unicodedata
import mistune as m
from ._compat import to_unicode, to_datetime

rules = m.BlockGrammar()


def read(filepath, **kwargs):
    """Read a file and parse it to a post."""

    with open(filepath, 'r') as f:
        content = f.read()

    try:
        meta, body = parse(content)
    except:
        return None

    if 'status' in meta and meta['status'] == 'draft':
        return None

    meta['filepath'] = filepath
    return Post(body, meta, **kwargs)


def parse(text):
    """Parse a text and parse the meta data and content."""
    meta, body = re.split(r'\n-{3,}', to_unicode(text), 1)
    meta = parse_meta(to_unicode(meta).strip())
    body = to_unicode(body).strip()
    return meta, body


def parse_meta(text):
    """Parse the meta part of an article.

    The meta part contains title, info, and description
    """
    meta = {}

    # parse title
    m = rules.heading.match(text)
    if m:
        title = m.group(2)
        text = text[len(m.group(0)):]
    else:
        m = rules.lheading.match(text)
        if m:
            title = m.group(1)
            text = text[len(m.group(0)):]
        else:
            title = None
    meta['title'] = title

    # parse meta data
    m = rules.list_block.match(text)
    if m:
        values = yaml.load(m.group(0))
        for item in values:
            for key in item:
                meta[key] = item[key]
        text = text[len(m.group(0)):]

    # the rest part is the description
    meta['description'] = text
    return meta


def slugify(s):
    """Make clean slug."""
    rv = []
    for c in unicodedata.normalize('NFKC', to_unicode(s)):
        cat = unicodedata.category(c)[0]
        if cat in 'LN' or c in '-_~/':
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
    # make sure / is flat
    style = re.sub(r'\/{2,}', '/', style)
    return style


class Post(object):
    def __init__(self, body, meta, **kwargs):
        if 'filepath' not in meta:
            raise ValueError('filepath is not in meta')

        self.meta = meta
        self.body = body
        self.title = meta.pop('title', None)
        self.description = meta.pop('description', None)

        self.type = kwargs.get('type', 'post')
        self._config = kwargs

        if 'date' in meta:
            timezone = self.meta.get('timezone')
            if not timezone:
                timezone = kwargs.get('timezone', 'Asia/Chongqing')

            tz = pytz.timezone(timezone)
            date = tz.localize(to_datetime(meta.pop('date')))

            self.year = date.year
            self.month = date.month
            self.day = date.day
            self.date = date

    def __getattr__(self, key):
        try:
            return object.__getattribute__(self, key)
        except AttributeError:
            return self.meta.get(key, None)

    @property
    def id(self):
        if not self.dirname:
            return self.filename
        return u'-'.join((self.dirname.replace('/', '-'), self.filename))

    @property
    def filename(self):
        if 'filename' not in self.meta:
            basename = os.path.basename(self.filepath)
            self.meta['filename'] = os.path.splitext(basename)[0]
        return self.meta['filename']

    @property
    def dirname(self):
        source = os.path.abspath(self._config.get('source', '.'))
        if self.type == 'post':
            source = os.path.join(
                source, self._config.get('postsdir', '_posts')
            )
        relative = os.path.relpath(
            os.path.abspath(self.filepath),
            os.path.abspath(source),
        )
        if relative.startswith('..'):
            raise RuntimeError('Parse error for dirname.')
        dirname = os.path.dirname(relative)
        # unix path
        return dirname.replace('\\', '/')

    @property
    def url(self):
        if 'url' not in self.meta:
            style = self._config.get(
                'permalink', '/:year/:filename.html'
            )
            if self.type == 'post':
                self.meta['url'] = permalink(self, style)
            else:
                if self.dirname:
                    url = '/%s/%s' % (self.dirname, self.filename)
                else:
                    url = '/%s' % self.filename
                if style.endswith('.html'):
                    url += '.html'
                elif style.endswith('/'):
                    url += '/'
                # make sure url is flat
                self.meta['url'] = re.sub(r'\/{2,}', '/', url)
        return self.meta['url']

    @property
    def tags(self):
        tags = self.meta.get('tags', '')
        if isinstance(tags, (tuple, list)):
            return tags
        if not tags:
            return []
        return map(lambda o: o.strip(), tags.split(','))

    def __getstate__(self):
        return self.__dict__

    def __setstate__(self, d):
        self.__dict__.update(d)
