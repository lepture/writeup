# coding: utf-8

from writeup import parse


def test_parse_meta():
    text = '\n'.join([
        '# title',
        '- key: value',
        '- url: http://lepture.com',
        '',
        'A description about essay up.',
    ])
    meta = parse.parse_meta(text)
    assert u'title' == meta['title']
    assert u'value' == meta['key']
    assert u'http://lepture.com' == meta['url']
    assert u'A description about essay up.' == meta['description']


def test_parse_meta_no_title():
    text = '\n'.join([
        'spam',
        '# title',
        '- key: value',
        '- url: http://lepture.com',
        '',
        'A description about essay up.',
    ])
    meta = parse.parse_meta(text)
    assert meta['title'] is None


def test_parse():
    text = '\n'.join([
        '# title',
        '- key: value',
        '- url: http://lepture.com',
        '',
        'A description about essay up.',
        '-------',
        '',
        'A content placeholder.',
    ])
    article = parse.parse(text)
    assert article['title'] == u'title'
