# coding: utf-8
"""
    writeup.utils
    ~~~~~~~~~~~~~

    Utilities for writeup.

    :copyright: (c) 2013 by Hsiaoming Yang
"""

import os
import re
import shutil
from ._compat import to_bytes


def is_markdown(filepath):
    ext = os.path.splitext(filepath)[1]
    return ext in ('.md', '.mkd', '.markdown')


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


def fwalk(source, includes=None, excludes=None):
    dirs = filter(
        lambda f: os.path.isdir(os.path.join(source, f)),
        os.listdir(source)
    )

    for dirpath, dirnames, filenames in os.walk(source, followlinks=True):
        if '.git' in dirnames:
            dirnames.remove('.git')
        if '.hg' in dirnames:
            dirnames.remove('.git')
        if '.svn' in dirnames:
            dirnames.remove('.git')
        for name in dirs:
            if name.startswith('.') and name in dirnames:
                dirnames.remove(name)
            elif name.startswith('_') and name in dirnames:
                if not includes or name not in includes:
                    dirnames.remove(name)

        for filename in filenames:
            if filename.startswith('.'):
                # ignore hidden files
                continue
            filepath = os.path.join(dirpath, filename)
            relpath = os.path.relpath(filepath, source)
            if not (excludes and relpath in excludes):
                yield filepath


def is_subdir(source, target):
    """If target is a subdirectory of source."""
    relpath = os.path.relpath(source, target)
    return not relpath.startswith('../')


def is_html(filepath):
    exts = ('.html', '.xml')
    for ext in exts:
        if filepath.endswith(ext):
            return True
    return False


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

    @property
    def prev_url(self):
        if self.prev_num == 1:
            return self._root
        ret = self._style.replace(':num', str(self.prev_num))
        return self._root + ret

    @property
    def has_next(self):
        return self.page < self.pages

    @property
    def next_num(self):
        return self.page + 1

    @property
    def next_url(self):
        ret = self._style.replace(':num', str(self.next_num))
        return self._root + ret

    @property
    def posts(self):
        start = (self.page - 1) * self.per_page
        end = self.page * self.per_page
        items = self.items[start:end]
        for k, _ in items:
            yield self._cache.get(k)
