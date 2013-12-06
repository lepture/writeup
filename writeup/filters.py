# coding: utf-8
"""
    writeup.filters
    ~~~~~~~~~~~~~~~

    Built-in filters for Writeup.

    :copyright: (c) 2013 by Hsiaoming Yang
"""

import re
import misaka as m
from markupsafe import escape
from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import HtmlFormatter


def _iframe(src, width=650, height=365, content=None, link=None):
    """Create an iframe html snippet."""
    html = (
        '<iframe width="%s" height="%s" src="%s" '
        'frameborder="0" allowfullscreen></iframe>'
    ) % (width, height, src)
    if not content:
        return html
    if link:
        content = '<a href="%s">%s</a>' % (link, content)
    return '<figure>%s<figcaption>%s</figcaption></figure>' % (
        html, content
    )


def youtube(link):
    """Find youtube player URL."""
    pattern = r'http://www\.youtube\.com\/watch\?v=([a-zA-Z0-9\-\_]+)'
    match = re.match(pattern, link)
    if not match:
        pattern = r'http:\/\/youtu.be\/([a-zA-Z0-9\-\_]+)'
        match = re.match(pattern, link)
    if not match:
        return None
    return 'http://www.youtube.com/embed/%s' % match.group(1)


def vimeo(link):
    """Find vimeo player URL."""
    pattern = r'https?:\/\/vimeo\.com\/([\d]+)'
    match = re.match(pattern, link)
    if not match:
        return None
    return 'https://player.vimeo.com/video/%s' % match.group(1)


def youku(link):
    """Find youku player URL."""
    pattern = r'http:\/\/v\.youku\.com\/v_show/id_([\w]+)\.html'
    match = re.match(pattern, link)
    if not match:
        return None
    return 'http://player.youku.com/embed/%s' % match.group(1)


def gist(link, content=None):
    """Render gist script."""
    pattern = r'(https?:\/\/gist\.github\.com\/.+\d+)'
    match = re.match(pattern, link)
    if not match:
        return None
    html = '<script src="%(link)s.js"></script>' % match.group(1)
    if not content:
        return html
    return '<figure>%s<figcaption>%s</figcaption></figure>' % (
        html, content
    )


def embed(link, width=650, height=366, content=None):
    html = gist(link, content)
    if html:
        return html

    src = youtube(link)
    if src:
        return _iframe(src, width, height, content, link)
    src = vimeo(link)
    if src:
        return _iframe(src, width, height, content, link)
    src = youku(link)
    if src:
        return _iframe(src, width, height, content, link)
    return None


class BaseRenderer(m.HtmlRenderer):
    def autolink(self, link, is_email):
        if is_email:
            return '<a href="mailto:%(link)s">%(link)s</a>' % {'link': link}
        html = embed(link)
        if html:
            return html
        content = link.replace('http://', '').replace('https://', '')
        return '<a href="%s">%s</a>' % (link, content)

    def link(self, link, title, content):
        width = 650
        height = 366
        if title:
            # title can descibe height and width: 650 x 366
            pattern = r'(\d{3,4})[^\d]+(\d{3})'
            match = re.match(pattern, title)
            if match:
                width = match.group(1)
                height = match.group(2)
        html = embed(link, width, height, content)
        if html:
            return html
        html = '<a href="%s"' % link
        if title:
            html = '%s title="%s"' % (html, title)
        html = '%s>%s</a>' % (html, content)
        return html

    def image(self, link, title, alt_text):
        html = '<img src="%s" alt="%s" />' % (link, alt_text)
        if not title:
            return html
        return '<figure>%s<figcaption>%s</figcaption></figure>' % (
            html, title
        )

    def paragraph(self, content):
        pattern = r'<figure>.*</figure>'
        if re.match(pattern, content):
            return content
        # a single image in this paragraph
        pattern = r'^<img[^>]+>$'
        if re.match(pattern, content):
            return '<figure>%s</figure>' % content
        return '<p>%s</p>' % content

    def block_quote(self, content):
        pattern = r'^--([^<]+)(.*)$'
        match = re.search(pattern, content, re.M | re.U)
        if not match:
            return '<blockquote>%s</blockquote>' % content
        text = match.group(1).strip()
        pattern = r'%s$' % match.group(0)
        content = re.sub(pattern, match.group(2), content)
        return (
            '<blockquote class="cite-quote">'
            '%s<cite>%s</cite>'
            '</blockquote>'
        ) % (content, text)


class HighlightRenderer(BaseRenderer):
    def block_code(self, text, lang):
        if not lang:
            return u'<pre><code>%s</code></pre>' % escape(text)

        inlinestyles = False
        linenos = False
        if hasattr(self, '_inlinestyles'):
            inlinestyles = self._inlinestyles
        if hasattr(self, '_linenos'):
            linenos = self._linenos

        try:
            lexer = get_lexer_by_name(lang, stripall=True)
            formatter = HtmlFormatter(
                noclasses=inlinestyles, linenos=linenos
            )
            code = highlight(text, lexer, formatter)
            if linenos:
                return '<div class="highlight-wrapper">%s</div>' % code
            return code
        except:
            return '<pre class="%s"><code>%s</code></pre>' % (
                lang, escape(text)
            )


def markdown(text, highlight=True, inlinestyles=False, linenos=False):
    """Markdown filter for writeup.

    :param text: the content to be markdownify
    :param highlight: highlight the code block or not
    :param inlinestyles: highlight the code with inline styles
    :param linenos: show linenos of the highlighted code
    """
    if not text:
        return u''
    if highlight:
        renderer = HighlightRenderer()
        renderer._inlinestyles = inlinestyles
        renderer._linenos = linenos
    else:
        renderer = BaseRenderer()

    extensions = (
        m.EXT_NO_INTRA_EMPHASIS | m.EXT_FENCED_CODE | m.EXT_AUTOLINK |
        m.EXT_TABLES | m.EXT_STRIKETHROUGH | m.EXT_SUPERSCRIPT
    )
    md = m.Markdown(renderer, extensions=extensions)
    return md.render(text)


def xmldatetime(date):
    """Convert a Date into XML Schema RFC3339 format."""
    time = date.strftime('%Y-%m-%dT%H:%M:%S')
    tz = date.strftime('%z')
    return time + tz[:3] + ':' + tz[3:]


word_pattern = re.compile(
    u'[a-zA-Z0-9_\u0392-\u03c9]+|'
    u'[\u4E00-\u9FFF\u3400-\u4dbf\uf900-\ufaff\u3040-\u309f\uac00-\ud7af]+',
    re.UNICODE
)


def wordcount(data):
    """Word count for ASCII and CJK."""
    ret = word_pattern.findall(data)
    count = 0
    for s in ret:
        if ord(s[0]) >= 12352:
            # this is cjk
            count += len(s)
        else:
            count += 1
    return count
