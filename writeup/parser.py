#!/usr/bin/env python
# coding: utf-8
"""
    writeup.parser
    ~~~~~~~~~~~~~~

    Parse a markdown file into a Post.

    :copyright: (c) 2013 by Hsiaoming Yang
"""

import re
import yaml
import mistune as m
from ._compat import to_unicode

rules = m.BlockGrammar()


def parse(filepath):
    """Read a file and parse it to a dict."""

    with open(filepath, 'r') as f:
        content = f.read()

    try:
        meta = parse_text(content)
    except:
        return None

    meta['filepath'] = filepath
    return meta


def parse_text(text):
    """Parse a text and parse the meta data and content."""
    meta, body = re.split(r'\n-{3,}', to_unicode(text), 1)
    meta = parse_meta(to_unicode(meta).strip())
    meta['content'] = to_unicode(body).strip()
    return meta


def parse_meta(text):
    """Parse the meta part of an article.

    The meta part contains title, info, and description
    """
    meta = {}

    # parse title
    m = rules.heading.match(text)
    if m:
        title = m.group(2)
        text = text[len(m.group(0)):]
    else:
        m = rules.lheading.match(text)
        if m:
            title = m.group(1)
            text = text[len(m.group(0)):]
        else:
            title = None
    meta['title'] = title

    # parse meta data
    m = rules.list_block.match(text)
    if m:
        data = m.group(0)
        values = yaml.load(data)
        for item in values:
            for key in item:
                meta[key] = item[key]
        text = text[len(data):]

    # the rest part is the description
    meta['description'] = text
    return meta
