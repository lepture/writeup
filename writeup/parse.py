#!/usr/bin/env python
# coding: utf-8
"""
    writeup.parse
    ~~~~~~~~~~~~~
"""

import re
import hoedown as m
from ._compat import to_unicode


def parse(text):
    """Parse a text and parse the meta data and content."""
    meta, body = re.split(r'\n---{3,}', text, 1)

    meta = parse_meta(to_unicode(text).strip())
    ret = format_meta(meta)
    ret['meta'] = meta
    ret['body'] = to_unicode(body).strip()
    return ret


def parse_meta(text):
    """Parse the meta part of an article.

    The meta part contains title, info, and description.
    """
    meta = {}
    html = m.html(text)
    titles = re.findall(r'^<h1>(.*)</h1>', html)
    if not titles:
        meta[u'title'] = None
    else:
        meta[u'title'] = titles[0]

    items = re.findall(r'<li>(.*?)</li>', html, re.S)
    for item in items:
        key, value = item.split(':', 1)
        meta[key.rstrip()] = value.lstrip()

    desc = re.findall(r'<p>(.*?)</p>', html, re.S)
    if desc:
        meta[u'description'] = '\n\n'.join(desc)

    return meta


def format_meta(data):
    """Handle special built-in meta data and rich format them."""
    ret = {}
    ret['title'] = data.pop('title', None)
    ret['description'] = data.pop('description', None)
    return ret
