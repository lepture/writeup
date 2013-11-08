# coding: utf-8

from writeup import filters


text = '\n'.join([
    '# title',
    '- key: value',
    '- url: http://lepture.com',
    '',
    '```python',
    'def foo:',
    '    pass',
    '```',
])


def test_plain_markdown():
    html = filters.markdown(text, highlight=False)
    assert 'highlight' not in html


def test_highlight_markdown():
    html = filters.markdown(text, highlight=True)
    assert 'highlight' in html


def test_highlight_markdown():
    html = filters.markdown(text, highlight=True, linenos=True)
    assert 'linenos' in html


def test_highlight_markdown():
    html = filters.markdown(text, highlight=True, inlinestyles=True)
    assert 'background:' in html
