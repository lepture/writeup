# coding: utf-8
"""
    writeup.server
    ~~~~~~~~~~~~~~

    Start a server for previewing.

    :copyright: (c) 2013 by Hsiaoming Yang
"""

import os
import hashlib
import datetime
import mimetypes
import email.utils
from wsgiref.simple_server import make_server
from . import __version__


class Server(object):
    def __init__(self, sitedir='_site'):
        self._sitedir = sitedir

    def filepath(self, url):
        """Parse the real filepath of a url."""
        url = url.lstrip('/')
        url = os.path.join(self._sitedir, url)

        if url.endswith('/'):
            url += 'index.html'
        elif not os.path.exists(url) and not url.endswith('.html'):
            url += '.html'

        if not os.path.exists(url):
            return None
        return url

    def read(self, url):
        """Reading from a file."""
        url = self.filepath(url)
        if not url:
            return None
        with open(url, 'r') as f:
            return f.read()

    def mtime(self, url):
        url = self.filepath(url)
        if not url:
            return None
        mtime = os.path.getmtime(url)
        return email.utils.formatdate(mtime, usegmt=True)

    def serve_forever(self, host='0.0.0.0', port=4000):
        print('Start server at http://%s:%s' % (host, port))
        make_server(host, int(port), self.wsgi).serve_forever()

    def wsgi(self, environ, start_response):
        path = environ['PATH_INFO']
        mime_types, encoding = mimetypes.guess_type(path)
        if not mime_types:
            mime_types = 'text/html'

        body = self.read(path)
        headers = [
            ('Content-Type', mime_types),
            ('Server', 'Writeup/%s' % __version__),
        ]
        if body is None:
            start_response('404 Not Found', headers)
            not_found = self.read('404.html')
            if not_found:
                yield not_found
        else:
            etag = hashlib.md5(body).hexdigest()
            match = environ.get('HTTP_IF_NONE_MATCH', None)

            mtime = self.mtime(path)
            modified = environ.get('HTTP_IF_MODIFIED_SINCE', None)
            if etag == match or modified == mtime:
                start_response('304 Not Modified', headers)
            else:
                headers.append(('Etag', etag))
                headers.append(('Last-Modified', mtime))
                headers.append(('Content-Length', str(len(body))))
                start_response('200 OK', headers)
                yield body
