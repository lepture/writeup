# coding: utf-8
"""
    writeup.filters
    ~~~~~~~~~~~~~~~

    Built-in filters for Writeup.

    :copyright: (c) 2013 by Hsiaoming Yang
"""

import re
from .markdown import markdown

__all__ = ['markdown', 'xmldatetime', 'wordcount', 'linguist']


def xmldatetime(date):
    """Convert a Date into XML Schema RFC3339 format."""
    return date.isoformat('T')


word_pattern = re.compile(
    u'[a-zA-Z0-9_\u0392-\u03c9]+|'
    u'[\u4E00-\u9FFF\u3400-\u4dbf\uf900-\ufaff\u3040-\u309f\uac00-\ud7af]+',
    re.UNICODE
)


def wordcount(data):
    """Word count for ASCII and CJK."""
    if not data:
        return 0
    ret = word_pattern.findall(data)
    count = 0
    for s in ret:
        if ord(s[0]) >= 0x4e00:
            # this is cjk
            count += len(s)
        else:
            count += 1
    return count


def linguist(data):
    """Language detection.

    Currently only support English and Chinese.
    """
    if not data:
        return 'en'
    ret = word_pattern.findall(data)
    chinese = 0
    english = 0
    for s in ret:
        if ord(s[0]) >= 0x4e00:
            chinese += len(s)
        else:
            english += 1

    if float(chinese) / (chinese + english) > 0.26:
        return 'zh'
    return 'en'
