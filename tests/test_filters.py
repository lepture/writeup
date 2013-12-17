# coding: utf-8

from writeup import filters
import datetime


text = '\n'.join([
    '# title',
    '- key: value',
    '- url: http://lepture.com',
    '',
    '```python',
    'def foo():',
    '    pass',
    '```',
    '',
    '    def foo():',
    '        pass',
    '',
    '```notalanguage',
    'me = foo',
    '```',
    ''
])


def test_none():
    html = filters.markdown(None)
    assert html == ''

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


def test_youku_link():
    html = filters.markdown(
        'hello http://v.youku.com/v_show/id_XNjEyNDI4MDA4.html'
    )
    assert 'iframe' in html

    html = filters.markdown(
        'hello [Downton Abbey]'
        '(http://v.youku.com/v_show/id_XNjEyNDI4MDA4.html)'
    )
    assert '<figure>' in html


def test_gist_link():
    html = filters.markdown(
        'hello https://gist.github.com/paulmillr/2657075'
    )
    assert 'script' in html

    html = filters.markdown(
        'hello [git.io/top](https://gist.github.com/paulmillr/2657075)'
    )
    assert '<figure>' in html

def test_vimeo_link():
    html = filters.markdown('hello https://vimeo.com/79148964')
    assert 'iframe' in html


def test_auto_email():
    html = filters.markdown('hello me@lepture.com')
    assert 'mailto' in html


def test_width_height():
    html = filters.markdown(
        'hello [Downton Abbey]'
        '(http://v.youku.com/v_show/id_XNjEyNDI4MDA4.html "400x500")'
    )
    assert '<figure>' in html
    assert 'width="400"' in html
    assert 'height="500"' in html


def test_normal_link():
    html = filters.markdown(
        'hello [Downton Abbey]'
        '(http://movie.douban.com/subject/20398945/)'
    )
    assert '<figure>' not in html
    assert 'title' not in html

    html = filters.markdown(
        'hello [Downton Abbey]'
        '(http://movie.douban.com/subject/20398945/ "S4")'
    )
    assert 'title' in html


def test_image():
    html = filters.markdown(
        'hello ![Art of human body]'
        '(http://img3.douban.com/view/photo/photo/public/p1487563850.jpg)'
    )
    assert '<figure>' not in html

    html = filters.markdown(
        '![Art of human body]'
        '(http://img3.douban.com/view/photo/photo/public/p1487563850.jpg)'
    )
    assert '<figure>' in html

    html = filters.markdown(
        '![Art of human body]'
        '(http://img3.douban.com/view/photo/photo/public/'
        'p1487563850.jpg "Art of human body")'
    )
    assert '<figure>' in html


def test_block_quote():
    html = filters.markdown('> Hello World')
    assert 'cite-quote' not in html

    html = filters.markdown(
        '> Hello World\n'
        '> -- lepture\n'
    )
    assert 'cite-quote' in html


def test_xmldatetime():
    t = datetime.datetime(2013, 12, 13)
    assert filters.xmldatetime(t) == '2013-12-13T00:00:00'


def test_wordcount():
    s = u'''中文 is Chinese'''
    assert filters.wordcount(s) == 4

def test_linguist():
    s = u'''中文 is Chinese'''
    assert filters.linguist(s) == 'zh'

    s = u'''中文 is Chinese. And this is English.'''
    assert filters.linguist(s) == 'en'
