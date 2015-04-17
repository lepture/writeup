# coding: utf-8
"""
    writeup
    ~~~~~~~

    :copyright: (c) 2013 - 2015 by Hsiaoming Yang
"""

__version__ = '0.2'
__author__ = 'Hsiaoming Yang <me@lepture.com>'
__license__ = 'BSD'
__homepage__ = 'https://github.com/lepture/writeup'


from .app import Application
from .builder import PostBuilder, PageBuilder, FileBuilder


class Writeup(object):
    def __init__(self, config=None, **kwargs):
        app = Application(config=config, **kwargs)
        self.post_builder = PostBuilder(app)
        self.page_builder = PageBuilder(app)
        self.file_builder = FileBuilder(app)
        self.app = app

    def build(self, filepath):
        with self.app.create_context():
            if filepath in self.app.post_indexer.keys():
                self.post_builder.build(filepath)
            elif filepath in self.app.page_indexer.keys():
                self.page_builder.build(filepath)
            else:
                self.file_builder.build(filepath)

    def run(self):
        with self.app.create_context():
            self.post_builder.run()
            self.page_builder.run()
            self.file_builder.run()
