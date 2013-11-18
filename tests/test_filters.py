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


def test_linenos_markdown():
    html = filters.markdown(text, highlight=True, linenos=True)
    assert 'linenos' in html


def test_inline_markdown():
    html = filters.markdown(text, highlight=True, inlinestyles=True)
    assert 'background:' in html


def test_youtube_link():
    html = filters.markdown(
        'hello http://www.youtube.com/watch?v=p8Ey0AufD9g'
    )
    assert 'iframe' in html


def test_youtube_link2():
    html = filters.markdown('hello http://youtu.be/p8Ey0AufD9g')
    assert 'iframe' in html


def test_gist_link():
    html = filters.markdown(
        'hello https://gist.github.com/paulmillr/2657075'
    )
    assert 'script' in html


def test_vimeo_link():
    html = filters.markdown('hello https://vimeo.com/79148964')
    assert 'iframe' in html
