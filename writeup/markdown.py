# coding: utf-8

import os
import re
import mistune as m
from markupsafe import escape
from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import HtmlFormatter
from .utils import _top
from ._compat import to_bytes, to_unicode


class BaseRenderer(m.Renderer):
    def autolink(self, link, is_email):
        if is_email:
            return '<a href="mailto:%(link)s">%(link)s</a>' % {'link': link}
        html = embed(link)
        if html:
            return html
        content = link.replace('http://', '').replace('https://', '')
        return '<a href="%s">%s</a>' % (link, content)

    def link(self, link, title, content):
        html = '<a href="%s"' % link
        if title:
            html = '%s title="%s"' % (html, title)

        if '<figure><img' in content:
            return re.sub(r'(<img.*?>)', r'%s>\1</a>' % html, content)

        html = '%s>%s</a>' % (html, content)
        return html

    def image(self, link, title, alt_text):
        if hasattr(self, '_lazyimg') and self._lazyimg:
            html = '<img data-src="%s" alt="%s" />' % (link, alt_text)
        else:
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
            return '<figure>%s</figure>\n' % content
        return '<p>%s</p>\n' % content

    def block_quote(self, content):
        pattern = ur'<p>(?:--|\u2014)\s*([^<]+)<\/p>$'
        match = re.search(pattern, content, re.U)
        if not match:
            return '<blockquote>%s</blockquote>' % content
        text = match.group(1).strip()
        pattern = r'%s$' % match.group(0)
        cite = '<cite>%s</cite>' % text
        content = re.sub(pattern, cite, content, flags=re.M)
        return '<blockquote class="cite-quote">%s</blockquote>' % content


class HighlightRenderer(BaseRenderer):
    def block_code(self, text, lang):
        if not lang:
            text = text.strip()
            return u'<pre><code>%s</code></pre>\n' % escape(text)

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
                return '<div class="highlight-wrapper">%s</div>\n' % code
            return code
        except:
            return '<pre class="%s"><code>%s</code></pre>\n' % (
                lang, escape(text)
            )

_mds = {}


def _get_md(highlight, inlinestyles, linenos, lazyimg):
    global _mds
    ident = hash((highlight, inlinestyles, linenos, lazyimg))
    md = _mds.get(ident)
    if md:
        return md
    if highlight:
        renderer = HighlightRenderer()
        renderer._inlinestyles = inlinestyles
        renderer._linenos = linenos
    else:
        renderer = BaseRenderer()

    renderer._lazyimg = lazyimg
    md = m.Markdown(renderer)
    _mds[ident] = md
    return md


def markdown(text, highlight=True, inlinestyles=False, linenos=False,
             lazyimg=False, cache_key=None):
    """Markdown filter for writeup.

    :param text: the content to be markdownify
    :param highlight: highlight the code block or not
    :param inlinestyles: highlight the code with inline styles
    :param linenos: show linenos of the highlighted code
    :param lazyimg: render image src as data-src
    :param cache_key: read from cache if possible
    """
    if not text:
        return u''

    if cache_key is None and _top.request:
        cache_key = '%i-%s' % (len(text), _top.request._cache_key)

    if cache_key is None:
        md = _get_md(highlight, inlinestyles, linenos, lazyimg)
        return md.render(text)

    ident = hash((highlight, inlinestyles, linenos, lazyimg))
    key = 'markdown.%i.%s' % (ident, cache_key)
    cache_file = os.path.join(_top.app.cachedir, key)
    if os.path.isfile(cache_file):
        with open(cache_file, 'rb') as f:
            return to_unicode(f.read())

    md = _get_md(highlight, inlinestyles, linenos, lazyimg)
    html = md.render(text)
    with open(cache_file, 'wb') as f:
        f.write(to_bytes(html))
    return html
