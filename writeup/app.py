# coding: utf-8

import os
import pytz
import json
import fnmatch
import logging
import datetime
from contextlib import contextmanager
from .request import Request
from .utils import _top
from .utils import cached_property
from .utils import json_dump

logger = logging.getLogger('writeup')


class Application(object):
    def __init__(self, config=None, **kwargs):
        kwargs.setdefault('basedir', '.')
        kwargs.setdefault('postsdir', '_posts')
        kwargs.setdefault('sitedir', '_site')
        kwargs.setdefault('cachedir', '.cache')
        kwargs.setdefault('permalink', '/:dirname/:filename.html')

        if config is not None:
            kwargs.update(load_config(config))

        self.config = kwargs

    @cached_property
    def permalink(self):
        return self.config.get('permalink')

    @cached_property
    def basedir(self):
        return os.path.abspath(self.config.get('basedir'))

    @cached_property
    def postsdir(self):
        return os.path.abspath(self.config.get('postsdir'))

    @cached_property
    def sitedir(self):
        return os.path.abspath(self.config.get('sitedir'))

    @cached_property
    def cachedir(self):
        directory = os.path.abspath(self.config.get('cachedir'))
        if os.path.isdir(directory):
            return directory
        os.makedirs(directory)
        return directory

    @cached_property
    def jinja(self):
        layouts = self.config.get('layouts', '_layouts')
        includes = self.config.get('includes', '_includes')
        jinja = create_jinja(layouts, includes)
        jinja.globals.update(create_jinja_globals(self))
        return jinja

    @contextmanager
    def create_context(self):
        _top.app = self
        yield
        del _top.app

    @cached_property
    def post_indexer(self):
        db_file = os.path.join(self.cachedir, 'post.index')
        return Indexer(db_file, 'mtime', 'dirname', 'tags', 'date')

    @cached_property
    def page_indexer(self):
        db_file = os.path.join(self.cachedir, 'page.index')
        return Indexer(db_file, 'mtime', 'dirname', 'filename')

    @cached_property
    def file_indexer(self):
        db_file = os.path.join(self.cachedir, 'file.index')
        return Indexer(db_file, 'mtime', 'dirname', 'filename')

    def create_index(self):
        logger.info('indexing')

        def index_request(req):
            logger.debug('indexing [%s]: %s' % (req.file_type, req.relpath))
            if req.file_type == 'post':
                self.post_indexer.add(req)
            elif req.file_type == 'page':
                self.page_indexer.add(req)
            elif req.file_type == 'file':
                self.file_indexer.add(req)

        if self.basedir in self.postsdir:
            includes = [os.path.relpath(self.postsdir, self.basedir)]
        else:
            includes = None

        for filename in walk_tree(self.basedir, includes=includes):
            index_request(Request(filename))

        if not includes:
            for filename in walk_tree(self.postsdir):
                index_request(Request(filename))

        self.post_indexer.save()
        self.page_indexer.save()
        self.file_indexer.save()


class Indexer(object):
    def __init__(self, db_file, *keys):
        self.db_file = db_file
        self._keys = keys

    @cached_property
    def mtime(self):
        if not os.path.exists(self.db_file):
            return None
        return os.path.getmtime(self.db_file)

    @cached_property
    def _data(self):
        if not os.path.exists(self.db_file):
            return {}

        with open(self.db_file, 'rb') as f:
            return json.load(f)

    def add(self, req):
        if self.mtime and self.mtime > req.mtime:
            # ignore this file
            return
        value = {k: getattr(req, k) for k in self._keys}
        self._data[req.filepath] = value

    def keys(self):
        return self._data.keys()

    def filter(self, func):
        for key in self._data:
            rv = self._data[key]
            rv['filepath'] = key
            if func(rv):
                yield key

    def save(self):
        data = self._data
        with open(self.db_file, 'wb') as f:
            json_dump(data, f)


def create_jinja(layouts='_layouts', includes='_includes'):
    loaders = []

    if not os.path.exists(layouts):
        raise RuntimeError('%s directory is required.' % layouts)

    loaders.append(layouts)

    if os.path.exists(includes):
        loaders.append(includes)

    from jinja2 import Environment, FileSystemLoader
    jinja = Environment(
        loader=FileSystemLoader(loaders),
        trim_blocks=True,
        lstrip_blocks=True,
        autoescape=False,
        extensions=[
            'jinja2.ext.do',
            'jinja2.ext.loopcontrols',
            'jinja2.ext.with_',
        ]
    )

    from . import filters
    rv = {k: getattr(filters, k) for k in filters.__all__}
    jinja.filters.update(rv)

    jinja._last_updated = max((os.path.getmtime(d) for d in loaders))
    return jinja


def load_config(filepath):
    """Load and parse configuration from a yaml file."""
    from yaml import load
    try:
        from yaml import CLoader as Loader
    except ImportError:
        from yaml import Loader

    with open(filepath, 'r') as f:
        return load(f, Loader)


def walk_tree(source, includes=None, excludes=None):
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
            if excludes and fnmatch.fnmatch(relpath, excludes):
                continue

            yield filepath


def create_jinja_globals(app):

    site = app.config.copy()
    tz = pytz.timezone(site.get('timezone', 'Asia/Shanghai'))
    site['now'] = tz.localize(datetime.datetime.now())

    def filter_posts(subdirectory=None, reverse=True, count=None):
        dirname = subdirectory

        def get_posts():
            for key in app.post_indexer._data:
                rv = app.post_indexer._data[key]
                if dirname is not None and rv['dirname'] != dirname:
                    continue
                rv['filepath'] = key
                yield rv

        posts = sorted(get_posts(), key=lambda o: o['date'], reverse=reverse)
        if count:
            posts = posts[:count]

        for rv in posts:
            yield Request(rv['filepath'])

    site['posts'] = filter_posts

    def static_url(filepath, url=None):
        """Generate static url."""
        if not url:
            url = '/' + filepath

        abspath = os.path.join(app.basedir, filepath)
        t = int(os.path.getmtime(abspath))
        return '%s?t=%i' % (url, t)

    return {'site': site, 'static_url': static_url}
