# coding: utf-8
"""
    writeup.utils
    ~~~~~~~~~~~~~

    Utilities for writeup.

    :copyright: (c) 2013 by Hsiaoming Yang
"""

import os
import re
import json
import shutil
import datetime
import threading
import unicodedata
from ._compat import to_bytes, to_unicode


_top = threading.local()
# set default request
_top.request = None


class _Missing(object):

    def __repr__(self):
        return 'no value'

    def __reduce__(self):
        return '_missing'

_missing = _Missing()


class cached_property(property):
    def __init__(self, func, name=None, doc=None):
        self.__name__ = name or func.__name__
        self.__module__ = func.__module__
        self.__doc__ = doc or func.__doc__
        self.func = func

    def __set__(self, obj, value):
        obj.__dict__[self.__name__] = value

    def __get__(self, obj, type=None):
        if obj is None:
            return self
        value = obj.__dict__.get(self.__name__, _missing)
        if value is _missing:
            value = self.func(obj)
            obj.__dict__[self.__name__] = value
        return value


def to_datetime(value):
    """Convert possible value to datetime."""
    if not value:
        return None
    if isinstance(value, datetime.datetime):
        return value
    if isinstance(value, datetime.date):
        return datetime.datetime.combine(
            value, datetime.datetime.min.time()
        )
    if isinstance(value, (int, float)):
        # TODO
        return value

    supported_formats = [
        '%a %b %d %H:%M:%S %Y',
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%d %H:%M',
        '%Y-%m-%dT%H:%M',
        '%Y%m%d %H:%M:%S',
        '%Y%m%d %H:%M',
        '%Y-%m-%d',
        '%Y%m%d',
    ]
    for fmt in supported_formats:
        try:
            return datetime.datetime.strptime(value, fmt)
        except ValueError:
            pass
    raise ValueError('Unrecognized date/time: %r' % value)


class JSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, datetime.datetime):
            return o.strftime('%Y-%m-%d %H:%M:%S')
        if isinstance(o, datetime.date):
            return o.strftime('%Y-%m-%d')
        return super(JSONEncoder, self).default(o)


def json_dump(obj, f):
    json.dump(obj, f, cls=JSONEncoder)


def is_subdir(source, target):
    """If target is a subdirectory of source."""
    relpath = os.path.relpath(source, target)
    return not relpath.startswith('../')


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


def fwrite(dest, content):
    """Write given content to the destination."""
    # make sure the directory exists
    folder = os.path.split(dest)[0]
    if not os.path.isdir(folder):
        os.makedirs(folder)

    with open(dest, 'w') as f:
        f.write(to_bytes(content))


def fcopy(source, dest):
    """Copy a file to the givent destination."""
    source_time = os.path.getmtime(source)
    if os.path.exists(dest) and source_time <= os.path.getmtime(dest):
        return

    folder = os.path.split(dest)[0]
    if not os.path.isdir(folder):
        os.makedirs(folder)

    shutil.copy(source, dest)
