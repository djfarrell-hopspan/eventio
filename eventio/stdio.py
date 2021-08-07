# Copyright 2021 "Dan Farrell <djfarrell@hopspan.com>"
# 
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
# 
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import binascii
import functools
import subprocess
import sys

from . import poller
from . import liner


log =  functools.partial(print, 'info   :', flush=True)
logw = functools.partial(print, 'warning:', flush=True)
loge = functools.partial(print, 'error  :', flush=True)
logd = functools.partial(print, 'debug  :', flush=True)


def set_logfns(i, w, e, d):

    global log
    global logw
    global loge
    global logd

    log = i
    logw = w
    loge = e
    logd = d


class StdioBaseHandler(poller.Handler):

    def __init__(self, name, stdin, stdout=None, stderr=None):

        fds = {
            stdin.fileno(),
        }
        if stderr is not None:
            fds.add(stderr.fileno())
        if stdout is not None:
            fds.add(stdout.fileno())

        poller.Handler.__init__(self, name if name else '__stdin__', fds=fds)

        self.stdin = stdin
        self.stderr = stderr
        self.stdout = stdout

    def on_stdin(self, data):

        log(f'{self.name}: stdin: {data}')

    def on_stdin_closed(self):

        logw(f'{self.name}: closed')
        self.poller.pop_handler(self)

    def on_readable(self, fd):

        logd(f'{self.name}: on readable: {fd}')
        data = self.stdin.read(2**16)
        if isinstance(data, str):
            data = data.encode()

        logd(f'{self.name}: on readable: {fd}: {len(data)}: {binascii.b2a_hex(data)}')
        if not len(data):
            logw(f'{self.name}: closing')
            self.on_stdin_closed()
        elif b'\x0d' in data or self.stdin.closed:
            self.on_stdin(data[:data.find(b'\x0d')])
            raise SystemExit(0)
        else:
            self.on_stdin(data)

        logd(f'{self.name}: {self.stdin.closed}')
        if self.stdin.closed:
            self.on_stdin_closed()

    def on_errorable(self, fd):

        loge(f'handler[{self.__name__}]: on error')

class StdioHandler(StdioBaseHandler):

    def __init__(self, *args, **kwargs):

        StdioBaseHandler.__init__(self, '__stdin__', sys.stdin.buffer, *args, **kwargs)

class StdioBaseLineHandler(StdioBaseHandler, liner.LineMixin):

    def __init__(self, *args, **kwargs):

        StdioBaseHandler.__init__(self, *args, **kwargs)
        liner.LineMixin.__init__(self)

    def on_stdin_closed(self):

        self.on_flush_line()
        StdioHandler.on_stdin_closed(self)

    def on_stdin(self, data):

        logd(f'{self.name}: stdin: {data}')
        self.on_line_data(data)

class StdioLineHandler(StdioBaseLineHandler, liner.LineMixin):

    def __init__(self):

        StdioBaseHandler.__init__(self, '__stdin_line__', sys.stdin)
        liner.LineMixin.__init__(self)
