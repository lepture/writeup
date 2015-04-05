# coding: utf-8

import os
import re
import json
import pytz
from .parser import parse
from .globals import current_app
from .utils import cached_property, slugify, to_datetime


class Request(object):
    def __init__(self, filepath):
        self.filepath = filepath

    @cached_property
    def mtime(self):
        return os.path.getmtime(self.filepath)

    @cached_property
    def _cache_key(self):
        name = os.path.relpath(self.filepath).replace(os.path.sep, '.')
        return '%s-%s' % (name, self.mtime)

    @cached_property
    def _data(self):
        filepath = os.path.join(current_app.cachedir, self._cache_key)

        if os.path.exists(filepath):
            with open(filepath, 'rb') as f:
                return json.load(f)

        data = parse(self.filepath)
        if data is None:
            # TODO
            raise

        with open(filepath, 'wb') as f:
            json.dump(data, f)

        return data

    def __getattr__(self, key):
        try:
            return object.__getattribute__(self, key)
        except AttributeError:
            return self._data.get(key, None)

    def get_type(self):
        if current_app.postsdir not in self.filepath:
            return 'page'

        if 'status' in self._data and self._data['status'] == 'draft':
            return 'draft'

        if 'date' not in self._data:
            return 'invalid'

        return 'post'

    @cached_property
    def relpath(self):
        if current_app.postsdir in self.filepath:
            relpath = os.path.relpath(self.filepath, current_app.postsdir)
        else:
            relpath = os.path.relpath(self.filepath, current_app.basedir)

        if relpath.startswith('..'):
            raise RuntimeError('Parse error for relpath.')
        return relpath

    @cached_property
    def dirname(self):
        name = os.path.dirname(self.relpath)
        return name.replace('\\', '/')

    @cached_property
    def filename(self):
        if 'filename' in self._data:
            return self._data['filename']

        basename = os.path.basename(self.filepath)
        return os.path.splitext(basename)[0]

    @cached_property
    def url(self):
        if 'url' in self._data:
            return self._data['url']

        style = current_app.permalink
        if self.get_type() == 'post':
            return permalink(self, style)

        if self.dirname:
            url = '/%s/%s' % (self.dirname, self.filename)
        else:
            url = '/%s' % self.filename
        if style.endswith('.html'):
            url += '.html'
        elif style.endswith('/'):
            url += '/'
        # make sure url is flat
        return re.sub(r'\/{2,}', '/', url)

    @cached_property
    def tags(self):
        tags = self._data.get('tags', '')
        if isinstance(tags, (tuple, list)):
            return tags
        if not tags:
            return []
        return [o.strip() for o in tags.split(',')]

    @cached_property
    def date(self):
        timezone = current_app.config.get('timezone')
        if not timezone:
            timezone = 'Asia/Chongqing'

        tz = pytz.timezone(timezone)
        return tz.localize(to_datetime(self._data['date']))


def static_url(filepath, url=None):
    """Generate static url."""
    if not url:
        url = '/' + filepath

    abspath = os.path.join(current_app.basedir, filepath)
    t = int(os.path.getmtime(abspath))
    return '%s?t=%i' % (url, t)


def permalink(obj, style):
    """Generate permalink by the given style.

    A style is defined in _config.yml, an example::

        /:year/:filename.html
    """
    pattern = re.compile(r':\w+')
    keys = pattern.findall(style)

    def _getattr(name):
        if name in ['year', 'month', 'day']:
            return getattr(obj.date, name)
        return getattr(obj, name)

    for key in keys:
        try:
            repl = _getattr(key[1:])
            style = style.replace(key, slugify(repl))
        except AttributeError:
            # TODO: warn
            pass
    # make sure / is flat
    style = re.sub(r'\/{2,}', '/', style)
    return style
