# coding: utf-8

"""
    writeup.builder
    ~~~~~~~~~~~~~~~

    Load configuration, source and build the site.

    :copyright: (c) 2013 - 2015 by Hsiaoming Yang
"""

import os
import json
import logging

from .request import Request
from .globals import current_app
from .utils import cached_property

logger = logging.getLogger('writeup')


class Indexer(object):
    def __init__(self, name, *keys):
        self.db_file = os.path.join(current_app.cachedir, name)
        self.keys = keys

    @cached_property
    def _data(self):
        if not os.path.exists(self.db_file):
            return {}

        with open(self.db_file, 'rb') as f:
            return json.load(f)

    def add(self, req):
        value = {k: getattr(req, k) for k in self.keys}
        self._data[req.filepath] = value

    def keys(self):
        return self._data.keys()

    def save(self):
        filepath = os.path.join(current_app.cachedir, self.db_file)
        with open(filepath, 'wb') as f:
            f.dump(self._data, f)


post_index = Indexer(
    'post.index', 'date', 'mtime', 'dirname', 'tags', 'title',
)

page_index = Indexer(
    'page.index', 'mtime', 'dirname', 'title',
)


class Builder(object):
    def __init__(self):
        pass


class RequestBuilder(Builder):
    pass


class HTMLBuilder(Builder):
    pass
