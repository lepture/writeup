
import sys
PY3 = sys.version_info[0] == 3

if PY3:
    unicode_type = str
    bytes_type = bytes
else:
    unicode_type = unicode
    bytes_type = str


def to_unicode(data, encoding='utf-8'):
    if isinstance(data, unicode_type):
        return data

    if isinstance(data, bytes_type):
        return unicode_type(data, encoding=encoding)

    if isinstance(data, int):
        return str(data)

    return data
