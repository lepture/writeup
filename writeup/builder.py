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


logger = logging.getLogger('writeup')


class Builder(object):
    def __init__(self):
        pass

    def is_supported(self, filename):
        ext = os.path.splitext(filename)[1]
        return ext in ('.md', '.mkd', '.markdown')


class RequestBuilder(Builder):
    pass


class HTMLBuilder(Builder):
    pass
