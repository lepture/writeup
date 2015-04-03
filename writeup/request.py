# coding: utf-8

import os
import json
from .utils import cached_property
from .globals import current_app
from .parser import read


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

        data = read(self.filepath)

        with open(filepath, 'wb') as f:
            json.dump(data, f)

        return data

    def __getattr__(self, key):
        try:
            return object.__getattribute__(self, key)
        except AttributeError:
            return self._data.get(key, None)

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

        # TODO
        return ''

    @cached_property
    def tags(self):
        tags = self._data.get('tags', '')
        if isinstance(tags, (tuple, list)):
            return tags
        if not tags:
            return []
        return [o.strip() for o in tags.split(',')]
