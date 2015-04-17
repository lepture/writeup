# coding: utf-8

import os
import re
import json
import logging
from datetime import datetime
from .parser import parse
from .utils import _top
from .utils import cached_property, slugify, to_datetime, json_dump

logger = logging.getLogger('writeup')


class Request(object):
    def __init__(self, filepath, **kwargs):
        self.filepath = filepath
        self._app = kwargs.pop('app', _top.app)
        self._values = kwargs

    @cached_property
    def mtime(self):
        return os.path.getmtime(self.filepath)

    @cached_property
    def _cache_key(self):
        name = os.path.relpath(self.filepath).replace(os.path.sep, '.')
        return '%s-%s' % (name, self.mtime)

    @cached_property
    def _data(self):
        if self._should_parse_file():
            data = self._parse_file()
        else:
            data = {}
        data.update(self._values)
        return data

    def _parse_file(self):
        filepath = os.path.join(self._app.cachedir, self._cache_key)

        if os.path.exists(filepath):
            with open(filepath, 'rb') as f:
                return json.load(f)

        data = parse(self.filepath)
        if data is None:
            logger.warn('parsing failed: %s' % self.relpath)
            return {}

        logger.debug('parsing success: %s' % self.relpath)
        with open(filepath, 'wb') as f:
            json_dump(data, f)

        return data

    def __getattr__(self, key):
        try:
            return object.__getattribute__(self, key)
        except AttributeError:
            return self._data.get(key, None)

    def _should_parse_file(self):
        ext = os.path.splitext(self.filepath)[1]
        return ext in ('.md', '.mkd', '.markdown')

    @cached_property
    def file_type(self):
        if not self._should_parse_file():
            return 'file'

        if self._app.postsdir not in self.filepath:
            return 'page'

        if 'status' in self._data and self._data['status'] == 'draft':
            return 'draft'

        if 'date' not in self._data:
            return 'draft'

        return 'post'

    @cached_property
    def relpath(self):
        if self._app.postsdir in self.filepath:
            relpath = os.path.relpath(self.filepath, self._app.postsdir)
        else:
            relpath = os.path.relpath(self.filepath, self._app.basedir)

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

        style = self._app.permalink
        if self.file_type == 'post':
            return create_permalink(self, style)

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
    def title(self):
        return self._data.get('title')

    @cached_property
    def description(self):
        return self._data.get('description')

    @cached_property
    def body(self):
        return self._data.get('content')

    @cached_property
    def content(self):
        return self._data.get('content')

    @cached_property
    def tags(self):
        tags = self._data.get('tags', '')
        if isinstance(tags, (tuple, list)):
            return tags
        if not tags:
            return []
        return [o.strip() for o in tags.split(',')]

    @cached_property
    def timestamp(self):
        if self.file_type != 'post':
            return self.mtime
        delta_epoch = to_datetime(self._data['date']) - datetime(1970, 1, 1)
        return delta_epoch.total_seconds()

    @cached_property
    def date(self):
        if self.file_type != 'post':
            return None

        tz = self._app.timezone
        return tz.localize(to_datetime(self._data['date']))


def create_permalink(obj, style):
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
