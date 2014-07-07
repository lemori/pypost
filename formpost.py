#coding: utf-8

# 2006/02 Will Holcomb <wholcomb@gmail.com>
# 
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
# 
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# 2007/07/26 Slightly modified by Brian Schneider  
#
# in order to support unicode files ( multipart_encode function )
# From http://peerit.blogspot.com/2007/07/multipartposthandler-doesnt-work-for.html
#
# 2013/07 Ken Olum <kdo@cosmos.phy.tufts.edu>
#
# Removed one of \r\n and send Content-Length
#
# 2014/05 Applied Fedora rpm patch
#
# https://bugzilla.redhat.com/show_bug.cgi?id=920778
# http://pkgs.fedoraproject.org/cgit/python-MultipartPostHandler2.git/diff/python-MultipartPostHandler2-cut-out-main.patch?id=c1638bb3e45596232b4d02f1e69901db0c28cfdb
#
# 2014/05/09 Sérgio Basto <sergio@serjux.com>
#
# Better deal with None values, don't throw an exception and just send an empty string.
# Simplified text example
#
# 2014/07/07 <lemori@foxmail.com>
# Feature:
#    A simple api interface with more functions;
#    Supports Non-ASCII values/dict and filenames well.
"""
Usage:
    webutil.post(url, data=None, has_files=False|True)
When has_files=False:
    data can be a relatively complicated structure, e.g.
    { "user": { "name": "bob", "age": "18"},
        "colors": ["red", "blue", "green"] }
When has_files=True:
    it post with contenttype = multipart/form-data
    and data should be a simple dict, e.g.
    { "username" : "bob", "password" : "riviera",
        "file" : open("filepath", "rb") }
"""
import urllib
import urllib2
import os, stat
import re
from mimetypes import guess_type
from cStringIO import StringIO

class Callable:
    def __init__(self, anycallable):
        self.__call__ = anycallable

# Controls how sequences are uncoded.
# If true, elements may be given multiple values by assigning a sequence.
doseq = 1

def has_non_ascii(value):
    if re.search('\\\\x', repr(value)) or re.search('\\\\u', repr(value)):
        return True
    else:
        return False

def encode_str(value):
    if has_non_ascii(value):
        value = value.decode('utf-8') if isinstance(value, str) else value
    if isinstance(value, unicode):
        return value.encode('utf-8')
    else:
        return value

def _json_dumps(obj, box):
    # Better simplejson.dumps function
    if isinstance(obj, basestring):
        box.append( encode_str(obj).replace('\n', '\\n').replace('"', '\\"') )
        return
    elif isinstance(obj, list):
        c = False
        box.append('[')
        for v in obj:
            if c:
                box.append(',')
            c = True
            b = '"' if isinstance(v, (basestring,int,bool)) else ''
            box.append(b)
            _json_dumps(v, box)
            box.append(b)
        box.append(']')
        return
    elif isinstance(obj, dict):
        c = False
        box.append('{')
        for (k,v) in obj.items():
            if c:
                box.append(',')
            c = True
            box.append('"%s":' % encode_str(k))
            b = '"' if isinstance(v, (basestring,int,bool)) else ''
            box.append(b)
            _json_dumps(v, box)
            box.append(b)
        box.append('}')
        return
    elif isinstance(obj, bool):
        box.append('%s' % ('1' if obj else '0'))
        return
    else:
        box.append( str(obj) )
        return

class FormDataHandler(urllib2.BaseHandler):
    handler_order = urllib2.HTTPHandler.handler_order - 10 # needs to run first

    def http_request(self, request):
        data = request.get_data()
        if data is None:
            return request
        if not isinstance(data, basestring):
            v_files = []
            v_vars = []
            try:
                for(key, value) in data.items():
                    if type(value) == file:
                        v_files.append((key, value))
                    else:
                        v_vars.append((key, encode_str(value)))
            except TypeError:
                systype, value, traceback = sys.exc_info()
                raise TypeError, "not a valid non-string sequence or mapping object", traceback

            if len(v_files) == 0:
                data = urllib.urlencode(v_vars, doseq)
            else:
                boundary, data = self.multipart_encode(v_vars, v_files)
                contenttype = 'multipart/form-data; boundary=%s' % boundary
                if(request.has_header('Content-Type')
                   and request.get_header('Content-Type').find('multipart/form-data') != 0):
                    print "Replacing %s with %s" % (
                        request.get_header('content-type'),
                        'multipart/form-data')
                request.add_unredirected_header('Content-Type', contenttype)

            request.add_data(data)
        elif has_non_ascii(data):
            request.add_data(encode_str(data))

        return request

    def multipart_encode(vars, files, boundary = None, buffer = None):
        if boundary is None:
            boundary = '----------ThIs_Is_tHe_bouNdaRY_$' # No guarantee
        if buffer is None:
            buffer = StringIO()
        for(key, value) in vars:
            value = "" if value is None else value
            buffer.write('--%s\r\n' % boundary)
            buffer.write('Content-Disposition: form-data; name="%s"' % key)
            buffer.write('\r\n\r\n' + value + '\r\n')
        for(key, fd) in files:
            fsize = os.fstat(fd.fileno())[stat.ST_SIZE]
            fname = fd.name.split('/')[-1]
            contenttype = guess_type(fname)[0] or 'application/octet-stream'
            fname = encode_str(fname)
            buffer.write('--%s\r\n' % boundary)
            buffer.write('Content-Disposition: form-data; name="%s"; filename="%s"\r\n' % (key, fname))
            buffer.write('Content-Type: %s\r\n' % contenttype)
            buffer.write('Content-Length: %s\r\n' % fsize)
            fd.seek(0)
            buffer.write('\r\n' + fd.read() + '\r\n')
        buffer.write('--' + boundary + '--\r\n')
        buffer = buffer.getvalue()
        return boundary, buffer

    multipart_encode = Callable(multipart_encode)

    https_request = http_request


class BodyPostHandler(urllib2.BaseHandler):
    handler_order = urllib2.HTTPHandler.handler_order - 10 # needs to run first

    def http_request(self, request):
        data = request.get_data()
        if data is None:
            return request
        if not isinstance(data, basestring):
            newdata = []
            _json_dumps(data, newdata)
            request.add_data(''.join(newdata))
        elif has_non_ascii(data):
            request.add_data( encode_str(data) )

    https_request = http_request


def post(url, data=None, has_files=False):
    '''url: request URL, supports params.
    body: content in the body field.'''
    if has_files:
        opener = urllib2.build_opener(FormDataHandler)
    else:
        opener = urllib2.build_opener(BodyPostHandler)
    r = opener.open(url, data)
    return loads(r.read())
