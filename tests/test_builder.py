# coding: utf-8

import os
import tempfile
from writeup.builder import Builder

dirname = os.path.abspath(os.path.dirname(__file__))
source = os.path.join(dirname, 'cases', 'builder')
config = os.path.join(source, '_config.yml')
postsdir = os.path.join(source, '_posts')


class TestBuilder(object):
    def setUp(self):
        builder = Builder(config=config, source=source, postsdir=postsdir)
        self.builder = builder

    def test_read(self):
        f = os.path.join(postsdir, 'welcome-to-writeup.md')
        post = self.builder.read(f)
        assert post.title == u'Welcome to Writeup'

        post = self.builder.read(f)
        assert post is None

    def test_load_posts(self):
        self.builder.load_posts()
        assert len(list(self.builder.posts())) > 0

    def test_build(self):
        self.builder.build()


class TestCacheBuilder(TestBuilder):
    def setUp(self):
        builder = Builder(
            config=config,
            source=source,
            postsdir=postsdir,
            cachedir = tempfile.mkdtemp(),
        )
        self.builder = builder
